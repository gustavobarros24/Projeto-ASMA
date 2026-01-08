from spade.behaviour import PeriodicBehaviour


class ChargingBehaviour(PeriodicBehaviour):
    def __init__(self, period: int, *, log=None):
        super().__init__(period=period)
        self.log = log

    async def run(self):
        drone = self.agent.drone_info

        if drone.available and drone.battery_percent < 100:
            drone.battery_percent += 5

            if drone.battery_percent > 100:
                drone.battery_percent = 100

            self.log.info(f"Charging... {drone.battery_percent}%")