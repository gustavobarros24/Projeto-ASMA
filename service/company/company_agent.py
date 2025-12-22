from __future__ import annotations
from typing import Optional, Tuple, Dict
from spade.agent import Agent
from common.package import *
from common.geo_coord import *
from utils.logger import *
from behaviour.buyer_behaviour import *
from behaviour.receiver_behaviour import *
from common.item import *


"""
===============================================================================

	Company Agent

===============================================================================
"""

log = get_logger( name = "company", log_dir = "logs", console = True )

class CompanyAgent( Agent ):
	inventory: Dict[str, Item]

	def __init__( self, jid: str, password: str, inventory: Dict[str, Item] ):
		super().__init__( jid, password )
		self.inventory = inventory

	async def setup( self ):
		log.info( f"Company agent started: { self.jid }..." )
		self.add_behaviour( ReceiverBehaviour() )