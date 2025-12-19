#!/usr/bin/env python3
"""
SchedArray CLI entry point.

Allows running: python -m schedarray <command>
"""

import sys
from pathlib import Path

# Add current directory to path to ensure we can import
sys.path.insert(0, str(Path(__file__).parent.parent))

from schedarray.cli import main

if __name__ == "__main__":
    main()

