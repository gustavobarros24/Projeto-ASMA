from __future__ import annotations
from typing import Optional, Tuple, Dict
from spade.agent import Agent
from common.package import *
from common.geo_coord import *
from utils.logger import *
from behaviour.buyer_behaviour import *
from behaviour.receiver_behaviour import *
from collections import defaultdict

"""
===============================================================================

	Client Agent

===============================================================================
"""

log = logging.getLogger( __name__ )

class ClientAgent( Agent ):
	jid: str
	pending_orders: Dict[str, str]
	available_items_cache: Dict[str, Item]
	inventory: Dict[str, Dict[str, Item]]
	budget: float
	location: GeoCoord

	def __init__( self, jid: str, password: str, budget: float , location: GeoCoord ):
		super().__init__( jid, password )
		self.pending_orders = {}
		self.budget = budget
		self.available_items_cache = {}
		self.inventory = defaultdict( dict )
		self.location = location

	async def setup( self ):
		log.info( f"Agent started: { self.jid }..." )
		self.add_behaviour( ReceiverBehaviour() )

	def get_inventory( self, company_id: str ):
		self.add_behaviour(  )

	def clean_cache( self ):
		self.available_items_cache.clear()

	def buy_item( self, seller_jid: str, item_id: str ):
		item = self.available_items_cache[item_id]
		self.add_behaviour( BuyerBehaviour( seller_jid, self.jid, item ) )
