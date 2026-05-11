import json
import logging

from google.genai import types as genai_types

from app.core.ai import get_client
from app.models.question import QuestionData, Example, TestCase

logger = logging.getLogger("screensaver")

_PROMPT = """Analyze this screenshot of a DSA (Data Structures and Algorithms) problem.

EXISTING QUESTIONS IN DATABASE:
{existing_json}

INSTRUCTIONS:
1. Determine if this image contains a DSA question. If not, return: {{"error": "not_a_dsa_problem"}}
2. Check if this question already exists in the database.
3. If it exists, provide 'target_id' matching the existing ID, and update only MISSING or IMPROVED data.
4. If it's new, generate a unique 'target_id' (slugified title).
5. Return ONLY a JSON object with this exact structure:
{{
  "action": "update" | "new" | "ignore",
  "target_id": "existing-id-or-new-id",
  "data": {{
    "title": "Problem title (slug-friendly)",
    "description": "Full problem description",
    "constraints": "All constraints as a single string",
    "examples": [
      {{
        "input": "nums = [2,7,11,15], target = 9",
        "output": "[0,1]",
        "explanation": "nums[0] + nums[1] = 2 + 7 = 9"
      }}
    ],
    "test_cases": [
      {{
        "input": "nums = [3,2,4], target = 6",
        "output": "[1,2]"
      }}
    ]
  }}
}}

RULES:
- Inputs MUST be in Python variable-assignment format: `key = value` (e.g. `n = 5, arr = [1,2,3]`).
- Include ALL visible examples as both examples and test_cases.
- Surgical Update: if 'action' is 'update', only include fields present in the image.
- Return ONLY valid JSON, no markdown fences."""


def analyze_screen(img_bytes: bytes, model: str, existing_questions: list[dict] = None, sid: str = None) -> dict:
    """
    Send a screenshot to Gemini with context and extract a structured update or new question.
    Returns a dict with: 'action', 'target_id', 'data' (QuestionData).
    Raises ValueError if the image doesn't contain a DSA problem.
    Raises RuntimeError on API or parse errors.
    """
    client = get_client()
    
    if existing_questions is None:
        existing_questions = []
    
    prompt = _PROMPT.format(existing_json=json.dumps(existing_questions, indent=2))

    try:
        from app.services.pubsub import pubsub
        response_stream = client.models.generate_content_stream(
            model=model,
            contents=[
                genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                genai_types.Part.from_text(text=prompt),
            ],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        print(f"\n--- [START STREAM: {model} (Analyze)] ---")
        chunks = []
        for chunk in response_stream:
            if chunk.text:
                print(chunk.text, end="", flush=True)
                chunks.append(chunk.text)
                if sid:
                    pubsub.emit(sid, {"type": "stream", "chunk": chunk.text})
        print("\n--- [END STREAM] ---\n")
        
        raw = "".join(chunks).strip()
    except Exception as exc:
        logger.error(f"Gemini API generation failed: {exc}")
        raise RuntimeError(f"Gemini API error: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"Invalid JSON from Gemini: {exc}\nRaw output: {raw[:500]}")
        raise RuntimeError(f"Invalid JSON from Gemini: {exc}\nRaw: {raw[:300]}") from exc

    if "error" in data:
        raise ValueError(data["error"])

    if data.get("action") == "ignore":
        raise ValueError("No new DSA data found in image.")

    qd_raw = data.get("data", {})
    qd = QuestionData(
        title=qd_raw.get("title", "Untitled"),
        description=qd_raw.get("description", ""),
        constraints=qd_raw.get("constraints", ""),
        examples=[Example(**e) for e in qd_raw.get("examples", [])],
        test_cases=[TestCase(**t) for t in qd_raw.get("test_cases", [])],
    )
    
    return {
        "action": data.get("action", "new"),
        "target_id": data.get("target_id", "untitled"),
        "data": qd
    }
