import asyncio
import uuid
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from spade.behaviour import CyclicBehaviour
from common.packet import (
    Packet, RequestDronePacket, ResponseDronePacket,
    RequestDroneLendPacket, ResponseDroneLendPacket,
    ConfirmDroneLendPacket, DroneLentPacket
)
from common.drone_info import DroneInfo
from utils.communication import new_message
from config.config import CENTRAL_ID

log = logging.getLogger(__name__)

# Constants
_NEGOTIATION_TIMEOUT = 8  # seconds to wait for company responses

@dataclass
class PendingNegotiation:
    """Stores data about an ongoing negotiation."""
    request_id: str
    original_request: RequestDronePacket
    responses: Dict[str, ResponseDroneLendPacket] = field(default_factory=dict)
    companies_asked: List[str] = field(default_factory=list)
    created_at: float = 0.0


class NegotiateBehaviour(CyclicBehaviour):
    """
    Behaviour that handles the negotiation of drone lending between companies.
    
    When the central agent receives a drone request and has no available drones,
    this behaviour asks all other companies if they have drones available to lend.
    """

    def __init__(self, companies: List[str]):
        super().__init__()
        self.companies = companies  # List of company IDs
        self.pending_negotiations: Dict[str, PendingNegotiation] = {}
        self.response_queues: Dict[str, asyncio.Queue] = {}

    async def run(self):
        # esté run() não deve fazer receive de mensagens, pois pode entrar em conflito com o ReceiveBehaviour
        # apenas o ReceiveBehaviour recebe mensagens da rede.

        await self._check_timeouts()

        await asyncio.sleep(1)

    async def start_negotiation(self, request: RequestDronePacket) -> Optional[DroneInfo]:
        """
        Start a negotiation to find a drone from other companies.
        
        Args:
            request: The original drone request from a company
            
        Returns:
            DroneInfo if a drone was found and lent, None otherwise
        """
        request_id = str(uuid.uuid4())
        
        # Get all companies except the requester
        other_companies = [c for c in self.companies if c.upper() != request.sender_id.upper()]
        
        if not other_companies:
            log.warning("No other companies to negotiate with")
            return None

        log.info(f"Starting drone lending negotiation {request_id} for {request.sender_id}")
        log.info(f"Asking {len(other_companies)} companies: {other_companies}")

        # Create pending negotiation record
        negotiation = PendingNegotiation(
            request_id=request_id,
            original_request=request,
            companies_asked=other_companies,
            created_at=asyncio.get_event_loop().time()
        )
        self.pending_negotiations[request_id] = negotiation

        # Create a queue to collect responses
        response_queue = asyncio.Queue()
        self.response_queues[request_id] = response_queue

        # Send request to all other companies
        lend_request = RequestDroneLendPacket(
            sender_id=CENTRAL_ID,
            request_id=request_id,
            package_weight=request.package_weight,
            client_location=request.client_location,
            pickup_location=request.pickup_location,
            requester_company_id=request.sender_id
        )

        for company_id in other_companies:
            msg = new_message(lend_request, company_id)
            await self.send(msg)
            log.info(f"Sent drone lend request to {company_id}")

        # Wait for responses
        result = await self._wait_for_responses(request_id, len(other_companies))
        
        # Clean up
        if request_id in self.response_queues:
            del self.response_queues[request_id]
        if request_id in self.pending_negotiations:
            del self.pending_negotiations[request_id]

        return result

    async def _wait_for_responses(self, request_id: str, expected_count: int) -> Optional[DroneInfo]:
        """Wait for responses and select the best drone offer."""
        response_queue = self.response_queues.get(request_id)
        if not response_queue:
            return None

        responses: List[ResponseDroneLendPacket] = []
        start_time = asyncio.get_event_loop().time()

        while len(responses) < expected_count:
            elapsed = asyncio.get_event_loop().time() - start_time
            remaining = _NEGOTIATION_TIMEOUT - elapsed
            
            if remaining <= 0:
                log.info(f"Negotiation {request_id} timed out after {_NEGOTIATION_TIMEOUT}s")
                break

            try:
                response = await asyncio.wait_for(response_queue.get(), timeout=remaining)
                responses.append(response)
                log.info(f"Received response from {response.sender_id}: has_drone={response.has_drone}")
            except asyncio.TimeoutError:
                break

        # Find best offer (drone available with lowest cost)
        best_offer: Optional[ResponseDroneLendPacket] = None
        for response in responses:
            if response.has_drone and response.drone:
                if best_offer is None or response.lending_cost < best_offer.lending_cost:
                    best_offer = response

        if not best_offer:
            log.info(f"No drones available from other companies for negotiation {request_id}")
            return None

        # Confirm the lending with the selected company
        negotiation = self.pending_negotiations.get(request_id)
        if not negotiation:
            return None

        # Send confirmation to the lender
        confirm_packet = ConfirmDroneLendPacket(
            sender_id=CENTRAL_ID,
            request_id=request_id,
            drone_id=best_offer.drone.id,
            requester_company_id=negotiation.original_request.sender_id,
            accepted=True
        )
        confirm_msg = new_message(confirm_packet, best_offer.sender_id)
        await self.send(confirm_msg)
        log.info(f"Sent confirmation to {best_offer.sender_id} for drone {best_offer.drone.id}")

        # Notify other companies that their offers were not accepted
        for response in responses:
            if response.has_drone and response.sender_id != best_offer.sender_id:
                reject_packet = ConfirmDroneLendPacket(
                    sender_id=CENTRAL_ID,
                    request_id=request_id,
                    drone_id=response.drone.id if response.drone else "",
                    requester_company_id=negotiation.original_request.sender_id,
                    accepted=False
                )
                reject_msg = new_message(reject_packet, response.sender_id)
                await self.send(reject_msg)

        # Notify the requester company about the lent drone
        lent_packet = DroneLentPacket(
            sender_id=CENTRAL_ID,
            request_id=request_id,
            drone=best_offer.drone,
            lender_company_id=best_offer.sender_id,
            lending_cost=best_offer.lending_cost
        )
        lent_msg = new_message(lent_packet, negotiation.original_request.sender_id)
        await self.send(lent_msg)
        log.info(f"Notified {negotiation.original_request.sender_id} about lent drone {best_offer.drone.id}")

        return best_offer.drone

    async def _handle_lend_response(self, packet: ResponseDroneLendPacket):
        """Handle a response from a company about drone availability."""
        request_id = packet.request_id
        
        if request_id not in self.response_queues:
            log.warning(f"Received response for unknown negotiation: {request_id}")
            return

        # Add response to the queue
        await self.response_queues[request_id].put(packet)

    async def _check_timeouts(self):
        """Check for and clean up timed-out negotiations."""
        current_time = asyncio.get_event_loop().time()
        timed_out = []
        
        for request_id, negotiation in self.pending_negotiations.items():
            if current_time - negotiation.created_at > _NEGOTIATION_TIMEOUT * 2:
                timed_out.append(request_id)
        
        for request_id in timed_out:
            log.warning(f"Cleaning up stale negotiation: {request_id}")
            if request_id in self.pending_negotiations:
                del self.pending_negotiations[request_id]
            if request_id in self.response_queues:
                del self.response_queues[request_id]
