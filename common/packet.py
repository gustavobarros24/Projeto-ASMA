import jsonpickle

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List
from .package import Package
from .geo_coord import *
from .item import *
from .drone_info import *


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
class RequestDronePacket( Packet ):
	company_budget: float
	package_weight: float
	client_location: GeoCoord
	pickup_location: GeoCoord

	def __init__( self, sender_id: str, company_budget: float, package_weight: float, client_location: GeoCoord, pickup_location: GeoCoord ):
		super().__init__( sender_id )
		self.company_budget = company_budget
		self.package_weight = package_weight
		self.client_location = client_location
		self.pickup_location = pickup_location

@dataclass
class ResponseDronePacket( Packet ):
	drone: Optional[DroneInfo]
	cost: float

	def __init__( self, sender_id: str, drone: Optional[DroneInfo], cost: float ):
		super().__init__( sender_id )
		self.drone = drone
		self.cost = cost

@dataclass
class PackageInfo( Packet ):
	package: Package

	def __init__( self, sender_id: str, package: Package ):
		super().__init__( sender_id )
		self.package = package

@dataclass
class DeliveryPacket( Packet ):
	package: Package

	def __init__( self, sender_id: str, package: Package ):
		super().__init__( sender_id )
		self.package = package

@dataclass
class BuyItemPacket( Packet ):
	order_id: str
	item_id: str
	client_location: GeoCoord

	def __init__( self, sender_id: str, order_id: str, item_id: str, client_location: GeoCoord ):
		super().__init__( sender_id )
		self.order_id = order_id
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


# ============================================================================
# Drone Lending Negotiation Packets
# ============================================================================

@dataclass
class RequestDroneLendPacket( Packet ):
	"""Central asks companies if they have available drones to lend."""
	request_id: str
	package_weight: float
	client_location: GeoCoord
	pickup_location: GeoCoord
	requester_company_id: str

	def __init__( self, sender_id: str, request_id: str, package_weight: float, 
				  client_location: GeoCoord, pickup_location: GeoCoord, requester_company_id: str ):
		super().__init__( sender_id )
		self.request_id = request_id
		self.package_weight = package_weight
		self.client_location = client_location
		self.pickup_location = pickup_location
		self.requester_company_id = requester_company_id


@dataclass
class ResponseDroneLendPacket( Packet ):
	"""Company responds to central with available drone (or None)."""
	request_id: str
	has_drone: bool
	drone: Optional[DroneInfo]
	lending_cost: float

	def __init__( self, sender_id: str, request_id: str, has_drone: bool, 
				  drone: Optional[DroneInfo] = None, lending_cost: float = 0.0 ):
		super().__init__( sender_id )
		self.request_id = request_id
		self.has_drone = has_drone
		self.drone = drone
		self.lending_cost = lending_cost


@dataclass
class ConfirmDroneLendPacket( Packet ):
	"""Central confirms the drone lending to the lender company."""
	request_id: str
	drone_id: str
	requester_company_id: str
	accepted: bool

	def __init__( self, sender_id: str, request_id: str, drone_id: str, 
				  requester_company_id: str, accepted: bool ):
		super().__init__( sender_id )
		self.request_id = request_id
		self.drone_id = drone_id
		self.requester_company_id = requester_company_id
		self.accepted = accepted


@dataclass
class DroneLentPacket( Packet ):
	"""Central notifies the requester company that a drone has been lent to them."""
	request_id: str
	drone: DroneInfo
	lender_company_id: str
	lending_cost: float

	def __init__( self, sender_id: str, request_id: str, drone: DroneInfo, 
				  lender_company_id: str, lending_cost: float ):
		super().__init__( sender_id )
		self.request_id = request_id
		self.drone = drone
		self.lender_company_id = lender_company_id
		self.lending_cost = lending_cost


@dataclass
class ReturnDronePacket( Packet ):
	"""Requester company returns the drone after delivery is complete."""
	drone_id: str
	lender_company_id: str

	def __init__( self, sender_id: str, drone_id: str, lender_company_id: str ):
		super().__init__( sender_id )
		self.drone_id = drone_id
		self.lender_company_id = lender_company_id


@dataclass
class DroneReturnedPacket( Packet ):
	"""Central notifies lender company that their drone has been returned."""
	drone_id: str

	def __init__( self, sender_id: str, drone_id: str ):
		super().__init__( sender_id )
		self.drone_id = drone_id