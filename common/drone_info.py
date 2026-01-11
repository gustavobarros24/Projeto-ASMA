from dataclasses import dataclass
from utils.utils import *
from .geo_coord import *
from .package import *
from config.config import *

"""
===============================================================================

	Drone info

===============================================================================
"""

_BASE_CONSUMPTION_PER_KM = 0.8      # % battery per km (empty drone)
_WEIGHT_FACTOR_PER_KG = 0.2         # extra % per km per kg
_SPEED_FACTOR_PER_KMH = 0.01        # extra % per km per km/h
_SAFETY_MARGIN = 5.0                # % battery kept in reserve

_SIMULATION_SPEED_SCALE = 100.0  # speed factor for the simulation (e.g., 100.0 means the simulation runs 100x faster than real-time)

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
		self.current_position = GeoCoord( CENTRAL_LAT, CENTRAL_LON )
		self.available = True

	def can_send( self, package: Package ) -> bool:
		battery_needed = self.battery_needed_percent( package )
		if self.battery_percent >= battery_needed:
			return True
		else:
			print( f"Drone { self.id } reject: battery { self.battery_percent }% < needed {battery_needed:.2f}%" )
			return False

	def calculate_consumption(self, distance_km: float, item_weight_kg: float = 0.0) -> float:
		per_km_cost = (
				_BASE_CONSUMPTION_PER_KM
				+ item_weight_kg * _WEIGHT_FACTOR_PER_KG
				+ self.speed_kmh * _SPEED_FACTOR_PER_KMH
		)
		return distance_km * per_km_cost

	def calculate_delivery_battery(self, dist_empty_km: float, dist_loaded_km: float, package_weight: float) -> float:
		cost_empty = self.calculate_consumption(dist_empty_km, 0.0)
		cost_loaded = self.calculate_consumption(dist_loaded_km, package_weight)
		return cost_empty + cost_loaded + _SAFETY_MARGIN

	def battery_needed_percent(self, package: Package) -> float:
		distance = self.current_position.distance_to(package.location)
		return self.calculate_consumption(distance, package.item.weight_kg) + _SAFETY_MARGIN

	def calculate_flight_duration(self, distance_km: float) -> float:
		return (distance_km / self.speed_kmh) * 3600 / _SIMULATION_SPEED_SCALE
