from dataclasses import dataclass
from utils.utils import *

"""
===============================================================================

	Item

===============================================================================
"""

@dataclass( slots = True, unsafe_hash = True )
class Item:
	id: str
	company_id: str
	name: str
	description: str
	price_usd: float
	weight_kg: float

	def __init__( self, id: str, company_id: str, name: str, description: str, price_usd: float, weight_kg: float ):
		self.id = id
		self.company_id = company_id
		self.description = description
		self.name = name
		self.price_usd = price_usd
		self.weight_kg = weight_kg