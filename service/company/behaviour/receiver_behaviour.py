from __future__ import annotations
from typing import Optional, Tuple, Dict
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from common.package import *
from utils.logger import *
from utils.utils import *
from common.packet import *

"""
===============================================================================

	Receiver Behaviour (Company)

===============================================================================
"""

_TIMEOUT = 1 # second

log = logging.getLogger( __name__ )

class ReceiverBehaviour( CyclicBehaviour ):
	async def run(self):
		msg = await self.receive( timeout = _TIMEOUT )
		if not msg:
			return

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
		inventory_packet = InventoryPacket( sender_id = self.agent.jid, inventory = self.agent.inventory )
		msg = Message( to = packet.sender_jid )
		msg.body = inventory_packet.serialize()
		await self.send( msg )
		log.info( f"Sent inventory to { packet.sender_jid }...")

	async def handle_buy( self, packet: BuyItemPacket ):
		item_id = packet.item_id
		sender_jid = packet.sender_jid
		if item_id in self.agent.inventory:
			item = self.agent.inventory[item_id]
			log.info( f"Item { item_id } sold to { sender_jid }..." )

			delivery_packet = DeliveryPacket(
				sender_id = self.agent.jid,
				order_id = packet.order_id,
				item_id = item.id
			)
			msg = Message( to = sender_jid )
			msg.body = delivery_packet.serialize()
			await self.send( msg )
			log.info( f"Sent delivery confirmation for order { packet.order_id }...")
		else:
			log.warning( f"Item { item_id } not available for { sender_jid }...")