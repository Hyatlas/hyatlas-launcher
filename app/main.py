# app/main.py
"""
Hyatlas Launcher – FastAPI entry point
=====================================

Run options
-----------
• Development (browser):   python -m app.main
• Desktop window:          python run_launcher_desktop.py
"""

from __future__ import annotations

import importlib
import threading
from pathlib import Path
from typing import Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core import config

try:
    import webview  # type: ignore
except ModuleNotFoundError:
    webview = None  # run_desktop() will raise

# ────────────────────────────── template setup
BASE_PATH = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "templates"))

app = FastAPI(
    title=config.APP_NAME,
    version=config.LAUNCHER_VERSION,
    docs_url=None,
    redoc_url=None,
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_PATH / "static"), html=False),
    name="static",
)

# ────────────────────────────── pages
PAGE_CONTEXT: Dict[str, str] = {
    "app_name": config.APP_NAME,
    "launcher_version": config.LAUNCHER_VERSION,
}

@app.get("/login", response_class=HTMLResponse)
async def page_login(request: Request):
    return TEMPLATES.TemplateResponse(
        "pages/login.html",
        {"request": request, **PAGE_CONTEXT},
    )

@app.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    # read launcher config to fetch last joined server (may be None)
    last_srv = config.read_config().get("lastServer")

    return TEMPLATES.TemplateResponse(
        "pages/index.html",
        {
            "request": request,
            **PAGE_CONTEXT,
            "last_server": last_srv,          # <<< neu
        },
    )

@app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    return TEMPLATES.TemplateResponse(
        "pages/settings.html",
        {"request": request, **PAGE_CONTEXT},
    )

@app.get("/servers", response_class=HTMLResponse)
async def page_servers(request: Request):
    return TEMPLATES.TemplateResponse(
        "pages/serverlist.html",
        {"request": request, **PAGE_CONTEXT},
    )

@app.get("/local", response_class=HTMLResponse)
async def page_local(request: Request):
    return TEMPLATES.TemplateResponse(
        "pages/local.html",
        {"request": request, **PAGE_CONTEXT},
    )

@app.get("/adventure", response_class=HTMLResponse)
async def page_adventure(request: Request):
    """
    Create-/Manage-Worlds UI (“NEW ADVENTURE” Menüpunkt)
    """
    return TEMPLATES.TemplateResponse(
        "pages/adventure.html",
        {"request": request, **PAGE_CONTEXT},
    )

@app.get("/avatar", response_class=HTMLResponse)
async def page_adventure(request: Request):
    """
    Create-/Manage-Worlds UI (“NEW ADVENTURE” Menüpunkt)
    """
    return TEMPLATES.TemplateResponse(
        "pages/avatar.html",
        {"request": request, **PAGE_CONTEXT},
    )
@app.get("/loading", response_class=HTMLResponse)
async def page_loading(request: Request):
    return TEMPLATES.TemplateResponse(
        "pages/loading.html",
        {"request": request, **PAGE_CONTEXT},
    )


# ────────────────────────────── API routers
auth     = importlib.import_module("app.api.auth")
servers  = importlib.import_module("app.api.servers")
updates  = importlib.import_module("app.api.updates")
settings = importlib.import_module("app.api.settings")

app.include_router(auth.router,     prefix="/api")
app.include_router(servers.router,  prefix="/api")
app.include_router(updates.router,  prefix="/api")
app.include_router(settings.router, prefix="/api")

# ────────────────────────────── desktop helper
def _run_uvicorn_bg(host: str, port: int) -> None:
    def _target():
        uvicorn.run(app, host=host, port=port, log_level="error")
    threading.Thread(target=_target, daemon=True).start()

def run_desktop(host: str = "127.0.0.1", port: int = 5050) -> None:
    if webview is None:
        raise RuntimeError("pywebview not installed – run:  pip install pywebview")

    _run_uvicorn_bg(host, port)

    import time
    time.sleep(0.8)                               # wait until Uvicorn is ready

    start_url = f"http://{host}:{port}/login"

    # ---- Bridge object for pywebview 3.x ----
    class Bridge:                                # pylint: disable=too-few-public-methods
        def expand(self):
            """
            Called from JS after successful login.
            Maximise window and load the main UI.
            """
            window.toggle_fullscreen()           # maximise
            window.load_url(f"http://{host}:{port}/")

        def quit(self):
            window.destroy()

    bridge = Bridge()
    # -----------------------------------------

    window = webview.create_window(
        title=config.APP_NAME,
        url=start_url,
        width=1280,
        height=720,
        resizable=False,
        confirm_close=True,
        js_api=bridge,                           # 👉 expose Bridge.expand()
    )

    webview.start()