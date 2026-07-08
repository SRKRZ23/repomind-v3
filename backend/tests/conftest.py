import sys
from pathlib import Path

# Make backend/ importable when pytest is run from backend/ or repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
