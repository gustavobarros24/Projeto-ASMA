import logging

from spade.behaviour import CyclicBehaviour
from common.packet import Packet, RequestDronePacket, ResponseDronePacket
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
        else:
            log.info(f"Received unexpected packet: {type(packet)}")

    async def handle_drone_request(self, packet: RequestDronePacket):
        log = self.agent.log

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
        else:
            log.warning(f"No drone available for {packet.sender_id}.")
            cost = 0.0

        response = ResponseDronePacket(self.agent.jid.node, best_drone, cost)
        msg = new_message(response, packet.sender_id)
        await self.send(msg)
        log.info(f"Response sent to {packet.sender_id} with drone assigned: {best_drone.id if best_drone else 'None'}")