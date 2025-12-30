import spade

from client_agent import *
from config.config import *
from common.geo_coord import *
from ui import *

"""
===============================================================================

	Main

===============================================================================
"""

_CLIENT_NAME = "client1"
_CLIENT_PASSWORD = "123"
_CLIENT_LOCATION = GeoCoord.random_geocoord()
_BUDGET = 5000.00 

log = get_logger( name = _CLIENT_NAME, log_dir = "logs", console = False )

async def main():
	log.info( f"Starting { _CLIENT_NAME }..." )
	try:
		client_agent = ClientAgent( get_agent_jid( _CLIENT_NAME ), _CLIENT_PASSWORD, _BUDGET, _CLIENT_LOCATION )
		await client_agent.start( auto_register = True )
		log.info( "Agent added..." )

		log.info( "Starting ui..." )
		ui_task = asyncio.create_task( terminal_ui( client_agent ) )
		await ui_task
	except Exception as e:
		log.critical( e )
	finally:
		log.info( "Shutting down agent..." )
		await client_agent.stop()

if __name__ == "__main__":
	spade.run( main() )