import spade
import asyncio
import uuid

from utils.logger import get_logger
from config.config import *
from common.geo_coord import GeoCoord
from common.packet import (
    Packet, RequestDronePacket, ResponseDronePacket, DroneLentPacket,
    RequestDroneLendPacket, ResponseDroneLendPacket, ConfirmDroneLendPacket,
    ReturnDronePacket, DroneReturnedPacket
)
from common.drone_info import DroneInfo
from utils.communication import new_message
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour

log = get_logger(name="test_negotiation", log_dir="logs", console=True)

_DEFAULT_PASSWORD = "123"
_DELIVERY_TIME = 3  # seconds to simulate delivery

# Company IDs to use in test
TEST_COMPANIES = ["COMPANY_A", "COMPANY_B", "COMPANY_C"]


class SimpleCentralAgent(Agent):
    """Central simplificado para teste - SEM drones próprios (força negociação)."""
    
    def __init__(self, jid: str, password: str, companies: list):
        super().__init__(jid, password)
        self.companies = companies
        self.drones = []  # Sem drones - força negociação
    
    async def setup(self):
        log.info(f"[CENTRAL] Started with companies: {self.companies}")
        log.info(f"[CENTRAL] No drones available - will negotiate with companies")
        self.add_behaviour(CentralReceiverBehaviour(self.companies))


class CentralReceiverBehaviour(CyclicBehaviour):
    def __init__(self, companies: list):
        super().__init__()
        self.companies = companies
        self.pending_requests = {}  # request_id -> {original_packet, responses, requester}
    
    async def run(self):
        msg = await self.receive(timeout=1)
        if not msg:
            return
        
        try:
            packet = Packet.deserialize(msg.body)
        except Exception as e:
            log.warning(f"[CENTRAL] Failed to deserialize: {e}")
            return
        
        if isinstance(packet, RequestDronePacket):
            log.info(f"[CENTRAL] Received drone request from {packet.sender_id}")
            await self.start_negotiation(packet)
        elif isinstance(packet, ResponseDroneLendPacket):
            log.info(f"[CENTRAL] Received lend response from {packet.sender_id}: has_drone={packet.has_drone}")
            await self.handle_lend_response(packet)
        elif isinstance(packet, ReturnDronePacket):
            log.info(f"[CENTRAL] Received drone return from {packet.sender_id}")
            await self.handle_drone_return(packet)
    
    async def start_negotiation(self, packet: RequestDronePacket):
        request_id = str(uuid.uuid4())[:8]
        
        # Get companies to ask (exclude requester)
        companies_to_ask = [c for c in self.companies if c.upper() != packet.sender_id.upper()]
        
        log.info(f"[CENTRAL] Starting negotiation {request_id}")
        log.info(f"[CENTRAL] Asking companies: {companies_to_ask}")
        
        self.pending_requests[request_id] = {
            'original': packet,
            'responses': [],
            'expected': len(companies_to_ask)
        }
        
        # Send request to all companies
        lend_request = RequestDroneLendPacket(
            sender_id=CENTRAL_ID,
            request_id=request_id,
            package_weight=packet.package_weight,
            client_location=packet.client_location,
            pickup_location=packet.pickup_location,
            requester_company_id=packet.sender_id
        )
        
        for company_id in companies_to_ask:
            msg = new_message(lend_request, company_id)
            await self.send(msg)
            log.info(f"[CENTRAL] Sent lend request to {company_id}")
    
    async def handle_lend_response(self, packet: ResponseDroneLendPacket):
        request_id = packet.request_id
        
        if request_id not in self.pending_requests:
            log.warning(f"[CENTRAL] Unknown request_id: {request_id}")
            return
        
        pending = self.pending_requests[request_id]
        pending['responses'].append(packet)
        
        log.info(f"[CENTRAL] Got {len(pending['responses'])}/{pending['expected']} responses")
        
        # Check if we have all responses or got a positive one
        if packet.has_drone or len(pending['responses']) >= pending['expected']:
            await self.finalize_negotiation(request_id)
    
    async def finalize_negotiation(self, request_id: str):
        pending = self.pending_requests[request_id]
        original = pending['original']
        
        # Find best offer
        best = None
        for resp in pending['responses']:
            if resp.has_drone and resp.drone:
                if best is None or resp.lending_cost < best.lending_cost:
                    best = resp
        
        if best:
            log.info(f"[CENTRAL] [OK] Found drone {best.drone.id} from {best.sender_id} (cost: {best.lending_cost})")
            
            # Confirm to lender
            confirm = ConfirmDroneLendPacket(
                sender_id=CENTRAL_ID,
                request_id=request_id,
                drone_id=best.drone.id,
                requester_company_id=original.sender_id,
                accepted=True
            )
            await self.send(new_message(confirm, best.sender_id))
            
            # Notify requester
            lent = DroneLentPacket(
                sender_id=CENTRAL_ID,
                request_id=request_id,
                drone=best.drone,
                lender_company_id=best.sender_id,
                lending_cost=best.lending_cost
            )
            await self.send(new_message(lent, original.sender_id))
            log.info(f"[CENTRAL] [OK] Drone {best.drone.id} assigned to {original.sender_id}")
        else:
            log.warning(f"[CENTRAL] [FAIL] No drones available from any company")
            response = ResponseDronePacket(CENTRAL_ID, None, 0.0)
            await self.send(new_message(response, original.sender_id))
        
        del self.pending_requests[request_id]

    async def handle_drone_return(self, packet: ReturnDronePacket):
        """Handle drone return and notify the lender company."""
        log.info(f"[CENTRAL] Processing drone return: {packet.drone_id} -> {packet.lender_company_id}")
        
        # Notify the lender that their drone is back
        returned_packet = DroneReturnedPacket(
            sender_id=CENTRAL_ID,
            drone_id=packet.drone_id
        )
        await self.send(new_message(returned_packet, packet.lender_company_id))
        log.info(f"[CENTRAL] [OK] Notified {packet.lender_company_id} that drone {packet.drone_id} is returned")


