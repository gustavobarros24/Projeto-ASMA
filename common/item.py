from __future__ import annotations
from dataclasses import dataclass
from utils.utils import *

"""
===============================================================================

	Item

===============================================================================
"""

@dataclass( slots = True, unsafe_hash = True )
class Item:
	item_id: str
	company_id: str
	name: str
	description: str
	price_usd: float
	weight_kg: float

	def __init__( self, item_id: str, company_id: str, name: str, description: str, price_usd: float, weight_kg: float ):
		self.item_id = item_id
		self.company_id = company_id
		self.description = description
		self.name = name
		self.price_usd = price_usd
		self.weight_kg = weight_kg