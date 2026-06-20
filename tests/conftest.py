import pathlib
import sys

# Ensure the repository root is on sys.path so tests can import app.main.
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
