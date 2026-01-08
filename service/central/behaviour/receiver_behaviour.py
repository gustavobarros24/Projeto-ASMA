import logging
from typing import Optional

from spade.behaviour import CyclicBehaviour
from common.packet import (
    Packet, RequestDronePacket, ResponseDronePacket,
    ResponseDroneLendPacket, ReturnDronePacket, DroneReturnedPacket,
    DroneStatusPacket
)
from common.drone_info import DroneInfo
from utils.communication import new_message

_PRICE_PER_KM = 0.50
_BASE_FEE = 3.0


class ReceiverBehaviour(CyclicBehaviour):
    def __init__(self, log):
        super().__init__()
        self.log = log

    async def run(self):
        msg = await self.receive(timeout=1)

        if not msg:
            return

        try:
            packet = Packet.deserialize(msg.body)
        except Exception as e:
            self.log.warning(f"Failed to deserialize packet: {e}")
            return

        if isinstance(packet, RequestDronePacket):
            self.log.info(f"Received drone request from {packet.sender_id} (budget: {packet.company_budget})...")
            await self.handle_drone_request(packet)
        elif isinstance(packet, ResponseDroneLendPacket):
            self.log.info(f"Received drone lend response from {packet.sender_id}...")
            await self.handle_lend_response(packet)
        elif isinstance(packet, ReturnDronePacket):
            self.log.info(f"Received drone return from {packet.sender_id} for drone {packet.drone_id}...")
            await self.handle_drone_return(packet)
        elif isinstance(packet, DroneStatusPacket):
            self.handle_status_update(packet)
        else:
            self.log.info(f"Received unexpected packet: {type(packet)}")

    async def handle_drone_request(self, packet: RequestDronePacket):
        best_drone: Optional[DroneInfo] = None
        min_cost = float('inf')

        for drone in self.agent.drones:
            if not drone.available:
                continue

            if drone.battery_percent < 20:
                self.log.debug(f"Drone {drone.id} skipped: Low battery ({drone.battery_percent}%)")
                continue

            if drone.capacity_kg < packet.package_weight:
                self.log.debug(f"Drone {drone.id} skipped: insufficient capacity ({drone.capacity_kg} < {packet.package_weight})")
                continue

            dist_to_pickup = drone.current_position.distance_to(packet.pickup_location)
            dist_delivery = packet.pickup_location.distance_to(packet.client_location)
            total_distance = dist_to_pickup + dist_delivery

            estimated_cost = _BASE_FEE + (total_distance * _PRICE_PER_KM)

            if estimated_cost > packet.company_budget:
                self.log.debug(f"Drone {drone.id} skipped: over budget ({estimated_cost:.2f} > {packet.company_budget})")
                continue

            if estimated_cost < min_cost:
                min_cost = estimated_cost
                best_drone = drone

        if best_drone:
            best_drone.available = False
            self.log.info(f"Drone {best_drone.id} assigned to {packet.sender_id}. (cost: {min_cost:.2f})")
            cost = min_cost

            response = ResponseDronePacket(self.agent.jid.node, best_drone, cost)
            msg = new_message(response, packet.sender_id)
            await self.send(msg)
            self.log.info(f"Response sent to {packet.sender_id} with drone assigned: {best_drone.id}")
        else:
            self.log.warning(f"No central drone available for {packet.sender_id}. Starting negotiation with companies...")

            # Use negotiate behaviour to find a drone from other companies
            negotiate_behaviour = self.agent.negotiate_behaviour
            if negotiate_behaviour:
                lent_drone = await negotiate_behaviour.start_negotiation(packet)
                if lent_drone:
                    self.log.info(f"Drone {lent_drone.id} lent to {packet.sender_id} from another company")
                    # The DroneLentPacket is already sent by negotiate_behaviour
                    return

            # If no drone found through negotiation, send response with no drone
            self.log.warning(f"No drone available for {packet.sender_id} after negotiation.")
            response = ResponseDronePacket(self.agent.jid.node, None, 0.0)
            msg = new_message(response, packet.sender_id)
            await self.send(msg)
            self.log.info(f"Response sent to {packet.sender_id} with no drone assigned")

    async def handle_lend_response(self, packet: ResponseDroneLendPacket):
        """Forward lend responses to the negotiate behaviour."""
        negotiate_behaviour = self.agent.negotiate_behaviour
        if negotiate_behaviour and packet.request_id in negotiate_behaviour.response_queues:
            await negotiate_behaviour.response_queues[packet.request_id].put(packet)
        else:
            self.log.warning(
                f"Received lend response for unknown request or negotiation not active: {packet.request_id}")

    async def handle_drone_return(self, packet: ReturnDronePacket):
        """Handle drone return notification and notify the lender company."""
        self.log.info(f"Processing drone return: {packet.drone_id} to {packet.lender_company_id}")

        # Notify the lender company that their drone has been returned
        return_notification = DroneReturnedPacket(
            sender_id=self.agent.jid.node,
            drone_id=packet.drone_id
        )
        msg = new_message(return_notification, packet.lender_company_id)
        await self.send(msg)
        self.log.info(f"Notified {packet.lender_company_id} that drone {packet.drone_id} has been returned")

    def handle_status_update(self, packet: DroneStatusPacket):
        updated_info = packet.drone_info

        for i, drone in enumerate(self.agent.drones):
            if drone.id == updated_info.id:
                self.agent.drones[i] = updated_info
                #self.log.info(f"Updated status for {drone.id}: {updated_info.battery_percent}%")
                return