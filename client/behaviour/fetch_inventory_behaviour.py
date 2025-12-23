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

	Fetch Inventory

===============================================================================
"""

log = logging.getLogger( __name__ )

class FetchBehaviour( OneShotBehaviour ):
	company_id: str

	def __init__( self, company_id: str ):
		super().__init__()
		self.company_id = company_id

	async def run( self ):
		log.info( f"Creating fetch packet for: { self.agent.jid }..." )
		packet = FetchInventoryPacket( self.agent.jid )

		msg = Message( to = self.company_id )
		msg.body = packet.serialize()

		log.info( "Sending fetch packet..." )
		await self.send( msg )
