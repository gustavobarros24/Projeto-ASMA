from __future__ import annotations
from typing import Optional, Tuple, Dict
from spade.behaviour import OneShotBehaviour
from spade.message import Message
from common.package import *
from utils.logger import *
from utils.utils import *
from common.packet import *
from common.item import *

"""
===============================================================================

	Buyer Behaviour

===============================================================================
"""

log = logging.getLogger( __name__ )

class BuyerBehaviour( OneShotBehaviour ):
	seller_jid: str
	item: str

	def __init__( self, seller_jid: str, item: Item ):
		super().__init__()
		self.item = item
		self.seller_jid = seller_jid

	async def run( self ):
		log.info( f"Creating buy packet for: { self.agent.jid }..." )
		order_id = generate_id()
		packet = BuyItemPacket( self.agent.jid, order_id, self.item.id, self.agent.location )
		self.agent.pending_orders[order_id] = self.item.id
		self.agent.budget -=  self.item.price 

		msg = Message( to = self.seller_jid )
		msg.body = packet.serialize()

		log.info( "Sending buy packet..." )
		await self.send( msg )
