from __future__ import annotations
import json
import queue
import re
import threading
import traceback
from datetime import datetime
from typing import Optional
import logging

from google.genai import types as genai_types

from app.core.ai import get_client
from app.core.config import settings
from app.models.question import Solution, SolutionStatus, TestResult
from app.services.runner import run_test
from app.storage.session_store import session_store

logger = logging.getLogger("screensaver")


_SOLVE_PROMPT_TEMPLATE = """\
Solve the following DSA problem in Python.

TITLE: {title}

DESCRIPTION:
{description}

CONSTRAINTS:
{constraints}

EXAMPLES:
{examples}

Requirements:
1. Write a function named `solve` that accepts keyword arguments matching the input variable names.
   OR write a `Solution` class with a single public method.
2. The function must return the answer (not print it).
3. Provide your complete solution inside a ```python ... ``` code block.
4. Before the code block, briefly explain your approach and state the Time and Space Complexity.
"""


class _SolverTask:
    """Manages one background solve thread for a single question."""

    def __init__(self, session_id: str, question_id: str, model: str, instructions: Optional[str] = None):
        self.session_id = session_id
        self.question_id = question_id
        self.model = model
        self.instructions = instructions
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"solver-{self.question_id}",
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    def _emit(self, event: dict):
        from app.services.pubsub import pubsub
        pubsub.emit(self.question_id, event)

    def _log(self, message: str, kind: str = "log"):
        ts = datetime.utcnow().strftime("%H:%M:%S")
        self._emit({"type": kind, "ts": ts, "msg": message})

    # ------------------------------------------------------------------
    def _run(self):
        try:
            self._solve()
        except Exception as exc:
            logger.error(f"Solver thread crashed for question {self.question_id}: {exc}")
            logger.error(traceback.format_exc())
            self._log(f"CRITICAL ERROR:\n{traceback.format_exc()}", "error")
            self._set_solution_status(SolutionStatus.ERROR)
        finally:
            self._emit({"type": "done"})

    def _solve(self):
        question = session_store.load_question(self.session_id, self.question_id)
        if question is None or question.data is None:
            self._log("ERROR: Question not found or has no data.", "error")
            return

        data = question.data
        all_tests = data.examples + data.test_cases  # type: ignore[operator]

        if not all_tests:
            self._log("⚠ No test cases — generating best-effort solution without verification.", "warn")

        history = session_store.load_conversation(self.session_id, self.question_id)
        solution = session_store.load_solution(self.session_id, self.question_id) or Solution()
        solution.status = SolutionStatus.SOLVING
        solution.model_used = self.model
        session_store.save_solution(self.session_id, self.question_id, solution)

        if not history:
            base_prompt = _SOLVE_PROMPT_TEMPLATE.format(
                title=data.title,
                description=data.description,
                constraints=data.constraints or "N/A",
                examples=json.dumps(
                    [e.model_dump() for e in data.examples], indent=2
                ),
            )
            if self.instructions:
                base_prompt += f"\n\nUSER INSTRUCTIONS:\n{self.instructions}"

            history.append({
                "role": "user",
                "content": base_prompt,
            })
        else:
            if self.instructions:
                history.append({
                    "role": "user",
                    "content": f"USER INSTRUCTIONS:\n{self.instructions}"
                })

        client = get_client()
        max_turns = settings.SOLVER_MAX_TURNS

        for turn in range(1, max_turns + 1):
            if self._stop_event.is_set():
                self._log("⛔ Stopped by user.", "warn")
                solution.status = SolutionStatus.STOPPED
                session_store.save_solution(self.session_id, self.question_id, solution)
                session_store.save_conversation(self.session_id, self.question_id, history)
                return

            self._log(f"🤖 Gemini turn {turn}/{max_turns} using {self.model}…")
            solution.iterations = turn
            session_store.save_solution(self.session_id, self.question_id, solution)

            try:
                gc = [
                    genai_types.Content(
                        role=h["role"],
                        parts=[genai_types.Part.from_text(text=h["content"])],
                    )
                    for h in history
                ]
                response_stream = client.models.generate_content_stream(model=self.model, contents=gc)
                
                print(f"\n--- [START STREAM: {self.model} (Solve Turn {turn})] ---")
                resp_chunks = []
                for chunk in response_stream:
                    if self._stop_event.is_set():
                        break
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                        resp_chunks.append(chunk.text)
                        self._emit({"type": "stream", "chunk": chunk.text})
                print("\n--- [END STREAM] ---\n")
                
                if self._stop_event.is_set():
                    self._log("⛔ Stopped by user during generation.", "warn")
                    solution.status = SolutionStatus.STOPPED
                    session_store.save_solution(self.session_id, self.question_id, solution)
                    session_store.save_conversation(self.session_id, self.question_id, history)
                    return
                
                resp_text = "".join(resp_chunks)
            except Exception as exc:
                self._log(f"Gemini error: {exc}", "error")
                solution.status = SolutionStatus.ERROR
                session_store.save_solution(self.session_id, self.question_id, solution)
                return

            history.append({"role": "model", "content": resp_text})
            code, explanation = _extract_code_and_explanation(resp_text)
            solution.code = code
            solution.explanation = explanation
            self._log(f"  Code extracted ({len(code)} chars). Running {len(all_tests)} test(s)…")

            results: list[TestResult] = []
            all_passed = True
            failures: list[str] = []

            for i, tc in enumerate(all_tests):
                if self._stop_event.is_set():
                    self._log("⛔ Stopped by user during testing.", "warn")
                    solution.status = SolutionStatus.STOPPED
                    session_store.save_solution(self.session_id, self.question_id, solution)
                    session_store.save_conversation(self.session_id, self.question_id, history)
                    return
                label = tc.input[:60] + ("…" if len(tc.input) > 60 else "")
                self._log(f"  ▷ Test {i + 1}: {label}")
                passed, diag = run_test(code, tc.input, tc.output)
                results.append(TestResult(
                    input=tc.input,
                    expected=tc.output,
                    actual=str(diag),
                    passed=passed,
                ))
                if passed:
                    self._log(f"    ✅ PASSED", "pass")
                else:
                    self._log(f"    ❌ FAILED: {str(diag)[:200]}", "fail")
                    all_passed = False
                    failures.append(
                        f"Test {i + 1}\nInput: {tc.input}\nExpected: {tc.output}\nDiagnostic:\n{diag}"
                    )

            solution.test_results = results
            session_store.save_solution(self.session_id, self.question_id, solution)
            session_store.save_conversation(self.session_id, self.question_id, history)

            if not all_tests:
                self._log("⚠ No tests to verify — saving code as best-effort.", "warn")
                solution.status = SolutionStatus.NO_TESTS
                session_store.save_solution(self.session_id, self.question_id, solution)
                return

            if all_passed:
                self._log("🎉 All tests passed! Solution saved.", "success")
                solution.status = SolutionStatus.SOLVED
                session_store.save_solution(self.session_id, self.question_id, solution)
                return

            if turn < max_turns:
                feedback = (
                    f"Some test cases failed ({len(failures)}/{len(all_tests)}).\n\n"
                    + "\n---\n".join(failures)
                    + "\n\nPlease analyse the failures, fix the logic, and provide updated code."
                )
                history.append({"role": "user", "content": feedback})

        self._log(f"⚠ Reached max turns ({max_turns}) without passing all tests.", "warn")
        solution.status = SolutionStatus.FAILED
        session_store.save_solution(self.session_id, self.question_id, solution)

    def _set_solution_status(self, status: SolutionStatus):
        sol = session_store.load_solution(self.session_id, self.question_id) or Solution()
        sol.status = status
        session_store.save_solution(self.session_id, self.question_id, sol)


