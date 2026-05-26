from fastapi import APIRouter
import os
import sys
import time
import signal
import logging

logger = logging.getLogger("screensaver")

router = APIRouter(prefix="/api/system", tags=["system"])

import threading

def do_restart():
    logger.info("Restarting system cleanly...")
    time.sleep(0.5)
    # Re-execute the current python process with the same arguments (cross-platform)
    os.execv(sys.executable, [sys.executable] + sys.argv)

def force_exit():
    time.sleep(1.0)
    logger.info("Force exiting process now...")
    os._exit(0)

def do_stop():
    logger.info("Stopping system cleanly...")
    # Send SIGTERM to ourselves to trigger a clean uvicorn shutdown first
    os.kill(os.getpid(), signal.SIGTERM)
    # Start a backup thread to force-exit the process after 1 second if it hangs on active connections
    threading.Thread(target=force_exit, daemon=True).start()

@router.post("/restart")
async def restart_system():
    threading.Thread(target=do_restart, daemon=True).start()
    return {"message": "Restarting server..."}

@router.post("/stop")
async def stop_system():
    threading.Thread(target=do_stop, daemon=True).start()
    return {"message": "Stopping server..."}
