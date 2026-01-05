from spade.behaviour import PeriodicBehaviour
from common.package import *
from utils.logger import *
from utils.utils import *
from common.packet import *
from utils.communication import *
from config.config import *

"""
===============================================================================

	Package Manager Behaviour: it will manage the requests 
								of drones for packages

===============================================================================
"""

class PackageManagerBehaviour( PeriodicBehaviour ):    
	def __init__( self, period: int, *, log = None ):
		super().__init__( period = period )
		self.log = log

	async def run( self ):
		log = self.log

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
				log.info( f"Drone { drone.id } will send package: { package.order_id }..." )
				break

		if not sent:
			log.info( "Package not sent..." )

			log.info( "Creating request drone packet..." )
			packet = RequestDronePacket(
				sender_id=self.agent.jid.node,
				company_budget=self.agent.budget,
				package_weight=package.item.weight_kg,
				client_location=package.location,
				pickup_location=self.agent.location
			)

			log.info( "Creating message..." )
			msg = new_message( packet, CENTRAL_ID )
			await self.send( msg )

			log.info( "Make a request for new drone to send package..." )
			await queue.put( package )



