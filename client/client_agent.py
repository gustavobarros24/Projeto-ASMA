from typing import Dict
from spade.agent import Agent
from common.package import *
from common.geo_coord import *
from utils.logger import *
from behaviour.buyer_behaviour import *
from behaviour.receiver_behaviour import *
from behaviour.fetch_inventory_behaviour import *
from collections import defaultdict

"""
===============================================================================

	Client Agent

===============================================================================
"""
class ClientAgent( Agent ):
	pending_orders: Dict[str, str]
	available_items_cache: Dict[str, Item]
	inventory: Dict[str, Dict[str, Item]]
	budget: float
	location: GeoCoord

	def __init__( self, _id: str, _password: str, budget: float , location: GeoCoord, *, log = None ):
		super().__init__( _id, _password )
		self.pending_orders = {}
		self.budget = budget
		self.available_items_cache = {}
		self.inventory = defaultdict( dict )
		self.location = location
		self.log = log

	async def setup( self ):
		self.log.info( f"Agent started: { self.jid.node }..." )
		self.add_behaviour( ReceiverBehaviour( log = self.log ) )

	async def get_inventory( self, company_id: str ):
		self.log.info( f"Getting inventory from: { company_id }..." )
		self.add_behaviour( FetchBehaviour( company_id, log = self.log ) )

	async def clean_cache( self ):
		self.log.info( "Clearing cache..." )
		self.available_items_cache.clear()

	async def buy_item( self, seller_jid: str, item_id: str ):
		self.log.info( f"Buying item: { item_id } from { seller_jid }..." )
		item = self.available_items_cache[item_id]
		self.add_behaviour( BuyerBehaviour( seller_jid, item, log = self.log ) )
