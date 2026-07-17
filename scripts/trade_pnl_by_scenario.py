#!/usr/bin/env python3
"""
Thin wrapper: delegates to the new trade_pnl.py engine with design=ea_labels.

This preserves backward compatibility — running the old filename still produces
the original report (TRADE_PNL_BY_SCENARIO.md).
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Run the new engine with ea_labels (the only design this wrapper supports)
result = subprocess.run(
    [sys.executable, str(SCRIPT_DIR / "trade_pnl.py"), "--design", "ea_labels"],
    capture_output=True, text=True
)

if result.returncode != 0:
    print("Error from trade_pnl engine:", file=sys.stderr)
    print(result.stderr, file=sys.stderr)
    sys.exit(1)

print(result.stdout)
