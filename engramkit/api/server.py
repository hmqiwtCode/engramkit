"""EngramKit REST API — FastAPI app composing route modules."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from engramkit.config import ENGRAMKIT_HOME
from engramkit.api.routes_vaults import router as vaults_router
from engramkit.api.routes_search import router as search_router
from engramkit.api.routes_kg import router as kg_router
from engramkit.api.routes_memory import router as memory_router
from engramkit.api.routes_chat import router as chat_router

app = FastAPI(title="EngramKit API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vaults_router)
app.include_router(search_router)
app.include_router(kg_router)
app.include_router(memory_router)
app.include_router(chat_router)


# ── Dashboard static file serving ─────────────────────────────────────────

def _find_dashboard_static() -> Path | None:
    """Find the built dashboard static files."""
    candidates = [
        Path(__file__).parent.parent.parent / "dashboard" / "out",       # repo: dashboard/out/
        Path(__file__).parent.parent / "dashboard_static",               # bundled in package
        ENGRAMKIT_HOME / "dashboard",                                    # ~/.engramkit/dashboard/
    ]
    env_path = os.environ.get("ENGRAMKIT_DASHBOARD_STATIC")
    if env_path:
        candidates.insert(0, Path(env_path))

    for c in candidates:
        if c.exists() and (c / "index.html").exists():
            return c
    return None


if os.environ.get("ENGRAMKIT_SERVE_DASHBOARD") == "1":
    static_dir = _find_dashboard_static()
    if static_dir:
        # Serve static assets (_next, favicon, etc.)
        next_static = static_dir / "_next"
        if next_static.exists():
            app.mount("/_next", StaticFiles(directory=str(next_static)), name="next_static")

        @app.get("/favicon.ico")
        async def favicon():
            fav = static_dir / "favicon.ico"
            if fav.exists():
                return FileResponse(str(fav))
            return HTMLResponse("", status_code=404)

        # SPA catch-all: serve index.html for all non-API, non-POST routes
        @app.api_route("/{full_path:path}", methods=["GET", "HEAD"])
        async def serve_spa(request: Request, full_path: str):
            # Skip API paths entirely — return 404 so FastAPI tries other routes
            if full_path.startswith("api"):
                return HTMLResponse("", status_code=404)

            # Try exact file match first (e.g. /search.html, /vaults.html)
            file_path = static_dir / full_path
            if file_path.is_file():
                return FileResponse(str(file_path))

            # Try with .html extension
            html_path = static_dir / f"{full_path}.html"
            if html_path.is_file():
                return FileResponse(str(html_path))

            # Try as directory with index.html
            index_path = static_dir / full_path / "index.html"
            if index_path.is_file():
                return FileResponse(str(index_path))

            # SPA fallback: serve root index.html (client-side routing handles the rest)
            root_index = static_dir / "index.html"
            if root_index.exists():
                return FileResponse(str(root_index))

            return HTMLResponse("Dashboard not found", status_code=404)


def main():
    import uvicorn
    ENGRAMKIT_HOME.mkdir(parents=True, exist_ok=True)
    port = int(os.environ.get("UVICORN_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
