import sys
import os
import json
import traceback

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

backend_app = None
import_error_message = None

try:
    from backend.main import app as backend_app
except BaseException as ex:
    import_error_message = f"{type(ex).__name__}: {str(ex)}\n\n{traceback.format_exc()}"

async def app(scope, receive, send):
    if scope['type'] != 'http':
        return

    if import_error_message is not None:
        body = json.dumps({
            "status": "backend_import_error",
            "error": import_error_message
        }).encode('utf-8')
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [(b'content-type', b'application/json')],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
        return

    # Forward to FastAPI app
    await backend_app(scope, receive, send)
