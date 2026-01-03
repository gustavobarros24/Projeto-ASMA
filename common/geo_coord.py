import random

from dataclasses import dataclass
from math import radians, sin, cos, asin, sqrt
from typing import Optional, Tuple


"""
===============================================================================

	GeoCoord: geographic coordinate WGS-84 (latitude, longitude, altitude).

===============================================================================
"""

_WGS84_EARTH_RADIUS_M = 6378137.0  # mean radius for haversine
_LAT_MIN: float = -90.0
_LAT_MAX: float = 90.0
_LON_MIN: float = -180.0
_LON_MAX: float = 180.0
_ALT_MIN = 0.0
_ALT_MAX = 2000
_TOLERANCE_LATLON_DEGREE = 1e-7  # ~1 cm at equator
_TOLERANCE_ALT_M = 0.01       # 1 cm

@dataclass( slots = True, unsafe_hash = True )
class GeoCoord:
	latitude: float
	longitude: float
	altitude_m: Optional[float] = None

	def __init__( self, latitude: float, longitude: float, altitude_m: Optional[float] = None ):
		if not _LAT_MIN <= latitude <= _LAT_MAX:
			raise ValueError( f"Latitude out of range: { latitude }" )

		if not _LON_MIN <= longitude < _LON_MAX:
			raise ValueError( f"Longitude out of range: { longitude }" )

		self.latitude = latitude
		self.longitude = longitude
		self.altitude_m = altitude_m

	def latlon( self ) -> Tuple[float, float]:
		return ( self.latitude, self.longitude )

	def latlonalt( self ) -> Tuple[float, float, Optional[float]]:
		return ( self.latitude, self.longitude, self.altitude_m )

	def distance_to( self, other: "GeoCoord" ) -> float:
		# harvsine formula
		self._validate_other( other )

		lat1, lon1 = radians( self.latitude ), radians( self.longitude )
		lat2, lon2 = radians( other.latitude ), radians( other.longitude )

		dlat = lat2 - lat1
		dlon = lon2 - lon1

		a = sin( dlat / 2 )**2 + cos( lat1 ) * cos( lat2 ) * sin( dlon / 2 )**2
		c = 2 * asin( sqrt( a ) )

		return ( _WGS84_EARTH_RADIUS_M * c ) / 1000.0 # for km

	def almost_equals( self, other: "GeoCoord", *, tol_deg: float = _TOLERANCE_LATLON_DEGREE, tol_alt_m: float = _TOLERANCE_ALT_M ) -> bool:
		# use this function to compare, because of floating point precision issues
		self._validate_other( other )

		if abs( self.latitude - other.latitude ) > tol_deg:
			return False
		if abs( self.longitude - other.longitude ) > tol_deg:
			return False

		if self.altitude_m is None or other.altitude_m is None:
			return self.altitude_m is other.altitude_m

		return abs( self.altitude_m - other.altitude_m ) <= tol_alt_m

	def _validate_other( self, other: "GeoCoord" ) -> None:
		if not isinstance( other, GeoCoord ):
			raise TypeError( f"Expected GeoCoord, got {type( other )!r}")

	@staticmethod
	def random_geocoord( *, min_alt_m: float = _ALT_MIN, max_alt_m: float = _ALT_MAX, with_altitude: bool = True ) -> "GeoCoord":
		latitude = random.uniform( _LAT_MIN, _LAT_MAX )
		longitude = random.uniform( _LON_MIN, _LON_MAX )

		altitude: Optional[float]
		if with_altitude:
			altitude = random.uniform( min_alt_m, max_alt_m )
		else:
			altitude = None

		return GeoCoord(
			latitude = latitude,
			longitude = longitude,
			altitude_m = altitude,
		)
