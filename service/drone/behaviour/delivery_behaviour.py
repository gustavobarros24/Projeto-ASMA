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

        if drone.owner_id is None:
            drone.owner_id = self.company_id
            self.log.info(f"Registered owner company: {drone.owner_id}")

        if drone.base_location is None:
            drone.base_location = self.pickup_location
            self.log.info(f"Registered base location: {drone.base_location}")

        drone.available = False

        if self.package.item.weight_kg > drone.capacity_kg:
            reason = f"overweight package. ({self.package.item.weight_kg}kg > capacity {drone.capacity_kg}kg)"
            self.log.warning(f"Reason for rejection: {reason}")

            packet = RefuseJobPacket(self.agent.jid.node, self.package, reason)
            msg = new_message(packet, self.company_id)
            await self.send(msg)

            drone.available = True
            return

        self.log.info(f"Delivery started: base -> pickup -> client -> base")

        dist_pickup = drone.current_position.distance_to(self.pickup_location)
        dist_delivery = self.pickup_location.distance_to(self.package.location)
        dist_return = self.package.location.distance_to(drone.base_location)

        empty_dist = dist_pickup + dist_return

        estimated_battery = drone.calculate_delivery_battery( empty_dist, dist_delivery, self.package.item.weight_kg )

        if drone.battery_percent < estimated_battery:
            reason = f"low battery. (current: {drone.battery_percent:.2f}%, needs: {estimated_battery:.2f}%)"
            self.log.warning(f"Reason for rejection: {reason}")

            packet = RefuseJobPacket(self.agent.jid.node, self.package, reason)
            msg = new_message(packet, self.company_id)
            await self.send(msg)

            drone.available = True
            return

        self.log.info(f"Flying to pickup point (company)... ({dist_pickup:.2f} km)")
        await asyncio.sleep(drone.calculate_flight_duration(dist_pickup))

        consumption = drone.calculate_consumption(dist_pickup, 0.0)
        drone.battery_percent -= consumption

        if drone.battery_percent <= 0:
            await self.handle_crash("Crash on way to pickup!")
            return

        drone.current_position = self.pickup_location

        self.log.info("Arrived at pickup: loading package...")
        await asyncio.sleep(_LOADING_TIME)

        self.log.info(f"Flying to client... ({dist_delivery:.2f} km)")
        await asyncio.sleep(drone.calculate_flight_duration(dist_delivery))

        consumption = drone.calculate_consumption(dist_delivery, self.package.item.weight_kg)
        drone.battery_percent -= consumption

        if drone.battery_percent <= 0:
            await self.handle_crash("Crash on way to client!")
            return

        drone.current_position = self.package.location

        self.log.info("Delivering package...")
        delivery_packet = DeliveryPacket(self.agent.jid.node, self.package)
        msg = new_message(delivery_packet, self.package.client_id)
        await self.send(msg)

        self.log.info(f"Returning to base (company)... ({dist_return:.2f} km)")
        await asyncio.sleep(drone.calculate_flight_duration(dist_return))

        consumption = drone.calculate_consumption(dist_return, 0.0)
        drone.battery_percent -= consumption

        if drone.battery_percent <= 0:
            await self.handle_crash("Crash on return to base!")
            return

        drone.current_position = drone.base_location

        self.log.info(f"Delivery complete! (battery remaining: {drone.battery_percent:.2f}%)")
        drone.available = True

        self.log.info(f"Notifying company {self.company_id} that delivery is complete...")

        status_packet = DroneStatusPacket(self.agent.jid.node, drone)
        msg = new_message(status_packet, self.company_id)
        await self.send(msg)

    async def handle_crash(self, reason: str):
        drone = self.agent.drone_info
        drone.battery_percent = 0
        drone.available = False

        self.log.error(f"{reason}: drone is lost.")

        packet = DroneStatusPacket(self.agent.jid.node, drone)

        if drone.owner_id:
            self.log.info(f"Notifying owner {drone.owner_id} about the crash...")
            await self.send(new_message(packet, drone.owner_id))
        await self.send(new_message(packet, "central"))