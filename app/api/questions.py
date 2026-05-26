from __future__ import annotations
import asyncio
import queue as stdlib_queue
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.api.deps import require_auth
from app.models.question import Question, QuestionStatus, Solution, SolutionStatus, TestResult
from app.services.solver import solver_service
from app.services.instructor import handle_instruction
from app.services.runner import run_test
from app.storage.session_store import session_store

router = APIRouter(prefix="/api/sessions", tags=["questions"])


class SolveRequest(BaseModel):
    model: str = "gemini-2.0-flash"
    instructions: str | None = None

class InstructRequest(BaseModel):
    model: str = "gemini-2.0-flash"
    instruction: str

class RunTestsRequest(BaseModel):
    code: str

def _get_question_or_404(sid: str, qid: str) -> Question:
    q = session_store.load_question(sid, qid)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@router.get("/{sid}/questions/{qid}", dependencies=[Depends(require_auth)])
async def get_question(sid: str, qid: str):
    q = _get_question_or_404(sid, qid)
    sol = session_store.load_solution(sid, qid)
    return {"question": q, "solution": sol}


@router.get("/{sid}/questions/{qid}/image", dependencies=[Depends(require_auth)])
async def get_question_image(sid: str, qid: str):
    """Return the screenshot JPEG captured during analysis."""
    _get_question_or_404(sid, qid)
    path = session_store.screenshot_path(sid, qid)
    if not path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(path, media_type="image/jpeg")


@router.post("/{sid}/questions/{qid}/solve", dependencies=[Depends(require_auth)])
async def solve(sid: str, qid: str, body: SolveRequest):
    q = _get_question_or_404(sid, qid)
    if q.data is None:
        raise HTTPException(status_code=422, detail="Question has no parsed data yet")

    # Update question status
    q.status = QuestionStatus.SOLVING
    session_store.save_question(q)

    started = solver_service.start(sid, qid, body.model, body.instructions)
    if not started:
        return {"ok": False, "detail": "Already solving this question"}
    return {"ok": True}

@router.post("/{sid}/questions/{qid}/instruct", dependencies=[Depends(require_auth)])
async def instruct(sid: str, qid: str, body: InstructRequest):
    _get_question_or_404(sid, qid)
    res = await asyncio.to_thread(handle_instruction, sid, qid, body.model, body.instruction)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res

@router.post("/{sid}/questions/{qid}/stop", dependencies=[Depends(require_auth)])
async def stop(sid: str, qid: str):
    solver_service.stop(qid)
    return {"ok": True}

@router.post("/{sid}/questions/{qid}/run_tests", dependencies=[Depends(require_auth)])
async def run_tests(sid: str, qid: str, body: RunTestsRequest):
    q = _get_question_or_404(sid, qid)
    sol = session_store.load_solution(sid, qid)
    if not q or not q.data or not sol:
        raise HTTPException(status_code=404, detail="Question/Solution data missing")
        
    sol.code = body.code
    all_tests = []
    if q.data.examples:
        all_tests.extend(q.data.examples)
    if q.data.test_cases:
        all_tests.extend(q.data.test_cases)
        
    results = []
    all_passed = True
    
    for tc in all_tests:
        passed, diag = run_test(body.code, tc.input, tc.output)
        results.append(TestResult(
            input=tc.input,
            expected=tc.output,
            actual=str(diag),
            passed=passed,
        ))
        if not passed:
            all_passed = False
            
    sol.test_results = results
    sol.status = SolutionStatus.SOLVED if all_passed else SolutionStatus.FAILED
    session_store.save_solution(sid, qid, sol)
    
    return {"ok": True, "solution": sol}

@router.post("/{sid}/questions/{qid}/reset", dependencies=[Depends(require_auth)])
async def reset_solution(sid: str, qid: str):
    """Clear the solution state so the question can be solved fresh."""
    q = _get_question_or_404(sid, qid)
    solver_service.stop(qid)
    q.status = QuestionStatus.ANALYZED
    session_store.save_question(q)
    session_store.save_solution(sid, qid, Solution())
    session_store.save_conversation(sid, qid, [])
    return {"ok": True}


@router.get("/{sid}/questions/{qid}/stream", dependencies=[Depends(require_auth)])
async def stream_logs(sid: str, qid: str):
    """SSE endpoint — streams solver log events until done or disconnected."""
    _get_question_or_404(sid, qid)

    from app.services.pubsub import pubsub
    log_q = pubsub.subscribe(qid)
    
    sol = session_store.load_solution(sid, qid)
    if not solver_service.is_running(qid):
        # Not currently solving — send current solution status and close
        status_msg = sol.status if sol else "idle"

        async def _once():
            yield {"data": f'{{"type":"status","msg":"{status_msg}"}}'}
        pubsub.unsubscribe(qid, log_q)
        return EventSourceResponse(_once())

    async def _event_gen():
        loop = asyncio.get_event_loop()
        try:
            while True:
                try:
                    # Non-blocking check every 100ms
                    msg = await loop.run_in_executor(None, _try_get, log_q)
                    if msg is None:
                        await asyncio.sleep(0.1)
                        continue
                    yield {"data": msg}
                    if '"type":"done"' in msg:
                        break
                except asyncio.CancelledError:
                    break
        finally:
            pubsub.unsubscribe(qid, log_q)

    return EventSourceResponse(_event_gen())


def _try_get(q: stdlib_queue.Queue):
    try:
        return q.get(timeout=0.1)
    except stdlib_queue.Empty:
        return None
