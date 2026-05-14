import sys
from pathlib import Path

INTERNAL = Path(__file__).parent / 'internal'
if INTERNAL.is_dir() and str(INTERNAL) not in sys.path:
    sys.path.insert(0, str(INTERNAL))


try:
    from aqt import mw
except ImportError:
    pass
else:
    from .main import main
    main()
