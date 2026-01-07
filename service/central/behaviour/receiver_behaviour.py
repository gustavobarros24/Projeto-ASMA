import logging

from spade.behaviour import CyclicBehaviour
from common.packet import (
    Packet, RequestDronePacket, ResponseDronePacket,
    ResponseDroneLendPacket, ReturnDronePacket, DroneReturnedPacket
)
from common.drone_info import DroneInfo
from utils.communication import new_message
from typing import Optional

_PRICE_PER_KM = 0.50
_BASE_FEE = 3.0

log = logging.getLogger( __name__ )

class ReceiverBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=1)

        if not msg:
            return

        try:
            packet = Packet.deserialize(msg.body)
        except Exception as e:
            log.warning(f"Failed to deserialize packet: {e}")
            return

        if isinstance(packet, RequestDronePacket):
            log.info(f"Received drone request from {packet.sender_id} (budget: {packet.company_budget})...")
            await self.handle_drone_request(packet)
        elif isinstance(packet, ResponseDroneLendPacket):
            log.info(f"Received drone lend response from {packet.sender_id}...")
            await self.handle_lend_response(packet)
        elif isinstance(packet, ReturnDronePacket):
            log.info(f"Received drone return from {packet.sender_id} for drone {packet.drone_id}...")
            await self.handle_drone_return(packet)
        else:
            log.info(f"Received unexpected packet: {type(packet)}")

    async def handle_drone_request(self, packet: RequestDronePacket):
        best_drone: Optional[DroneInfo] = None
        min_cost = float('inf')

        for drone in self.agent.drones:
            if not drone.available:
                continue

            if drone.capacity_kg < packet.package_weight:
                log.debug(f"Drone {drone.id} skipped: insufficient capacity ({drone.capacity_kg} < {packet.package_weight})")
                continue

            dist_to_pickup = drone.current_position.distance_to(packet.pickup_location)
            dist_delivery = packet.pickup_location.distance_to(packet.client_location)
            total_distance = dist_to_pickup + dist_delivery

            estimated_cost = _BASE_FEE + (total_distance * _PRICE_PER_KM)

            if estimated_cost > packet.company_budget:
                log.debug(f"Drone {drone.id} skipped: over budget ({estimated_cost:.2f} > {packet.company_budget})")
                continue

            if estimated_cost < min_cost:
                min_cost = estimated_cost
                best_drone = drone

        if best_drone:
            best_drone.available = False
            log.info(f"Drone {best_drone.id} assigned to {packet.sender_id}. (cost: {min_cost:.2f})")
            cost = min_cost
            
            response = ResponseDronePacket(self.agent.jid.node, best_drone, cost)
            msg = new_message(response, packet.sender_id)
            await self.send(msg)
            log.info(f"Response sent to {packet.sender_id} with drone assigned: {best_drone.id}")
        else:
            log.warning(f"No central drone available for {packet.sender_id}. Starting negotiation with companies...")
            
            # Use negotiate behaviour to find a drone from other companies
            negotiate_behaviour = self.agent.negotiate_behaviour
            if negotiate_behaviour:
                lent_drone = await negotiate_behaviour.start_negotiation(packet)
                if lent_drone:
                    log.info(f"Drone {lent_drone.id} lent to {packet.sender_id} from another company")
                    # The DroneLentPacket is already sent by negotiate_behaviour
                    return
            
            # If no drone found through negotiation, send response with no drone
            log.warning(f"No drone available for {packet.sender_id} after negotiation.")
            response = ResponseDronePacket(self.agent.jid.node, None, 0.0)
            msg = new_message(response, packet.sender_id)
            await self.send(msg)
            log.info(f"Response sent to {packet.sender_id} with no drone assigned")

    async def handle_lend_response(self, packet: ResponseDroneLendPacket):
        """Forward lend responses to the negotiate behaviour."""
        negotiate_behaviour = self.agent.negotiate_behaviour
        if negotiate_behaviour and packet.request_id in negotiate_behaviour.response_queues:
            await negotiate_behaviour.response_queues[packet.request_id].put(packet)
        else:
            log.warning(f"Received lend response for unknown request: {packet.request_id}")

    async def handle_drone_return(self, packet: ReturnDronePacket):
        """Handle drone return notification and notify the lender company."""
        log.info(f"Processing drone return: {packet.drone_id} to {packet.lender_company_id}")
        
        # Notify the lender company that their drone has been returned
        return_notification = DroneReturnedPacket(
            sender_id=self.agent.jid.node,
            drone_id=packet.drone_id
        )
        msg = new_message(return_notification, packet.lender_company_id)
        await self.send(msg)
        log.info(f"Notified {packet.lender_company_id} that drone {packet.drone_id} has been returned")