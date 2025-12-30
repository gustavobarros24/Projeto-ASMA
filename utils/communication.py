from spade.message import Message
from config.config import *
from common.packet import *

"""
===============================================================================

	Communication: helpers for communication

===============================================================================
"""

def new_message( packet: Packet, target_id: str ) -> Message:
	seller_jid = get_agent_jid( target_id )
	msg = Message( to = seller_jid )
	msg.body = packet.serialize()
	return msg