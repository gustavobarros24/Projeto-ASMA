from typing import Optional, Tuple, Dict
from spade.behaviour import CyclicBehaviour
from common.package import *
from utils.logger import *
from utils.utils import *
from common.packet import *

"""
===============================================================================

	Receiver Behaviour (Client)

===============================================================================
"""

_TIMEOUT = 5 # seconds

class ReceiverBehaviour( CyclicBehaviour ):
	def __init__( self, *, log ):
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
			return

		if isinstance( packet, DeliveryPacket ):
			log.info( "Received a delivery packet..." )
			self.handle_delivery( packet )
		if isinstance( packet, InventoryPacket ):
			log.info( "Received a inventory packet..." )
			self.handle_inventory( packet )
		else:
			log.warning( f"Receive an unexpected packet: { packet }..." )

	def handle_delivery( self, packet: DeliveryPacket ):
		log = self.log

		order_id = packet.order_id
		item_id = packet.item_id
		if self.agent.pending_orders[order_id] == item_id:
			log.info( f"Receive packet for order: { order_id } with item: { item_id }..." )
			package = self.agent.pending_orders.pop( order_id, None )
			self.agent.inventory[package.company_id].append( package.order_id )
			log.info( f"Item received: { package }..." )
		else:
			log.warning( f"Didn't ask for this: { item_id }..." )

	def handle_inventory( self, packet: InventoryPacket ):
		log = self.log

		self.agent.available_items_cache = packet.inventory
		log.info( "Inventory cache filled..." )