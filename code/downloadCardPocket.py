"""
Download Pocket card info from limitlesstcg.com

A shortcut for `code/updateDatabase.py pocket`; every option of that script
works here too.

Februray 18, 2025 by Weihang
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import updateDatabase

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "pocket", *sys.argv[1:]]
    updateDatabase.main()
