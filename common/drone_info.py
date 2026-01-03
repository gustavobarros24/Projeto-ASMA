from dataclasses import dataclass
from utils.utils import *
from .geo_coord import *
from .package import *

"""
===============================================================================

	Drone info

===============================================================================
"""

_CENTRAL_LAT = 41.888866
_CENTRAL_LON = -87.626396

_BASE_CONSUMPTION_PER_KM = 1.0      # % battery per km (empty drone)
_WEIGHT_FACTOR_PER_KG = 0.3         # extra % per km per kg
_SPEED_FACTOR_PER_KMH = 0.01        # extra % per km per km/h
_SAFETY_MARGIN = 5.0                # % battery kept in reserve

@dataclass( slots = True, unsafe_hash = True )
class DroneInfo:
	id: str
	model: str
	capacity_kg: float
	speed_kmh: float
	battery_percent: int
	current_position: GeoCoord
	available: bool

	def __init__( self, id: str, model: str, capacity_kg: float, speed_kmh: float, battery_percent: int ):
		self.id = id
		self.model = model
		self.capacity_kg = capacity_kg
		self.speed_kmh = speed_kmh
		self.battery_percent = battery_percent
		self.current_position = GeoCoord( _CENTRAL_LAT, _CENTRAL_LON )
		self.available = True

	def can_send( self, package: Package ) -> bool:
		if self.battery_percent >= self.battery_needed_percent( package ):
			return True
		else:
			print( f"Drone { self.id } reject: battery { self.battery_percent }% < needed {self.battery_needed_percent( package ):.2f}%" )
			return False

	def battery_needed_percent( self, package: Package ) -> float:
		distance = self.current_position.distance_to( package.location )

		per_km_cost = (
				_BASE_CONSUMPTION_PER_KM
				+ package.item.weight_kg * _WEIGHT_FACTOR_PER_KG
				+ self.speed_kmh * _SPEED_FACTOR_PER_KMH
		)

		return distance * per_km_cost + _SAFETY_MARGIN