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

class ReceiverBehaviour( CyclicBehaviour ):
	async def run( self ):
		log = self.agent.log

		msg = await self.receive( timeout = _TIMEOUT )
		if not msg:
			return

		log.info( "Received a message..." )
		try:
			packet = Packet.deserialize( msg.body )
		except Exception:
			log.warning( "Failed to deserialize packet" )
			return

		if isinstance( packet, FetchInventoryPacket ):
			log.info( f"Received inventory fetch request from { packet.sender_id }..." )
			await self.handle_fetch( packet )
		elif isinstance( packet, BuyItemPacket ):
			log.info( f"Received buy request from { packet.sender_id } for item { packet.item_id }..." )
			await self.handle_buy( packet )
		else:
			log.warning( f"Received unexpected packet: { packet }..." )

	async def handle_fetch( self, packet: FetchInventoryPacket ):
		log = self.agent.log

		inventory_packet = InventoryPacket( self.agent.jid.node, self.agent.inventory )
		msg = new_message( inventory_packet, packet.sender_id )
		await self.send( msg )
		log.info( f"Sent inventory to { packet.sender_jid }...")

	async def handle_buy( self, packet: BuyItemPacket ):
		log = self.agent.log
	
		inventory = self.agent.inventory
		item_id = packet.item_id
		sender_jid = packet.sender_jid
		if item_id in inventory:
			item = inventory[item_id]
			log.info( f"Item { item_id } sold to { sender_jid }..." )

			delivery_packet = DeliveryPacket(
				sender_id = self.agent.jid.node,
				order_id = packet.order_id,
				item_id = item.id
			)
			msg = new_message( delivery_packet, packet.sender_id )
			await self.send( msg )
			log.info( f"Sent delivery confirmation for order { packet.order_id }...")
		else:
			log.warning( f"Item { item_id } not available for { sender_jid }...")