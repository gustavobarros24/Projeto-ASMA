from spade.agent import Agent
from utils.logger import get_logger
from common.drone_info import DroneInfo
from .behaviour.receiver_behaviour import ReceiverBehaviour
from .behaviour.charging_behaviour import ChargingBehaviour
from .behaviour.status_update_behaviour import StatusUpdateBehaviour
from typing import Dict


class DroneAgent(Agent):
    drone_info: DroneInfo

    def __init__(self, jid: str, password: str, drone_info: Dict):
        super().__init__(jid, password)
        info = drone_info
        self.drone_info = DroneInfo(
            id=info['id'],
            model=info['model'],
            capacity_kg=info['capacity_kg'],
            speed_kmh=info['speed_kmh'],
            battery_percent=info['battery_percent']
        )

        self.log = get_logger(
            name=f"drone.{self.jid.node}",
            log_dir="logs",
            console=True
        )

    async def setup(self):
        self.log.info(f"Drone agent started: {self.jid.node} (battery: {self.drone_info.battery_percent}%)")
        self.add_behaviour(ReceiverBehaviour(log=self.log))
        self.add_behaviour(ChargingBehaviour(period=2, log=self.log))
        self.add_behaviour(StatusUpdateBehaviour(period=3))