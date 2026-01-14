import os

"""
===============================================================================

	Config

===============================================================================
"""

DOMAIN = "localhost"
#DOMAIN = os.getenv( "USERDOMAIN" )

CENTRAL_ID = "central"
CENTRAL_LAT = 41.888866
CENTRAL_LON = -87.626396

# Paths
COMPANIES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "companies.json")
ITEMS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "_items.json")
DRONES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "_drones.json")
CLIENTS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "clients.json")

def get_agent_jid( name: str ) -> str:
	return f"{ name }@{ DOMAIN }"

def get_jid_from_sender( sender: str ) -> str:
    name = sender.rsplit( '/', 1 )[ 0 ]
    return name