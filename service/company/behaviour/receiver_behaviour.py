from spade.behaviour import CyclicBehaviour
from common.package import *
from utils.logger import *
from utils.utils import *
from common.packet import *
from utils.communication import *

"""
===============================================================================

	Receiver Behaviour (Company)

===============================================================================
"""

_TIMEOUT = 1 # second

#log = logging.getLogger( __name__ )

class ReceiverBehaviour( CyclicBehaviour ):
	def __init__( self, *, log = None):
		super().__init__()
		self.log = log

	async def run( self ):
		log = self.log

		msg = await self.receive( timeout = _TIMEOUT )
		if not msg:
			return

		log.info( "Received a message..." )
		try:
			packet = Packet.deserialize( msg.body )
		except Exception:
			log.warning("Failed to deserialize packet")
			return

		if isinstance( packet, FetchInventoryPacket ):
			log.info( f"Received inventory fetch request from { packet.sender_id }..." )
			await self.handle_fetch( packet )
		elif isinstance( packet, BuyItemPacket ):
			log.info( f"Received buy request from { packet.sender_id } for item { packet.item_id }..." )
			await self.handle_buy( packet )
		elif isinstance( packet, ResponseDronePacket ):
			log.info( f"Received response drone from { packet.sender_id }..." )
			await self.handle_response_drone( packet )
		else:
			log.warning( f"Received unexpected packet: { packet }..." )

	async def handle_fetch( self, packet: FetchInventoryPacket ):
		log = self.log

		inventory_packet = InventoryPacket( self.agent.jid.node, self.agent.inventory )
		msg = new_message( inventory_packet, packet.sender_id )
		await self.send( msg )
		log.info( f"Sent inventory to { packet.sender_id }...")

	async def handle_buy( self, packet: BuyItemPacket ):
		log = self.log

		inventory = self.agent.inventory
		item_id = packet.item_id
		sender_id = packet.sender_id
		if item_id in inventory:
			item = inventory[item_id]
			log.info( f"Item { item_id } sold to { sender_id }..." )

			log.info( "Creating package to send..." )
			package = Package( packet.order_id, sender_id, packet.client_location,  item )

			log.info( "Putting in queue, to be eventually sent..." )
			await self.agent.packages_to_send.put( package )
		else:
			log.info( f"Item { item_id } doesn't exist in this company..." )

	async def handle_response_drone(self, packet: ResponseDronePacket):
		log = self.log

		if packet.drone:
			log.info(f"Renting new drone: {packet.drone.id} costing {packet.cost}...")

			packet.drone.available = True

			self.agent.rented_drones.append(packet.drone)
			self.agent.budget -= packet.cost
		else:
			log.info("No available drone...")