class TestCompanyAgent(Agent):
    """Empresa de teste que responde a pedidos de empréstimo."""
    
    def __init__(self, jid: str, password: str, has_drone: bool = True):
        super().__init__(jid, password)
        self.has_drone = has_drone
        self.drone = None
        self.drone_lent = False  # Track if drone is currently lent out
        if has_drone:
            self.drone = DroneInfo(
                id=f"DRONE_{jid.split('@')[0].upper()}",
                model="Test Drone",
                capacity_kg=10.0,
                speed_kmh=80,
                battery_percent=100
            )
    
    async def setup(self):
        log.info(f"[{self.jid.node.upper()}] Started (has_drone: {self.has_drone})")
        self.add_behaviour(CompanyReceiverBehaviour(self.drone))


class CompanyReceiverBehaviour(CyclicBehaviour):
    def __init__(self, drone: DroneInfo):
        super().__init__()
        self.drone = drone
    
    async def run(self):
        msg = await self.receive(timeout=1)
        if not msg:
            return
        
        try:
            packet = Packet.deserialize(msg.body)
        except:
            return
        
        company = self.agent.jid.node.upper()
        
        if isinstance(packet, RequestDroneLendPacket):
            log.info(f"[{company}] Received lend request for {packet.requester_company_id}")
            
            if self.drone and not self.agent.drone_lent:
                log.info(f"[{company}] [OK] Offering drone {self.drone.id}")
                response = ResponseDroneLendPacket(
                    sender_id=self.agent.jid.node,
                    request_id=packet.request_id,
                    has_drone=True,
                    drone=self.drone,
                    lending_cost=15.0
                )
            else:
                log.info(f"[{company}] [NO] No drone available")
                response = ResponseDroneLendPacket(
                    sender_id=self.agent.jid.node,
                    request_id=packet.request_id,
                    has_drone=False
                )
            
            await self.send(new_message(response, CENTRAL_ID))
            
        elif isinstance(packet, ConfirmDroneLendPacket):
            if packet.accepted:
                self.agent.drone_lent = True
                log.info(f"[{company}] [OK] Drone lending confirmed! Drone is now with {packet.requester_company_id}")
            else:
                log.info(f"[{company}] Drone lending rejected")
                
        elif isinstance(packet, DroneLentPacket):
            log.info(f"[{company}] [OK] Received lent drone {packet.drone.id} from {packet.lender_company_id}!")
            
        elif isinstance(packet, DroneReturnedPacket):
            self.agent.drone_lent = False
            log.info(f"[{company}] [OK] *** DRONE {packet.drone_id} RETURNED! *** Drone is available again.")


