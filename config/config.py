import os

"""
===============================================================================

	Config

===============================================================================
"""

DOMAIN = os.getenv( "USERDOMAIN" )

CENTRAL_ID = "central"
CENTRAL_LAT = 41.888866
CENTRAL_LON = -87.626396

def get_agent_jid( name: str ) -> str:
	return f"{ name }@{ DOMAIN }"

def get_jid_from_sender( sender: str ) -> str:
    name = sender.rsplit( '/', 1 )[ 0 ]
    return name