def _extract_code_and_explanation(text: str) -> tuple[str, str]:
    blocks = re.findall(r"```python\n(.*?)\n```", text, re.DOTALL)
    if not blocks:
        blocks = re.findall(r"```\n(.*?)\n```", text, re.DOTALL)
    
    code = blocks[-1].strip() if blocks else text.strip()
    
    # Try to extract the explanation text before the code block
    split_pattern = r"```python\n|```\n"
    parts = re.split(split_pattern, text)
    explanation = parts[0].strip() if len(parts) > 1 else ""
    
    return code, explanation


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------

class SolverService:
    def __init__(self):
        self._tasks: dict[str, _SolverTask] = {}
        self._lock = threading.Lock()

    def start(self, session_id: str, question_id: str, model: str, instructions: Optional[str] = None) -> bool:
        """Start solving. If already running, stops the old task and detaches it."""
        with self._lock:
            existing = self._tasks.get(question_id)
            if existing and existing.is_alive():
                existing.stop()
            
            task = _SolverTask(session_id, question_id, model, instructions)
            self._tasks[question_id] = task
        task.start()
        return True

    def stop(self, question_id: str):
        with self._lock:
            task = self._tasks.get(question_id)
        if task:
            task.stop()

    def stop_all(self):
        with self._lock:
            tasks = list(self._tasks.values())
        for t in tasks:
            t.stop()

    def is_running(self, question_id: str) -> bool:
        with self._lock:
            t = self._tasks.get(question_id)
        return t is not None and t.is_alive()

    def running_ids(self) -> list[str]:
        with self._lock:
            return [qid for qid, t in self._tasks.items() if t.is_alive()]


solver_service = SolverService()
