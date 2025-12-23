import spade
import asyncio
import json

from utils.logger import * 
from utils.utils import *
from central.central_agent import *
from company.company_agent import *
from drone.drone_agent import *
from config.config import *


"""
===============================================================================

	Main

===============================================================================
"""

_CENTRAL_NAME = "central"
_DEFAULT_PASSWORD = "123"

log = get_logger( name = "startup", log_dir = "logs", console = True )

def _load_companies():
	with open( COMPANIES_PATH ) as f:
		data = json.load( f )
	return [
		{
			"jid": get_agent_jid( c["id"] ),
			"password": _DEFAULT_PASSWORD,
			"info": c
		}
		for c in data["companies"]
	]

def _load_drones():
	with open( DRONES_PATH ) as f:
		data = json.load( f )
	return [
		{
			"jid": get_agent_jid( d["id"] ),
			"password": _DEFAULT_PASSWORD,
			"info": d
		}
		for d in data["drones"]
	]

async def main():
	log.info( f"Starting { _CENTRAL_NAME }..." )

	companies = _load_companies()
	log.info( f"Loaded companies: { companies }..." )

	drones = _load_drones()
	log.info( f"Loaded drones: { drones }...")

	try:
		# to be completed...
		# log.info( "Starting central..." )
		# central_agent = CentralAgent( get_agent_jid( _CENTRAL_NAME ), _DEFAULT_PASSWORD )
		# await central_agent.start( auto_register = True )

		log.info( "Starting companies..." )
		company_agents = []
		for company in companies:
			agent = CompanyAgent( company["jid"], company["password"], company["info"] )
			company_agents.append( agent )
			await agent.start( auto_register = True )

		# to be completed...
		# log.info( "Starting drones..." )
		# drone_agents = []
		# for drone in drones:
		# 	agent = DroneAgent( drone["jid"], drone["password"], drone["info"] )
		# 	drone_agents.append( agent )
		# 	await agent.start( auto_register = True )

	except Exception as e:
		log.critical( e )
		return

	print( "Agents running. Press Ctrl+C to stop." )
	try:
		while True:
			await asyncio.sleep( 1 )
	except KeyboardInterrupt:
		log.info( "Shutting down all agents..." )
	finally:
		#await central_agent.stop()
		for agent in company_agents: #+ drone_agents:
			await agent.stop()
		log.info( "Shutdown complete..." )

if __name__ == "__main__":
	spade.run( main() )