import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env or .env.local in project root, backend directory, and parent folders
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent

env_candidates = [
    project_root / ".env",
    project_root / ".env.local",
    backend_dir / ".env",
    backend_dir / ".env.local",
    project_root.parent / ".env",
]

for env_file in env_candidates:
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=True)

# Also run default load_dotenv() as fallback
load_dotenv()

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DIRECT_URL", "")
CREDIT_COST_PER_GENERATION = int(os.getenv("CREDIT_COST_PER_GENERATION", "1"))
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "*",
]
