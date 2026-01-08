from spade.behaviour import CyclicBehaviour
from common.packet import Packet, PackageInfo
from utils.logger import logging
from .delivery_behaviour import DeliveryBehaviour

_TIMEOUT = 1  # segundos


class ReceiverBehaviour(CyclicBehaviour):
    def __init__(self, *, log=None):
        super().__init__()
        self.log = log

    async def run(self):
        msg = await self.receive(timeout=_TIMEOUT)

        if not msg:
            return

        try:
            packet = Packet.deserialize(msg.body)
        except Exception as e:
            self.log.warning(f"Failed to deserialize packet: {e}")
            return

        if isinstance(packet, PackageInfo):
            self.log.info(f"Received delivery request...")
            delivery_behaviour = DeliveryBehaviour(packet, log=self.log)
            self.agent.add_behaviour(delivery_behaviour)

        else:
            self.log.warning(f"Unexpected packet type: {type(packet)}")