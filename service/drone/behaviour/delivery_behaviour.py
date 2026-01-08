import asyncio
from spade.behaviour import OneShotBehaviour
from common.packet import DeliveryPacket, PackageInfo, DroneStatusPacket, RefuseJobPacket
from common.package import Package
from utils.communication import new_message
from common.drone_info import _BASE_CONSUMPTION_PER_KM, _WEIGHT_FACTOR_PER_KG, _SPEED_FACTOR_PER_KMH
from utils.logger import logging

_SIMULATION_DELAY_SECONDS = 5  # simulation factor: higher values mean faster "flight", use 1.0 for real-time.


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

        # parte do voo sem carga (base -> pickup) e (cliente -> base).
        empty_dist = dist_pickup + dist_return
        cost_empty = empty_dist * (_BASE_CONSUMPTION_PER_KM + (drone.speed_kmh * _SPEED_FACTOR_PER_KMH))

        # parte do voo com a carga.
        loaded_dist = dist_delivery
        cost_loaded = loaded_dist * (
                _BASE_CONSUMPTION_PER_KM +
                (drone.speed_kmh * _SPEED_FACTOR_PER_KMH) +
                (self.package.item.weight_kg * _WEIGHT_FACTOR_PER_KG)
        )

        estimated_battery = cost_empty + cost_loaded + 5.0  # +5% de margem de segurança

        if drone.battery_percent < estimated_battery:
            reason = f"Low battery. (current: {drone.battery_percent:.2f}%, needs: {estimated_battery:.2f}%)"
            self.log.warning(f"REJECT: {reason}")

            packet = RefuseJobPacket(self.agent.jid.node, self.package, reason)
            msg = new_message(packet, self.company_id)
            await self.send(msg)

            drone.available = True
            return

        self.log.info(f"Flying to pickup point (company)... ({dist_pickup:.2f} km)")
        await asyncio.sleep(2)
        drone.current_position = self.pickup_location
        drone.battery_percent -= (dist_pickup * 1.0)

        self.log.info("Arrived at pickup: loading package...")
        await asyncio.sleep(1)

        self.log.info(f"Flying to client... ({dist_delivery:.2f} km)")
        await asyncio.sleep(2)
        drone.current_position = self.package.location
        drone.battery_percent -= (dist_delivery * 1.3)

        self.log.info("Delivering package...")
        delivery_packet = DeliveryPacket(self.agent.jid.node, self.package)
        msg = new_message(delivery_packet, self.package.client_id)
        await self.send(msg)

        self.log.info(f"Returning to base... ({dist_return:.2f} km)")
        await asyncio.sleep(2)
        drone.current_position = home_pos
        drone.battery_percent -= (dist_return * 1.0)

        self.log.info(f"Delivery complete! (battery remaining: {drone.battery_percent:.2f}%)")
        drone.available = True

        self.log.info(f"Notifying company {self.company_id} that delivery is complete...")

        status_packet = DroneStatusPacket(self.agent.jid.node, drone)
        msg = new_message(status_packet, self.company_id)
        await self.send(msg)