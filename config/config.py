import os

"""
===============================================================================

	Config

===============================================================================
"""
#DOMAIN = os.getenv( "USERDOMAIN" )

DOMAIN = "localhost"
CENTRAL_ID = "central"

def get_agent_jid( name: str ) -> str:
	return f"{ name }@{ DOMAIN }"

def get_jid_from_sender( sender: str ) -> str:
    name = sender.rsplit( '/', 1 )[ 0 ]
    return name