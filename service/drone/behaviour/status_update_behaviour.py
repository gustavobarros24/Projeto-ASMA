from spade.behaviour import PeriodicBehaviour
from common.packet import DroneStatusPacket
from utils.communication import new_message
from config.config import CENTRAL_ID


class StatusUpdateBehaviour(PeriodicBehaviour):
    async def run(self):
        drone_info = self.agent.drone_info

        #self.agent.log.debug(f"Sending status update: (battery: {drone_info.battery_percent}%)")

        packet = DroneStatusPacket(self.agent.jid.node, drone_info)
        msg = new_message(packet, CENTRAL_ID)
        await self.send(msg)