import jsonpickle

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List
from .package import Package
from .geo_coord import *
from .item import *


"""
===============================================================================

	Packets

===============================================================================
"""

@dataclass
class Packet:
	sender_id: str

	def __init__( self, sender_id: str ):
		self.sender_id = sender_id

	def serialize( self ) -> str:
		return jsonpickle.encode( self )

	@staticmethod
	def deserialize( data: str ) -> "Packet":
		return jsonpickle.decode( data )

@dataclass
class RequestDronesPacket( Packet ):
	company_budget: float
	packages: Dict[str, Package]

	def __init__( self, sender_id: str, company_budget: float, packages: Dict[str, Package] ):
		super().__init__( sender_id )
		self.company_budget = company_budget
		self.packages = packages

@dataclass
class ResponseDronesPacket( Packet ):
	packages: List[str]
	cost: float

	def __init__( self, sender_id: str, packages: List[str], cost: float ):
		super().__init__( sender_id )
		self.packages = packages
		self.cost = cost

@dataclass
class DeliveryPacket( Packet ):
	order_id: str
	item_id: str
	package: Package

	def __init__( self, sender_id: str, order_id: str, item_id: str, package: Package ):
		super().__init__( sender_id )
		self.order_id = order_id
		self.item_id = item_id
		self.package = package

@dataclass
class BuyItemPacket( Packet ):
	order_id: str
	item_id: str
	payment: float
	client_location: GeoCoord

	def __init__( self, sender_id: str, order_id: int, item_id: str, payment: float, client_location: GeoCoord ):
		super().__init__( sender_id )
		self.order_id = order_id
		self.payment = payment
		self.item_id = item_id
		self.client_location = client_location

@dataclass
class FetchInventoryPacket( Packet ):
	def __init__( self, sender_id: str ):
		super().__init__( sender_id )

@dataclass
class InventoryPacket( Packet ):
	inventory: Dict[str, Item]

	def __init__( self, sender_id: str, inventory: Dict[str, Item] ):
		super().__init__( sender_id )
		self.inventory = inventory