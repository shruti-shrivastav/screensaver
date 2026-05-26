from __future__ import annotations
import re
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from app.api.deps import require_auth
from app.models.question import Question, QuestionStatus
from app.models.session import Session
from app.services.capture import take_screenshot
from app.services.analyzer import analyze_screen
from app.storage.session_store import session_store

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    label: str = ""


class AnalyzeRequest(BaseModel):
    model: str = "gemini-2.0-flash"


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:60] or "question"


@router.get("", dependencies=[Depends(require_auth)])
async def list_sessions() -> list[Session]:
    return session_store.list_sessions()


@router.post("", dependencies=[Depends(require_auth)], status_code=status.HTTP_201_CREATED)
async def create_session(body: CreateSessionRequest) -> Session:
    return session_store.create_session(label=body.label)


@router.get("/{sid}", dependencies=[Depends(require_auth)])
async def get_session(sid: str):
    sess = session_store.get_session(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    questions = session_store.list_questions(sid)
    return {"session": sess, "questions": questions}


@router.delete("/{sid}", dependencies=[Depends(require_auth)], status_code=204)
async def delete_session(sid: str):
    sess = session_store.get_session(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    session_store.delete_session(sid)


@router.get("/{sid}/stream", dependencies=[Depends(require_auth)])
async def stream_session(sid: str):
    import asyncio
    import queue as stdlib_queue
    from sse_starlette.sse import EventSourceResponse
    from app.services.pubsub import pubsub
    
    log_q = pubsub.subscribe(sid)
    
    def _try_get(q: stdlib_queue.Queue):
        try:
            return q.get(timeout=0.1)
        except stdlib_queue.Empty:
            return None

    async def _event_gen():
        loop = asyncio.get_event_loop()
        try:
            while True:
                try:
                    msg = await loop.run_in_executor(None, _try_get, log_q)
                    if msg is None:
                        await asyncio.sleep(0.1)
                        continue
                    yield {"data": msg}
                except asyncio.CancelledError:
                    break
        finally:
            pubsub.unsubscribe(sid, log_q)

    return EventSourceResponse(_event_gen())



@router.post("/{sid}/analyze", dependencies=[Depends(require_auth)])
async def analyze(request: Request, sid: str, body: AnalyzeRequest) -> Question:
    """Capture screen, call Gemini, persist question + screenshot, return Question."""
    sess = session_store.get_session(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
        
    existing_questions = session_store.list_questions(sid)
    eq_summary = [
        {"id": q.id, "title": q.data.title}
        for q in existing_questions if q.data
    ]
 
    # Capture
    try:
        img_bytes = take_screenshot()
        session_store.save_frame(sid, img_bytes)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Screen capture failed: {exc}")
 
    # Create a placeholder question while analyzing
    question = Question(
        id="analyzing",
        session_id=sid,
        status=QuestionStatus.ANALYZING,
        model_used=body.model,
    )
 
    # Analyze with Gemini (Fully Async)
    try:
        result = await analyze_screen(img_bytes, body.model, eq_summary, sid=sid, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    action = result["action"]
    target_id = result["target_id"]
    new_qd = result["data"]
    
    existing = next((q for q in existing_questions if q.id == target_id), None)
    
    if action == "update" and existing:
        qid = existing.id
        # Merge fields
        if new_qd.title and new_qd.title != "Untitled":
            existing.data.title = new_qd.title
        if new_qd.description:
            existing.data.description = new_qd.description
        if new_qd.constraints:
            existing.data.constraints = new_qd.constraints
        
        # Merge examples/test_cases avoiding exact duplicates
        for ex in new_qd.examples:
            if not any(e.input == ex.input for e in existing.data.examples):
                existing.data.examples.append(ex)
        for tc in new_qd.test_cases:
            if not any(t.input == tc.input for t in existing.data.test_cases):
                existing.data.test_cases.append(tc)
                
        existing.status = QuestionStatus.ANALYZED
        existing.model_used = body.model
        question = existing
    else:
        # Create new question
        qid = _slugify(new_qd.title) if action == "new" else _slugify(target_id)
        existing_ids = {q.id for q in existing_questions}
        base_qid = qid
        counter = 1
        while qid in existing_ids:
            qid = f"{base_qid}-{counter}"
            counter += 1
            
        question = Question(
            id=qid,
            session_id=sid,
            status=QuestionStatus.ANALYZED,
            data=new_qd,
            model_used=body.model,
        )

    session_store.save_screenshot(sid, qid, img_bytes)
    session_store.save_question(question)
    return question


@router.post("/{sid}/capture", dependencies=[Depends(require_auth)])
async def capture_frame(sid: str):
    sess = session_store.get_session(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    img_bytes = take_screenshot()
    filename = session_store.save_frame(sid, img_bytes)
    return {"ok": True, "filename": filename}


@router.get("/{sid}/frames", dependencies=[Depends(require_auth)])
async def get_frames(sid: str):
    sess = session_store.get_session(sid)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"frames": session_store.list_frames(sid)}


@router.get("/{sid}/frames/{filename}", dependencies=[Depends(require_auth)])
async def get_frame_file(sid: str, filename: str):
    p = session_store.get_frame_path(sid, filename)
    if not p:
        raise HTTPException(status_code=404, detail="Frame not found")
    return FileResponse(p, media_type="image/jpeg")
