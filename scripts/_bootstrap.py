"""Bootstrap helper — adds src/ to sys.path so scripts work without pip install."""
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent          # repo root
_SRC  = _ROOT / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Expose for scripts that need the root path
PROJECT_ROOT = _ROOT
