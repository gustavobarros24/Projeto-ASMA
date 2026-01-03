from typing import List, Dict
from spade.agent import Agent
from utils.logger import get_logger
from common.drone_info import DroneInfo
from .behaviour.receiver_behaviour import ReceiverBehaviour


class CentralAgent(Agent):
    drones: List[DroneInfo]

    def __init__(self, jid: str, password: str, drones_data: List[Dict]):
        super().__init__(jid, password)
        self.drones = []
        self._load_drones(drones_data)

        self.log = get_logger(
            name="central",
            log_dir="logs",
            console=True
        )

    def _load_drones(self, drones_data:List[Dict]):
        for d in drones_data:
            info = d['info']
            drone = DroneInfo(
                id=info['id'],
                model=info['model'],
                capacity_kg=info['capacity_kg'],
                speed_kmh=info['speed_kmh'],
                battery_percent=info['battery_percent']
            )
            self.drones.append(drone)

    async def setup(self):
        self.log.info(f"Central agent started: {self.jid.node}")
        self.log.info(f"Managing {len(self.drones)} drones.")

        self.add_behaviour(ReceiverBehaviour())