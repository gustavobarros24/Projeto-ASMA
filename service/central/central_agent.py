from typing import List, Dict, Optional
from spade.agent import Agent
from utils.logger import get_logger
from common.drone_info import DroneInfo
from .behaviour.receiver_behaviour import ReceiverBehaviour
from .behaviour.negotiate_behaviour import NegotiateBehaviour
from .web_api import CentralWebAPI
from config.config import *


log = get_logger( name = CENTRAL_ID, log_dir = "logs", console = True )

# Set to True to disable central drones and force negotiation for testing
FORCE_NEGOTIATION_TEST = False

class CentralAgent(Agent):
    drones: List[DroneInfo]
    companies: List[str]
    negotiate_behaviour: Optional[NegotiateBehaviour]

    def __init__(self, jid: str, password: str, drones_data: List[Dict], companies: List[str] = None):
        super().__init__(jid, password)
        self.drones = []
        self.companies = companies or []
        self.negotiate_behaviour = None
        self._load_drones(drones_data)

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
            # If testing negotiation, mark all central drones as unavailable
            if FORCE_NEGOTIATION_TEST:
                drone.available = False
            self.drones.append(drone)

    async def setup(self):
        log.info(f"Central agent started: {self.jid.node}")
        log.info(f"Managing {len(self.drones)} drones.")
        log.info(f"Known companies: {self.companies}")
        
        if FORCE_NEGOTIATION_TEST:
            log.warning("FORCE_NEGOTIATION_TEST is ON - Central drones are disabled!")

        # Add negotiate behaviour if companies are registered
        if self.companies:
            self.negotiate_behaviour = NegotiateBehaviour(self.companies)
            self.add_behaviour(self.negotiate_behaviour)
            log.info("Negotiate behaviour added for drone lending between companies")

        self.add_behaviour(ReceiverBehaviour(log))
        
        # Setup web API (delegated to separate module)
        web_api = CentralWebAPI(self)
        web_api.setup_routes()
        web_api.start(hostname="127.0.0.1", port=10000)
        
        log.info("Web API started at http://127.0.0.1:10000")
        log.info("For dashboard, run: python service/central/web_server.py")