class RequesterCompanyAgent(Agent):
    """Empresa que pede drone e depois faz entrega e devolve."""
    
    def __init__(self, jid: str, password: str):
        super().__init__(jid, password)
        self.borrowed_drone = None
        self.lender_company = None
    
    async def setup(self):
        log.info(f"[{self.jid.node.upper()}] Started (will request drone)")
        self.add_behaviour(RequesterReceiverBehaviour())
        self.add_behaviour(RequesterBehaviour())


class RequesterReceiverBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=1)
        if not msg:
            return
        
        try:
            packet = Packet.deserialize(msg.body)
        except:
            return
        
        company = self.agent.jid.node.upper()
        
        if isinstance(packet, DroneLentPacket):
            log.info(f"[{company}] [OK] Received lent drone {packet.drone.id} from {packet.lender_company_id}")
            self.agent.borrowed_drone = packet.drone
            self.agent.lender_company = packet.lender_company_id
            
            # Start delivery simulation
            self.agent.add_behaviour(DeliveryBehaviour(packet.drone, packet.lender_company_id))
            
        elif isinstance(packet, ResponseDronePacket):
            if packet.drone:
                log.info(f"[{company}] [OK] Got drone {packet.drone.id}")
            else:
                log.info(f"[{company}] [NO] No drone available")


class RequesterBehaviour(OneShotBehaviour):
    async def run(self):
        company = self.agent.jid.node.upper()
        
        log.info(f"[{company}] Waiting 2 seconds before requesting...")
        await asyncio.sleep(2)
        
        log.info(f"[{company}] Sending drone request to Central...")
        
        request = RequestDronePacket(
            sender_id=self.agent.jid.node,
            company_budget=1000.0,
            package_weight=2.0,
            client_location=GeoCoord(41.88, -87.63),
            pickup_location=GeoCoord(41.89, -87.62)
        )
        
        await self.send(new_message(request, CENTRAL_ID))
        log.info(f"[{company}] Request sent! Waiting for drone...")


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
        
        # Clear local reference
        self.agent.borrowed_drone = None
        self.agent.lender_company = None


async def main():
    log.info("=" * 70)
    log.info("   TESTE COMPLETO: NEGOCIACAO + ENTREGA + DEVOLUCAO")
    log.info("=" * 70)
    log.info("")
    log.info("Cenario:")
    log.info(f"  - Central: SEM drones (forca negociacao)")
    log.info(f"  - COMPANY_A: Pede drone ao Central")
    log.info(f"  - COMPANY_B: TEM drone para emprestar")
    log.info(f"  - COMPANY_C: NAO tem drone")
    log.info("")
    log.info("Fluxo esperado:")
    log.info("  1. COMPANY_A pede drone")
    log.info("  2. Central negocia com B e C")
    log.info("  3. COMPANY_B empresta drone")
    log.info("  4. COMPANY_A faz entrega (simulado)")
    log.info("  5. COMPANY_A devolve drone")
    log.info("  6. COMPANY_B recebe drone de volta")
    log.info("")
    log.info("=" * 70)
    
    await asyncio.sleep(1)
    
    agents = []
    
    try:
        # 1. Start Central (without drones)
        central = SimpleCentralAgent(
            get_agent_jid(CENTRAL_ID),
            _DEFAULT_PASSWORD,
            TEST_COMPANIES
        )
        await central.start(auto_register=True)
        agents.append(central)
        
        await asyncio.sleep(0.5)
        
        # 2. Start Company A (REQUESTER - uses special agent)
        company_a = RequesterCompanyAgent(
            get_agent_jid(TEST_COMPANIES[0]),
            _DEFAULT_PASSWORD
        )
        await company_a.start(auto_register=True)
        agents.append(company_a)
        
        # 3. Start Company B (has drone to lend)
        company_b = TestCompanyAgent(
            get_agent_jid(TEST_COMPANIES[1]),
            _DEFAULT_PASSWORD,
            has_drone=True
        )
        await company_b.start(auto_register=True)
        agents.append(company_b)
        
        # 4. Start Company C (no drone)
        company_c = TestCompanyAgent(
            get_agent_jid(TEST_COMPANIES[2]),
            _DEFAULT_PASSWORD,
            has_drone=False
        )
        await company_c.start(auto_register=True)
        agents.append(company_c)
        
        log.info("")
        log.info("All agents started. Running test...")
        log.info("")
        
        # Wait for full cycle: negotiation + delivery + return
        await asyncio.sleep(15)
        
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
