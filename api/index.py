from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from academic_engine.web.app import create_app


fastapi_app = create_app()


async def app(scope, receive, send):
    await fastapi_app(scope, receive, send)
