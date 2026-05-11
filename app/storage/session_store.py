import json
import logging
import os
import threading
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.models.question import Question, QuestionData, QuestionStatus, Solution
from app.models.session import Session

logger = logging.getLogger("screensaver")


class SessionStore:
    """Single source of truth for all disk I/O. Thread-safe per question."""

    def __init__(self):
        self._q_locks: dict[str, threading.Lock] = {}
        self._meta_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session_dir(self, sid: str) -> str:
        return os.path.join(settings.sessions_dir, sid)

    def _question_dir(self, sid: str, qid: str) -> str:
        return os.path.join(self._session_dir(sid), "questions", qid)

    def _q_lock(self, sid: str, qid: str) -> threading.Lock:
        key = f"{sid}/{qid}"
        with self._meta_lock:
            if key not in self._q_locks:
                self._q_locks[key] = threading.Lock()
            return self._q_locks[key]

    @staticmethod
    def _read_json(path: str) -> Optional[dict]:
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as exc:
            logger.error(f"Failed to read JSON from {path}: {exc}")
            return None

    @staticmethod
    def _write_json(path: str, data: dict | list):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, path)  # atomic on POSIX

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, label: str = "") -> Session:
        ts = datetime.utcnow()
        sid = ts.strftime("%Y%m%dT%H%M%S")
        if not label:
            label = ts.strftime("%b %d, %I:%M %p")
        sess = Session(id=sid, label=label, created_at=ts)
        path = os.path.join(self._session_dir(sid), "session.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._write_json(path, sess.model_dump())
        return sess

    def list_sessions(self) -> list[Session]:
        base = settings.sessions_dir
        if not os.path.isdir(base):
            return []
        sessions: list[Session] = []
        for sid in sorted(os.listdir(base), reverse=True):
            path = os.path.join(base, sid, "session.json")
            raw = self._read_json(path)
            if raw:
                try:
                    s = Session(**raw)
                    s.question_count = self._count_questions(sid)
                    sessions.append(s)
                except Exception as exc:
                    logger.error(f"Failed to parse session {sid}: {exc}")
        return sessions

    def get_session(self, sid: str) -> Optional[Session]:
        path = os.path.join(self._session_dir(sid), "session.json")
        raw = self._read_json(path)
        if not raw:
            return None
        try:
            s = Session(**raw)
            s.question_count = self._count_questions(sid)
            return s
        except Exception as exc:
            logger.error(f"Failed to parse session {sid}: {exc}")
            return None

    def delete_session(self, sid: str):
        import shutil
        d = self._session_dir(sid)
        if os.path.isdir(d):
            shutil.rmtree(d)

    def _count_questions(self, sid: str) -> int:
        q_dir = os.path.join(self._session_dir(sid), "questions")
        if not os.path.isdir(q_dir):
            return 0
        return sum(
            1 for entry in os.scandir(q_dir)
            if entry.is_dir() and os.path.exists(os.path.join(entry.path, "question.json"))
        )

    # ------------------------------------------------------------------
    # Questions
    # ------------------------------------------------------------------

    def save_question(self, question: Question):
        with self._q_lock(question.session_id, question.id):
            path = os.path.join(
                self._question_dir(question.session_id, question.id), "question.json"
            )
            self._write_json(path, question.model_dump())

    def load_question(self, sid: str, qid: str) -> Optional[Question]:
        with self._q_lock(sid, qid):
            path = os.path.join(self._question_dir(sid, qid), "question.json")
            raw = self._read_json(path)
            if not raw:
                return None
            try:
                return Question(**raw)
            except Exception as exc:
                logger.error(f"Failed to parse question {qid} in {sid}: {exc}")
                return None

    def list_questions(self, sid: str) -> list[Question]:
        q_dir = os.path.join(self._session_dir(sid), "questions")
        if not os.path.isdir(q_dir):
            return []
        questions: list[Question] = []
        for qid in sorted(os.listdir(q_dir)):
            q = self.load_question(sid, qid)
            if q:
                questions.append(q)
        return questions

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def save_screenshot(self, sid: str, qid: str, img_bytes: bytes):
        path = os.path.join(self._question_dir(sid, qid), "screenshot.jpg")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(img_bytes)

    def screenshot_path(self, sid: str, qid: str) -> Optional[str]:
        path = os.path.join(self._question_dir(sid, qid), "screenshot.jpg")
        return path if os.path.exists(path) else None

    # ------------------------------------------------------------------
    # Frames (Raw captures)
    # ------------------------------------------------------------------

    def save_frame(self, sid: str, img_bytes: bytes) -> str:
        d = self._session_dir(sid)
        frames_dir = os.path.join(d, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"frame_{ts}.jpg"
        with open(os.path.join(frames_dir, filename), "wb") as f:
            f.write(img_bytes)
        return filename

    def list_frames(self, sid: str) -> list[str]:
        frames_dir = os.path.join(self._session_dir(sid), "frames")
        if not os.path.isdir(frames_dir):
            return []
        return sorted([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])

    def get_frame_path(self, sid: str, filename: str) -> Optional[str]:
        path = os.path.join(self._session_dir(sid), "frames", filename)
        return path if os.path.exists(path) else None

    # ------------------------------------------------------------------
    # Solutions
    # ------------------------------------------------------------------

    def save_solution(self, sid: str, qid: str, solution: Solution):
        with self._q_lock(sid, qid):
            path = os.path.join(self._question_dir(sid, qid), "solution.json")
            self._write_json(path, solution.model_dump())

    def load_solution(self, sid: str, qid: str) -> Optional[Solution]:
        with self._q_lock(sid, qid):
            path = os.path.join(self._question_dir(sid, qid), "solution.json")
            raw = self._read_json(path)
            if not raw:
                return None
            try:
                return Solution(**raw)
            except Exception as exc:
                logger.error(f"Failed to parse solution for {qid} in {sid}: {exc}")
                return None

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    def save_conversation(self, sid: str, qid: str, history: list):
        with self._q_lock(sid, qid):
            path = os.path.join(self._question_dir(sid, qid), "conversation.json")
            self._write_json(path, history)

    def load_conversation(self, sid: str, qid: str) -> list:
        with self._q_lock(sid, qid):
            path = os.path.join(self._question_dir(sid, qid), "conversation.json")
            raw = self._read_json(path)
            return raw if isinstance(raw, list) else []


# Global singleton
session_store = SessionStore()
