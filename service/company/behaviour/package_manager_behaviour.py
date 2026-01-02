from spade.behaviour import PeriodicBehaviour
from common.package import *
from utils.logger import *
from utils.utils import *
from common.packet import *
from utils.communication import *

"""
===============================================================================

	Package Manager Behaviour: it will manage the requests 
								of drones for packages

===============================================================================
"""

class PackageManagerBehaviour( PeriodicBehaviour ):
	async def run( self ):
		log = self.agent.log

		queue = self.agent.packages_to_send
		try:
			package = await queue.get()
		except Exception as e:
			log.info( f"Error getting package from the queue: { e }...." )
			return

		sent = False
		drones = self.agent.rented_drones
		for drone in drones:
			if drone.available and drone.can_send( package ):
				log.info( f"Available drone: { drone.id }..." )

				log.info( "Creating package info packet..." )
				packet = PackageInfo( self.agent.jid.node, package )

				log.info( "Creating message..." )
				msg = new_message( packet, drone.id )
				await self.send( msg )
				sent = True
				log.info( f"Drone: { drone.id } will send package: { package.order_id }..." )
				break

		if not sent:
			log.info( "Package not sent..." )

			log.info( "Creating request drone packet..." )
			packet = RequestDronePacket( self.agent.jid.node, self.agent.budget, package.item.weight_kg, package.location )

			log.info( "Creating message..." )
			msg = new_message( packet, ... ) # will need central id
			await self.send( msg )

			log.info( "Make a request for new drone to send package..." )
			await queue.put( package )



