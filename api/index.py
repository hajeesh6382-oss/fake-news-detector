import sys
import os
import traceback

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from backend.main import app
except Exception as ex:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI(title="Veritas AI Import Error Fallback")
    err_text = f"{type(ex).__name__}: {str(ex)}\n\n{traceback.format_exc()}"
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def fallback_route(path: str):
        return JSONResponse(status_code=500, content={"status": "backend_import_error", "error": err_text})
