import spade
import asyncio

from client.client_agent import *
from config.config import *
from common.geo_coord import *
from client.web_ui import ClientWebUI

"""
===============================================================================

	Main

===============================================================================
"""

_CLIENT_NAME = "client" + generate_id()[:4]
_CLIENT_PASSWORD = "123"
_CLIENT_LOCATION = GeoCoord.random_geocoord()
_BUDGET = 5000.00 
_WEB_PORT = 5001  # Port for the web UI

log = get_logger( name = f"client.{ _CLIENT_NAME }", log_dir = "logs", console = False )

async def main():
	log.info( f"Starting { _CLIENT_NAME }..." )
	web_ui = None
	try:
		client_agent = ClientAgent( get_agent_jid( _CLIENT_NAME ), _CLIENT_PASSWORD, _BUDGET, _CLIENT_LOCATION, log = log )
		await client_agent.start( auto_register = True )
		log.info( "Agent added..." )

		# Start Web UI using aiohttp
		log.info( f"Starting Web UI on port {_WEB_PORT}..." )
		web_ui = ClientWebUI( client_agent, port=_WEB_PORT )
		await web_ui.start()
		
		print( f"\n{'='*60}" )
		print( f" Cliente iniciado com sucesso!" )
		print( f"{'='*60}" )
		print( f" Interface Web: http://localhost:{_WEB_PORT}" )
		print( f" Cliente ID: {_CLIENT_NAME}" )
		print( f" Orçamento: ${_BUDGET:.2f}" )
		print( f" Localização: {_CLIENT_LOCATION}" )
		print( f"{'='*60}\n" )
		print( "Pressione Ctrl+C para sair\n" )
		
		# Keep the main thread alive
		print( "DEBUG: Entering main loop..." )
		while True:
			await asyncio.sleep(1)
			
	except KeyboardInterrupt:
		print( "\n\nEncerrando cliente..." )
	except Exception as e:
		print( f"\n ERRO: {e}" )
		import traceback
		traceback.print_exc()
		log.critical( e )
	finally:
		log.info( "Shutting down agent..." )
		if web_ui is not None:
			await web_ui.stop()
		await client_agent.stop()

if __name__ == "__main__":
	spade.run( main() )