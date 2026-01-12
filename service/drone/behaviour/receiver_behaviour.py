from spade.behaviour import CyclicBehaviour
from common.packet import Packet, PackageInfo, RefuseJobPacket
from utils.communication import new_message
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
            if not self.agent.drone_info.available:
                reason = f"Drone is busy (battery: {self.agent.drone_info.battery_percent}%)"
                self.log.warning(f"Refusing job from {packet.sender_id}: {reason}")

                refuse_packet = RefuseJobPacket(
                    sender_id=self.agent.jid.node,
                    package=packet.package,
                    reason=reason
                )
                response_msg = new_message(refuse_packet, packet.sender_id)
                await self.send(response_msg)
                return

            self.log.info(f"Received delivery request...")
            delivery_behaviour = DeliveryBehaviour(packet, log=self.log)
            self.agent.add_behaviour(delivery_behaviour)

        else:
            self.log.warning(f"Unexpected packet type: {type(packet)}")