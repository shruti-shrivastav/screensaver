"""Entry point — run with: python run.py"""
import os
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    # Write PID file for deterministic process tracking
    pid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "service.pid")
    try:
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=settings.PORT,
            reload=False,
            log_level="info",
        )
    finally:
        # Clean up PID file on exit
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        except Exception:
            pass
