import json

from asyncio import Queue
from typing import  Dict, Optional
from spade.agent import Agent
from common.package import *
from common.geo_coord import *
from utils.logger import *
from utils.utils import *
from .behaviour.sender_behaviour import *
from .behaviour.receiver_behaviour import *
from .behaviour.package_manager_behaviour import *
from common.item import *
from common.drone_info import *


"""
===============================================================================

	Company Agent

===============================================================================
"""

_MANAGER_TIMEOUT = 2 # seconds

class CompanyAgent( Agent ):
	inventory: Dict[str, Item]
	packages_to_send: Queue[Package]
	rented_drones: List[DroneInfo]
	budget: float

	def __init__( self, _id: str, _password: str, _budget: float ):
		super().__init__( _id, _password )
		self.budget = _budget
		self.inventory = self._load_inventory( self.jid.node )
		self.packages_to_send = Queue()
		self.rented_drones = []

		self.log = get_logger(
			name = f"company.{ self.jid.node }",
			log_dir = "logs",
			console = True,
		)

	def _load_inventory( self, company_id: str ) -> Dict[str, Item]:
		with open( ITEMS_PATH, "r", encoding = "utf-8" ) as f:
			data = json.load( f )
		
		inventory = {}
		for item_data in data["items"]:
			if item_data["company_id"] == company_id.upper():
				item = Item( **item_data )
				inventory[item.id] = item
		return inventory

	async def setup( self ):
		self.log.info( f"Company agent started: { self.jid.node }..." )
		self.add_behaviour( ReceiverBehaviour() )
		self.add_behaviour( PackageManagerBehaviour( period = _MANAGER_TIMEOUT ) )