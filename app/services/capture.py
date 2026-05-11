from __future__ import annotations
import io
import os
import signal
import subprocess
import sys
import threading
import time
import logging

from PIL import ImageGrab
from app.core.config import settings

logger = logging.getLogger("screensaver")

_lock = threading.Lock()


def take_screenshot() -> bytes:
    """Capture the primary display and return JPEG bytes. Thread-safe."""
    if sys.platform.startswith("linux"):
        data = _capture_linux()
        if data:
            return data
        logger.warning("Linux capture failed, trying fallback.")
        return _capture_fallback()
    return _capture_fallback()


def _capture_linux() -> bytes | None:
    with _lock:
        tmp = settings.FRAME_PATH.replace(".jpg", "-tmp.jpg")
        proc = None
        try:
            proc = subprocess.Popen(
                ["/usr/bin/gpu-screen-recorder", "-w", settings.DISPLAY_OUTPUT, "-o", tmp],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
            else:
                # Timed out — ask it to finalise
                try:
                    proc.send_signal(signal.SIGINT)
                    time.sleep(0.5)
                except Exception:
                    pass
                if proc.poll() is None:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        except FileNotFoundError:
            logger.error("gpu-screen-recorder not found. Please install it.")
            return None
        except Exception as exc:
            logger.error(f"Error executing gpu-screen-recorder: {exc}")
            return None

        if os.path.exists(tmp):
            os.chmod(tmp, 0o600)
            os.rename(tmp, settings.FRAME_PATH)

        if os.path.exists(settings.FRAME_PATH):
            try:
                with open(settings.FRAME_PATH, "rb") as f:
                    return f.read()
            except Exception:
                pass
        return None


def _capture_fallback() -> bytes:
    with _lock:
        try:
            screenshot = ImageGrab.grab()
            buf = io.BytesIO()
            screenshot.save(buf, format="JPEG", quality=85, optimize=True)
            return buf.getvalue()
        except Exception as exc:
            logger.error(f"Fallback capture via ImageGrab failed: {exc}")
            raise RuntimeError(f"All screen capture methods failed: {exc}") from exc
