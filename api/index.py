import sys
import os
import traceback

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from backend.main import app
except Exception as e:
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def error_catcher(path_name: str = ""):
        return {"status": "backend_import_error", "error": str(e), "traceback": err_tb}
