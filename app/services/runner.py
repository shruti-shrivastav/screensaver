from __future__ import annotations
import json
import os
import re
import subprocess
import sys
import tempfile


def run_test(code: str, test_input: str, expected_output: str) -> tuple[bool, str]:
    """
    Execute `code` with the given test input and compare to expected_output.
    Supports either a `solve(**kwargs)` function or a `Solution` class with a single public method.

    Returns:
        (passed: bool, diagnostic: str)
    """
    # Convert comma-separated assignments to newline-separated for exec
    processed_input = re.sub(r",\s*([a-zA-Z_]\w*\s*=)", r"\n\1", test_input)

    script = f"""\
import json
import sys
import traceback

{code}

def _run():
    try:
        vars_ = {{}}
        exec({repr(processed_input)}, {{}}, vars_)

        if 'solve' in globals():
            result = globals()['solve'](**vars_)
        elif 'Solution' in globals():
            sol = globals()['Solution']()
            methods = [m for m in dir(sol) if not m.startswith('_') and callable(getattr(sol, m))]
            if not methods:
                raise RuntimeError("Solution class has no public methods")
            result = getattr(sol, methods[0])(**vars_)
        else:
            raise RuntimeError("No 'solve' function or 'Solution' class found in code")

        print("---RESULT---")
        print(json.dumps(result, default=str))
    except Exception:
        print("---ERROR---")
        traceback.print_exc()

_run()
"""

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
            tmp.write(script)
            tmp_path = tmp.name

        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        combined = proc.stdout + "\n" + proc.stderr

        if "---ERROR---" in combined:
            err_part = combined.split("---ERROR---", 1)[1].strip()
            return False, err_part or "Unknown execution error"

        if "---RESULT---" in combined:
            result_line = combined.split("---RESULT---", 1)[1].strip().split("\n")[0]
            try:
                actual = json.loads(result_line)
            except json.JSONDecodeError:
                actual = result_line

            try:
                expected = json.loads(expected_output)
            except json.JSONDecodeError:
                expected = expected_output

            if _compare(actual, expected):
                return True, str(actual)
            return False, f"Expected: {expected!r}\nActual:   {actual!r}"

        return False, f"No result marker in output:\n{combined[:500]}"

    except subprocess.TimeoutExpired:
        return False, "Execution timed out (15 s)"
    except Exception as exc:
        return False, f"System error: {exc}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _compare(actual, expected) -> bool:
    """Order-insensitive list comparison, otherwise strict equality."""
    if actual == expected:
        return True
    if isinstance(actual, list) and isinstance(expected, list):
        try:
            return sorted(str(x) for x in actual) == sorted(str(x) for x in expected)
        except Exception:
            pass
    return False
