from __future__ import annotations
from dataclasses import dataclass
from utils.utils import *
from .item import *

"""
===============================================================================

	Package

===============================================================================
"""

@dataclass( frozen = True, slots = True, unsafe_hash = True )
class Package:
	order_id: str
	item: Item

	def __init__( self, order_id: str, item: Item ):
		self.order_id = order_id
		self.item = item
