"""
Download Traditional Chinese card info from asia.pokemon-card.com

A shortcut for `code/updateDatabase.py tc`; every option of that script works
here too, and the sibling locales are available as `hk`, `th`, `id`, `sg`,
`my` and `ph`.

Februray 25, 2025 by Weihang
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import updateDatabase

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "tc", *sys.argv[1:]]
    updateDatabase.main()
