import uuid

from pathlib import Path

"""
===============================================================================

	Utils

===============================================================================
"""

BASE_DIR = Path( __file__ ).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"
COMPANIES_PATH = ASSETS_DIR / "companies.json"
DRONES_PATH = ASSETS_DIR / "_drones.json"
ITEMS_PATH = ASSETS_DIR / "_items.json"

def generate_id() -> str:
    return str( uuid.uuid4() )