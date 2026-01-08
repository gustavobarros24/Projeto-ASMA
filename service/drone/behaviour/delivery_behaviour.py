import asyncio
from spade.behaviour import OneShotBehaviour
from common.packet import DeliveryPacket, PackageInfo, DroneStatusPacket, RefuseJobPacket
from common.package import Package
from utils.communication import new_message
from utils.logger import logging

_LOADING_TIME = 2.0

class DeliveryBehaviour(OneShotBehaviour):
    def __init__(self, packet: PackageInfo, *, log=None):
        super().__init__()
        self.package = packet.package
        self.pickup_location = packet.pickup_location
        self.company_id = packet.sender_id
        self.log = log

    async def run(self):
        drone = self.agent.drone_info

        drone.available = False

        home_pos = drone.current_position
        self.log.info(f"Delivery started: base -> pickup -> client -> base")

        dist_pickup = drone.current_position.distance_to(self.pickup_location)
        dist_delivery = self.pickup_location.distance_to(self.package.location)
        dist_return = self.package.location.distance_to(home_pos)

        empty_dist = dist_pickup + dist_return

        estimated_battery = drone.calculate_delivery_battery( empty_dist, dist_delivery, self.package.item.weight_kg )

        if drone.battery_percent < estimated_battery:
            reason = f"Low battery. (current: {drone.battery_percent:.2f}%, needs: {estimated_battery:.2f}%)"
            self.log.warning(f"Reason for rejection: {reason}")

            packet = RefuseJobPacket(self.agent.jid.node, self.package, reason)
            msg = new_message(packet, self.company_id)
            await self.send(msg)

            drone.available = True
            return

        self.log.info(f"Flying to pickup point (company)... ({dist_pickup:.2f} km)")
        await asyncio.sleep(drone.calculate_flight_duration(dist_pickup))
        drone.current_position = self.pickup_location
        consumption = drone.calculate_consumption(dist_pickup, 0.0)
        drone.battery_percent -= consumption

        self.log.info("Arrived at pickup: loading package...")
        await asyncio.sleep(_LOADING_TIME)

        self.log.info(f"Flying to client... ({dist_delivery:.2f} km)")
        await asyncio.sleep(drone.calculate_flight_duration(dist_delivery))
        drone.current_position = self.package.location
        consumption = drone.calculate_consumption(dist_delivery, self.package.item.weight_kg)
        drone.battery_percent -= consumption

        self.log.info("Delivering package...")
        delivery_packet = DeliveryPacket(self.agent.jid.node, self.package)
        msg = new_message(delivery_packet, self.package.client_id)
        await self.send(msg)

        self.log.info(f"Returning to base... ({dist_return:.2f} km)")
        await asyncio.sleep(drone.calculate_flight_duration(dist_return))
        drone.current_position = home_pos
        consumption = drone.calculate_consumption(dist_return, 0.0)
        drone.battery_percent -= consumption

        self.log.info(f"Delivery complete! (battery remaining: {drone.battery_percent:.2f}%)")
        drone.available = True

        self.log.info(f"Notifying company {self.company_id} that delivery is complete...")

        status_packet = DroneStatusPacket(self.agent.jid.node, drone)
        msg = new_message(status_packet, self.company_id)
        await self.send(msg)