from typing import Optional, Dict, Any
import json
from google.genai import types as genai_types
from app.core.ai import get_client
from app.models.question import Question, Solution
from app.storage.session_store import session_store

INSTRUCT_PROMPT = """\
You are an AI assistant managing a DSA solver interface.
The current state of the problem is:
TITLE: {title}
CODE:
```python
{code}
```
EXPLANATION:
{explanation}

The user gave this instruction: "{instruction}"

Process the instruction and return a JSON object ONLY with the following optional fields (omit fields that are not changed or requested):
{{
  "code": "The fully updated python code string (only if the user asked to change the code/approach)",
  "explanation": "The updated or new explanation (only if requested or if code changed)",
  "new_test_cases": [{{"input": "in format expected", "output": "expected out"}}],
  "focus_tab": "one of: 'tab-solution', 'tab-explanation'"
}}

Rules:
1. NEVER wrap the JSON in markdown code blocks. Output purely the raw JSON object.
2. Only include what changed.
3. If the user asks a question, put the answer in the "explanation" field and set "focus_tab" to "tab-explanation".
"""

def handle_instruction(sid: str, qid: str, model: str, instruction: str) -> Dict[str, Any]:
    q = session_store.load_question(sid, qid)
    sol = session_store.load_solution(sid, qid)
    if not q or not q.data or not sol:
        return {"error": "Question or solution not found."}

    client = get_client()
    prompt = INSTRUCT_PROMPT.format(
        title=q.data.title,
        code=sol.code or "",
        explanation=sol.explanation or "",
        instruction=instruction
    )

    try:
        response_stream = client.models.generate_content_stream(
            model=model,
            contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=prompt)])],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        print(f"\n--- [START STREAM: {model} (Instruct)] ---")
        chunks = []
        from app.services.pubsub import pubsub
        for chunk in response_stream:
            if chunk.text:
                print(chunk.text, end="", flush=True)
                chunks.append(chunk.text)
                pubsub.emit(qid, {"type": "stream", "chunk": chunk.text})
        print("\n--- [END STREAM] ---\n")
        
        try:
            data = json.loads("".join(chunks))
        except json.JSONDecodeError:
            return {"error": "Failed to parse LLM response as JSON"}
            
        # Update state based on data
        changed = False
        if "code" in data and data["code"]:
            sol.code = data["code"]
            changed = True
        if "explanation" in data and data["explanation"]:
            sol.explanation = data["explanation"]
            changed = True
            
        if changed:
            session_store.save_solution(sid, qid, sol)
            
        if "new_test_cases" in data and isinstance(data["new_test_cases"], list) and len(data["new_test_cases"]) > 0:
            if q.data.test_cases is None:
                q.data.test_cases = []
            from app.models.question import TestCase
            for tc in data["new_test_cases"]:
                q.data.test_cases.append(TestCase(input=tc.get("input", ""), output=tc.get("output", "")))
            session_store.save_question(q)
            
        return {
            "ok": True,
            "updates": data,
            "solution": sol.model_dump(),
            "question": q.model_dump()
        }
        
    except Exception as exc:
        return {"error": str(exc)}
