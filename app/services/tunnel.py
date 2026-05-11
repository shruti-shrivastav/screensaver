from __future__ import annotations
import collections
import subprocess
import threading
import time
import logging
from datetime import datetime
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("screensaver")

_LOG_MAXLEN = 300


class TunnelService:
    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._logs: collections.deque = collections.deque(maxlen=_LOG_MAXLEN)
        self._lock = threading.Lock()
        self._status = "stopped"
        self._error = ""
        self._manager: Optional[threading.Thread] = None
        self._running = False
        self._restart_requested = False
        self._backoff = 2

    def start_manager(self):
        if not settings.CF_TUNNEL_NAME and not settings.NGROK_URL:
            self._log("No tunnel configured — tunnel disabled.")
            self._status = "disabled"
            return
        self._running = True
        self._manager = threading.Thread(
            target=self._loop, daemon=True, name="tunnel-mgr"
        )
        self._manager.start()

    def stop_manager(self):
        self._running = False
        self._kill()

    def restart(self):
        self._restart_requested = True

    def get_logs(self) -> list[str]:
        return list(self._logs)

    def status(self) -> dict:
        proc_alive = self._proc is not None and self._proc.poll() is None
        return {
            "running": proc_alive,
            "status": self._status,
            "error": self._error,
            "tunnel_name": settings.NGROK_URL or settings.CF_TUNNEL_NAME or "(disabled)",
        }

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._logs.append(f"[{ts}] {msg}")

    def _kill(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=4)
                except Exception:
                    try:
                        self._proc.kill()
                    except Exception:
                        pass
            self._proc = None

    def _start(self):
        self._kill()
        
        if settings.NGROK_URL:
            name = settings.NGROK_URL
            self._log(f"Starting ngrok tunnel for {name}")
            cmd = ["ngrok", "http", f"--url={name}", str(settings.PORT)]
            binary_name = "ngrok"
        elif settings.CF_TUNNEL_NAME:
            name = settings.CF_TUNNEL_NAME
            self._log(f"Starting cloudflared tunnel run {name}")
            cmd = ["cloudflared", "tunnel", "run", name]
            binary_name = "cloudflared"
        else:
            return

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._status = "running"
            self._error = ""
            self._backoff = 2
            threading.Thread(
                target=self._reader, args=(self._proc,),
                daemon=True, name="tunnel-reader"
            ).start()
        except FileNotFoundError:
            self._status = "error"
            self._error = f"{binary_name} not found in PATH"
            self._log(f"ERROR: {self._error}")
            logger.error(self._error)
        except Exception as exc:
            self._status = "error"
            self._error = str(exc)
            self._log(f"ERROR: {exc}")
            logger.error(f"Tunnel start error: {exc}")

    def _reader(self, proc: subprocess.Popen):
        try:
            for line in proc.stdout:  # type: ignore
                self._log(line.rstrip())
        except Exception:
            pass

    def _loop(self):
        self._start()
        while self._running:
            time.sleep(1)
            if self._restart_requested:
                self._restart_requested = False
                self._log("Restart requested.")
                self._start()
                continue
            if self._proc and self._proc.poll() is not None:
                self._status = "crashed"
                self._log(f"tunnel process exited. Restarting in {self._backoff}s…")
                time.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, 60)
                self._start()


tunnel_service = TunnelService()
