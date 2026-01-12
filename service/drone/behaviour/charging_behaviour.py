from spade.behaviour import PeriodicBehaviour

DRONE_MAX_BATTERY_PERCENT = 100.0
DRONE_CHARGING_RATE_PERCENT = 5.0

class ChargingBehaviour(PeriodicBehaviour):
    def __init__(self, period: int, *, log=None):
        super().__init__(period=period)
        self.log = log

    async def run(self):
        drone = self.agent.drone_info

        if not drone.base_location:
            return

        if drone.current_position.almost_equals(drone.base_location):
            if drone.available and drone.battery_percent < DRONE_MAX_BATTERY_PERCENT:
                drone.battery_percent += DRONE_CHARGING_RATE_PERCENT

                if drone.battery_percent > DRONE_MAX_BATTERY_PERCENT:
                    drone.battery_percent = DRONE_MAX_BATTERY_PERCENT

                self.log.info(f"Charging... {drone.battery_percent}%")