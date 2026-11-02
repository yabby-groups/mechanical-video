"""Repository entry point for the read-only production gate."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mechanical_video.production_gate import STAGES, evaluate, main, sha  # noqa: E402,F401


if __name__ == '__main__':
    raise SystemExit(main())
