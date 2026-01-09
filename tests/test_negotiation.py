import spade
import asyncio
import uuid
import json

from ..utils.logger import get_logger
from ..utils.utils import *
from ..config.config import *
from ..common.geo_coord import GeoCoord
from ..common.packet import (
    Packet, RequestDronePacket, ResponseDronePacket, DroneLentPacket,
    RequestDroneLendPacket, ResponseDroneLendPacket, ConfirmDroneLendPacket,
    ReturnDronePacket, DroneReturnedPacket
)
from ..common.drone_info import DroneInfo
from ..utils.communication import new_message
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from service.central.central_agent import CentralAgent
from service.company.company_agent import CompanyAgent
from ..common.packet import DroneLentPacket

log = get_logger(name="test_negotiation", log_dir="logs", console=True)

_DEFAULT_PASSWORD = "123"
_DELIVERY_TIME = 3  # seconds to simulate delivery

def load_companies_from_json():
    """Load companies from JSON file."""
    with open(COMPANIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["companies"][:3]  # Use first 3 companies for testing


def load_drones_from_json():
    """Load drones from JSON file."""
    with open(DRONES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["drones"]


class DeliveryTriggerBehaviour(CyclicBehaviour):
    """Monitors for borrowed drones and triggers delivery simulation."""
    async def run(self):
        await asyncio.sleep(1)
        
        # Check if we have any borrowed drones
        if hasattr(self.agent, 'rented_drones') and len(self.agent.rented_drones) > 0:
            for drone in self.agent.rented_drones:
                # Check if this is a borrowed drone (not yet used)
                if drone.available and drone.id.startswith('DRONE'):
                    # Found a borrowed drone, start delivery!
                    log.info(f"[{self.agent.jid.node.upper()}] Found borrowed drone {drone.id}, starting delivery!")
                    
                    # Find the lender
                    lender = None
                    receiver_behaviour = None
                    for behaviour in self.agent.behaviours:
                        if hasattr(behaviour, 'borrowed_drones'):
                            receiver_behaviour = behaviour
                            if drone.id in behaviour.borrowed_drones:
                                lender = behaviour.borrowed_drones[drone.id]['lender']
                                break
                    
                    if lender:
                        # Mark drone as unavailable and start delivery
                        drone.available = False
                        self.agent.add_behaviour(DeliveryBehaviour(drone, lender))
                        # Remove this behaviour since we've triggered delivery
                        self.kill()
                        return


class RequesterBehaviour(OneShotBehaviour):
    def __init__(self, company_id: str):
        super().__init__()
        self.company_id = company_id
        
    async def run(self):
        log.info(f"[{self.company_id}] Waiting 2 seconds before requesting...")
        await asyncio.sleep(2)
        
        log.info(f"[{self.company_id}] Sending drone request to Central...")
        
        request = RequestDronePacket(
            sender_id=self.company_id.lower(),
            company_budget=1000.0,
            package_weight=2.0,
            client_location=GeoCoord(41.88, -87.63),
            pickup_location=self.agent.location  
        )
        
        await self.send(new_message(request, CENTRAL_ID))
        log.info(f"[{self.company_id}] Request sent! Waiting for drone...")


class DeliveryBehaviour(OneShotBehaviour):
    """Simula a entrega e depois devolve o drone."""
    
    def __init__(self, drone: DroneInfo, lender_company: str):
        super().__init__()
        self.drone = drone
        self.lender_company = lender_company
    
    async def run(self):
        company = self.agent.jid.node.upper()
        
        log.info(f"[{company}] ======= DELIVERY STARTED with drone {self.drone.id} =======")
        log.info(f"[{company}] Drone flying to pickup location...")
        await asyncio.sleep(_DELIVERY_TIME / 2)
        
        log.info(f"[{company}] Drone picked up package, flying to client...")
        await asyncio.sleep(_DELIVERY_TIME / 2)
        
        log.info(f"[{company}] ======= DELIVERY COMPLETE! =======")
        
        # Return the drone
        log.info(f"[{company}] Returning drone {self.drone.id} to {self.lender_company}...")
        
        return_packet = ReturnDronePacket(
            sender_id=self.agent.jid.node,
            drone_id=self.drone.id,
            lender_company_id=self.lender_company
        )
        await self.send(new_message(return_packet, CENTRAL_ID))
        
        log.info(f"[{company}] [OK] Drone return request sent to Central")


async def main():
    log.info("=" * 70)
    log.info("   TESTE COMPLETO: NEGOCIACAO + ENTREGA + DEVOLUCAO")
    log.info("   COM EMPRESAS E DRONES REAIS")
    log.info("=" * 70)
    
    # Load real companies and drones
    companies_data = load_companies_from_json()
    drones_data = load_drones_from_json()
    
    # Use first 3 companies
    company_ids = [c["id"] for c in companies_data]
    
    log.info("")
    log.info("Cenario:")
    log.info(f"  - Central: COM drones reais (mas vamos forcar negociacao)")
    log.info(f"  - {company_ids[0]}: Vai pedir drone ao Central")
    log.info(f"  - {company_ids[1]}: TEM drones proprios para emprestar")
    log.info(f"  - {company_ids[2]}: Pode ter ou nao drones")
    log.info("")
    log.info("Fluxo esperado:")
    log.info(f"  1. {company_ids[0]} pede drone")
    log.info("  2. Central negocia com outras empresas")
    log.info(f"  3. {company_ids[1]} empresta drone")
    log.info(f"  4. {company_ids[0]} faz entrega (simulado)")
    log.info(f"  5. {company_ids[0]} devolve drone")
    log.info(f"  6. {company_ids[1]} recebe drone de volta")
    log.info("")
    log.info("=" * 70)
    
    await asyncio.sleep(1)
    
    agents = []
    
    try:
        # 1. Start Central with real drones (but force negotiation)
        # Prepare drones with agent info
        drones_with_agent = []
        for drone_data in drones_data[:2]:  # Use first 2 drones
            drones_with_agent.append({
                'agent': None,  # Central doesn't use DroneAgents directly
                'info': drone_data
            })
        
        # Enable force negotiation mode
        from service.central import central_agent
        central_agent.FORCE_NEGOTIATION_TEST = True
        
        central = CentralAgent(
            get_agent_jid(CENTRAL_ID),
            _DEFAULT_PASSWORD,
            drones_with_agent,
            company_ids
        )
        await central.start(auto_register=True)
        agents.append(central)
        log.info(f"[CENTRAL] Started with {len(drones_with_agent)} drones (negotiation forced)")
        
        await asyncio.sleep(0.5)
        
        # 2. Start Company agents with real data
        for i, company_data in enumerate(companies_data):
            company_id = company_data["id"]
            location = GeoCoord(company_data["location"]["lat"], company_data["location"]["lon"])
            budget = company_data.get("annual_revenue_usd", 1000000) / 1000000  # Convert to millions
            
            company = CompanyAgent(
                get_agent_jid(company_id),
                _DEFAULT_PASSWORD,
                budget,
                location
            )
            await company.start(auto_register=True)
            agents.append(company)
            log.info(f"[{company_id}] Started at ({location.latitude:.3f}, {location.longitude:.3f})")
            
            # Add drones to AMAZON and APPLE so they can lend them
            if i == 1:  # AMAZON (second company)
                # Give AMAZON 2 drones
                drone1 = DroneInfo(
                    id=drones_data[0]["id"],
                    model=drones_data[0]["model"],
                    capacity_kg=drones_data[0]["capacity_kg"],
                    speed_kmh=drones_data[0]["speed_kmh"],
                    battery_percent=drones_data[0]["battery_percent"]
                )
                drone1.current_position = location
                drone1.available = True  # Make sure it's available
                company.rented_drones.append(drone1)
                log.info(f"[{company_id}] Added drone {drone1.id} for lending (available={drone1.available}, capacity={drone1.capacity_kg}kg)")
                
            elif i == 2:  # APPLE (third company)
                # Give APPLE 1 drone
                drone2 = DroneInfo(
                    id=drones_data[1]["id"],
                    model=drones_data[1]["model"],
                    capacity_kg=drones_data[1]["capacity_kg"],
                    speed_kmh=drones_data[1]["speed_kmh"],
                    battery_percent=drones_data[1]["battery_percent"]
                )
                drone2.current_position = location
                drone2.available = True  # Make sure it's available
                company.rented_drones.append(drone2)
                log.info(f"[{company_id}] Added drone {drone2.id} for lending (available={drone2.available}, capacity={drone2.capacity_kg}kg)")
            
            await asyncio.sleep(0.3)
        
        # 3. Add requester behaviour to first company
        requester_company = agents[1]  # First company agent (after central)
        log.info(f"[{company_ids[0]}] Will request drone in 2 seconds...")
        requester_company.add_behaviour(RequesterBehaviour(company_ids[0]))
        
        # Add a watcher to start delivery when drone arrives
        requester_company.add_behaviour(DeliveryTriggerBehaviour())
        
        log.info("")
        log.info("All agents started. Running test...")
        log.info("")
        
        # Wait for full cycle: negotiation + delivery + return
        await asyncio.sleep(20)
        
    except KeyboardInterrupt:
        log.info("Interrupted")
    except Exception as e:
        log.critical(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        log.info("")
        log.info("Shutting down...")
        for agent in agents:
            await agent.stop()
        log.info("Done!")


if __name__ == "__main__":
    spade.run(main())
