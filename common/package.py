from dataclasses import dataclass
from utils.utils import *
from .item import *
from .geo_coord import *

"""
===============================================================================

	Package

===============================================================================
"""

@dataclass( slots = True, unsafe_hash = True )
class Package:
	order_id: str
	client_id: str
	location: GeoCoord
	item: Item

	def __init__( self, order_id: str, client_id: str, location: GeoCoord, item: Item ):
		self.order_id = order_id
		self.client_id = client_id
		self.location = location
		self.item = item
