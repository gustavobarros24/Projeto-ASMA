from spade.behaviour import OneShotBehaviour
from common.package import *
from utils.logger import *
from utils.utils import *
from common.packet import *
from common.item import *
from utils.communication import *

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

	async def on_start( self ):
		log.info( f"FetchBehaviour started for { self.company_id }..." )

	async def run( self ):
		log.info( f"Creating fetch packet for: { self.agent.jid.node }..." )
		packet = FetchInventoryPacket( self.agent.jid.node )

		log.info( "Preparing message..." )
		msg = new_message( packet, self.company_id )

		log.info( "Sending fetch packet..." )
		await self.send( msg )
