from pathlib import Path
import os

LOCAL_BASE_DIR = Path.home() / ".cache" / "sereleum"
BASE_DIR = Path(os.environ.get("REVELIUM_BASE_DIR", LOCAL_BASE_DIR))

DEFAULT_CHROMADB_PATH = os.path.join(BASE_DIR, "chromadb")
DEFAULT_MODEL_DIR = os.path.join(BASE_DIR, "models")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

UNCLUSTERED = "unclustered"
