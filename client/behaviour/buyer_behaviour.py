from spade.behaviour import OneShotBehaviour
from common.package import *
from utils.logger import *
from utils.utils import *
from common.packet import *
from common.item import *
from config.config import *
from utils.communication import *

"""
===============================================================================

	Buyer Behaviour

===============================================================================
"""

log = logging.getLogger( __name__ )

class BuyerBehaviour( OneShotBehaviour ):
	seller_id: str
	item: Item

	def __init__( self, seller_id: str, item: Item ):
		super().__init__()
		self.item = item
		self.sender_id = seller_id

	async def run( self ):
		log.info( f"Creating buy packet for: { self.agent.jid.node } for { self.seller_id }..." )
		order_id = generate_id()
		packet = BuyItemPacket( self.agent.node, order_id, self.item.id, self.agent.location )
		self.agent.pending_orders[order_id] = self.item.id
		self.agent.budget -= self.item.price 

		log.info( "Preparing message..." )
		msg = new_message( packet, self.seller_id )

		log.info( "Sending buy packet..." )
		await self.send( msg )
