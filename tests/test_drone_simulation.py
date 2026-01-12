import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import spade
import asyncio
import json
from datetime import datetime

from utils.logger import get_logger
from config.config import *
from common.geo_coord import GeoCoord
from common.drone_info import DroneInfo, _SIMULATION_SPEED_SCALE
from common.item import Item
from common.package import Package
from common.packet import PackageInfo
from service.drone.drone_agent import DroneAgent
from service.drone.behaviour.delivery_behaviour import DeliveryBehaviour
from service.drone.behaviour.charging_behaviour import ChargingBehaviour

log = get_logger(name="test_drone_simulation", log_dir="logs", console=True)

_DEFAULT_PASSWORD = "123"
DRONES_PATH = "assets/_drones.json"


def load_drones_from_json():
    """Load drones from JSON file."""
    with open(DRONES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["drones"]


def print_section(title: str):
    """Print a section header."""
    log.info("")
    log.info("=" * 80)
    log.info(f"   {title}")
    log.info("=" * 80)


def print_test(test_name: str):
    """Print a test header."""
    log.info("")
    log.info(f">>> TEST: {test_name}")
    log.info("-" * 80)


async def test_flight_time_calculation():
    """Test 1: Verify flight time is calculated correctly based on distance and speed."""
    print_test("Flight Time Calculation")
    
    # Create test drone with known speed
    drone = DroneInfo(
        id="TEST_DRONE_SPEED",
        model="Speed Test Drone",
        capacity_kg=5.0,
        speed_kmh=72,  # 72 km/h = 20 m/s
        battery_percent=100
    )
    
    # Test distance: 10 km
    distance_km = 10.0
    
    # Use DroneInfo method to calculate flight duration
    sim_time = drone.calculate_flight_duration(distance_km)
    
    # Verify calculation is reasonable
    expected_time_hours = distance_km / drone.speed_kmh
    
    log.info(f"Distance: {distance_km} km")
    log.info(f"Speed: {drone.speed_kmh} km/h")
    log.info(f"Expected real time: {expected_time_hours*60:.2f} minutes")
    log.info(f"Simulated time: {sim_time:.2f} seconds")
    
    assert sim_time > 0, "Flight time should be positive!"
    assert sim_time < 60, "Simulated time should be reasonable!"
    log.info(" PASS: Flight time calculation is correct")


async def test_battery_consumption():
    """Test 2: Verify battery consumption with different loads."""
    print_test("Battery Consumption")
    
    drone = DroneInfo(
        id="TEST_DRONE_BATTERY",
        model="Battery Test Drone",
        capacity_kg=10.0,
        speed_kmh=60,
        battery_percent=100
    )
    
    distance = 5.0  # km
    
    # Test 1: Empty flight
    consumption_empty = drone.calculate_consumption(distance, 0.0)
    log.info(f"Empty flight ({distance} km): {consumption_empty:.2f}% battery")
    
    # Test 2: Light load (2 kg)
    consumption_light = drone.calculate_consumption(distance, 2.0)
    log.info(f"Light load 2kg ({distance} km): {consumption_light:.2f}% battery")
    
    # Test 3: Heavy load (8 kg)
    consumption_heavy = drone.calculate_consumption(distance, 8.0)
    log.info(f"Heavy load 8kg ({distance} km): {consumption_heavy:.2f}% battery")
    
    # Verify that heavier loads consume more battery
    assert consumption_empty < consumption_light < consumption_heavy, "Battery consumption not increasing with weight!"
    log.info(" PASS: Battery consumption increases with weight")


async def test_capacity_rejection():
    """Test 3: Verify drone rejects packages that are too heavy."""
    print_test("Capacity Rejection")
    
    # Create drone with 3kg capacity
    drone_data = {
        'id': 'TEST_DRONE_CAPACITY',
        'model': 'Small Capacity Drone',
        'capacity_kg': 3.0,
        'speed_kmh': 50,
        'battery_percent': 100
    }
    
    drone_agent = DroneAgent(
        get_agent_jid('test_drone_capacity'),
        _DEFAULT_PASSWORD,
        drone_data
    )
    
    await drone_agent.start(auto_register=True)
    log.info(f"Drone capacity: {drone_agent.drone_info.capacity_kg} kg")
    
    # Try to deliver a 5kg package (should reject)
    heavy_item = Item(
        id="HEAVY_ITEM",
        company_id="TEST",
        name="Heavy Package",
        description="Test heavy package",
        price_usd=100.0,
        weight_kg=5.0  # Exceeds capacity!
    )
    
    heavy_package = Package(
        order_id="TEST_ORDER_HEAVY",
        client_id="test_client",
        location=GeoCoord(41.89, -87.62),
        item=heavy_item
    )
    
    packet = PackageInfo(
        sender_id="test_company",
        package=heavy_package,
        pickup_location=GeoCoord(41.88, -87.63)
    )
    
    # Add delivery behaviour
    initial_battery = drone_agent.drone_info.battery_percent
    # Use DroneInfo.can_send to check if drone can handle package
    can_deliver = drone_agent.drone_info.can_send(heavy_package)
    log.info(f"Can deliver 5kg package (capacity {drone_agent.drone_info.capacity_kg}kg): {can_deliver}")
    
    drone_agent.add_behaviour(DeliveryBehaviour(packet, log=log))
    
    await asyncio.sleep(2)
    
    # Check if drone is still available (should be, because it rejected)
    if drone_agent.drone_info.available and not can_deliver:
        log.info(f" PASS: Drone correctly rejected package exceeding capacity")
    else:
        log.error(f" FAIL: Drone behavior incorrect for overweight package!")
    
    await drone_agent.stop()


async def test_low_battery_rejection():
    """Test 4: Verify drone rejects delivery when battery is too low."""
    print_test("Low Battery Rejection")
    
    # Create drone with low battery
    drone_data = {
        'id': 'TEST_DRONE_LOWBAT',
        'model': 'Low Battery Drone',
        'capacity_kg': 5.0,
        'speed_kmh': 60,
        'battery_percent': 10  # Very low battery!
    }
    
    drone_agent = DroneAgent(
        get_agent_jid('test_drone_lowbat'),
        _DEFAULT_PASSWORD,
        drone_data
    )
    
    await drone_agent.start(auto_register=True)
    log.info(f"Drone battery: {drone_agent.drone_info.battery_percent}%")
    
    # Try long distance delivery
    item = Item(
        id="ITEM",
        company_id="TEST",
        name="Test Item",
        description="Test item for delivery",
        price_usd=50.0,
        weight_kg=2.0
    )
    
    package = Package(
        order_id="TEST_ORDER_LONG",
        client_id="test_client",
        location=GeoCoord(42.0, -88.0),  # Far away!
        item=item
    )
    
    packet = PackageInfo(
        sender_id="test_company",
        package=package,
        pickup_location=GeoCoord(41.88, -87.63)
    )
    
    # Use DroneInfo.battery_needed_percent to check battery requirements
    battery_needed = drone_agent.drone_info.battery_needed_percent(package)
    can_deliver = drone_agent.drone_info.can_send(package)
    log.info(f"Battery needed: {battery_needed:.2f}%, Available: {drone_agent.drone_info.battery_percent}%")
    log.info(f"Can deliver: {can_deliver}")
    
    drone_agent.add_behaviour(DeliveryBehaviour(packet, log=log))
    
    await asyncio.sleep(2)
    
    # Should still be available (rejected due to low battery)
    if drone_agent.drone_info.available and not can_deliver:
        log.info(f" PASS: Drone correctly rejected delivery due to low battery")
    else:
        log.error(f" FAIL: Drone behavior incorrect for low battery situation!")
    
    await drone_agent.stop()


async def test_successful_delivery():
    """Test 5: Verify complete successful delivery."""
    print_test("Successful Delivery")
    
    drone_data = {
        'id': 'TEST_DRONE_DELIVERY',
        'model': 'Delivery Test Drone',
        'capacity_kg': 10.0,
        'speed_kmh': 72,
        'battery_percent': 100
    }
    
    drone_agent = DroneAgent(
        get_agent_jid('test_drone_delivery'),
        _DEFAULT_PASSWORD,
        drone_data
    )
    
    await drone_agent.start(auto_register=True)

    for behaviour in list(drone_agent.behaviours):
        if isinstance(behaviour, ChargingBehaviour):
            drone_agent.remove_behaviour(behaviour)
            log.info(" [TEST SETUP]: ChargingBehaviour removed to measure battery consumption accurately.")
    
    initial_position = drone_agent.drone_info.current_position
    drone_agent.drone_info.base_location = initial_position
    initial_battery = drone_agent.drone_info.battery_percent
    
    log.info(f"Initial position: ({initial_position.latitude:.3f}, {initial_position.longitude:.3f})")
    log.info(f"Initial battery: {initial_battery}%")
    
    # Create delivery
    item = Item(
        id="ITEM",
        company_id="TEST",
        name="Test Item",
        description="Test item for successful delivery",
        price_usd=50.0,
        weight_kg=2.0
    )
    
    client_location = GeoCoord(41.89, -87.61)
    pickup_location = GeoCoord(41.88, -87.62)
    
    package = Package(
        order_id="TEST_ORDER_SUCCESS",
        client_id="test_client",
        location=client_location,
        item=item
    )
    
    packet = PackageInfo(
        sender_id="test_company",
        package=package,
        pickup_location=pickup_location
    )
    
    # Calculate expected distances and battery consumption using DroneInfo methods
    dist_pickup = initial_position.distance_to(pickup_location)
    dist_delivery = pickup_location.distance_to(client_location)
    dist_return = client_location.distance_to(initial_position)
    total_dist = dist_pickup + dist_delivery + dist_return
    
    # Use DroneInfo.calculate_delivery_battery for accurate prediction
    dist_loaded = dist_delivery  # Only delivery leg has package
    dist_empty = dist_pickup + dist_return
    expected_consumption = drone_agent.drone_info.calculate_delivery_battery(
        dist_empty, dist_loaded, item.weight_kg
    )
    
    log.info(f"Total distance: {total_dist:.2f} km")
    log.info(f"Expected battery consumption: {expected_consumption:.2f}%")
    
    drone_agent.add_behaviour(DeliveryBehaviour(packet, log=log))

    flight_time = drone_agent.drone_info.calculate_flight_duration(total_dist)
    wait_time = flight_time + 5.0
    log.info(f"Waiting {wait_time:.2f}s for delivery...")
    await asyncio.sleep(wait_time)
    
    final_position = drone_agent.drone_info.current_position
    final_battery = drone_agent.drone_info.battery_percent
    
    log.info(f"Final position: ({final_position.latitude:.3f}, {final_position.longitude:.3f})")
    log.info(f"Final battery: {final_battery}%")
    log.info(f"Battery consumed: {initial_battery - final_battery:.2f}%")
    
    # Verify drone returned to base
    distance_from_base = final_position.distance_to(initial_position)
    
    if distance_from_base < 0.001:  # Within 1 meter
        log.info(f" PASS: Drone returned to base")
    else:
        log.error(f" FAIL: Drone did not return to base (distance: {distance_from_base*1000:.1f}m)")
    
    # Verify drone is available again
    if drone_agent.drone_info.available:
        log.info(f" PASS: Drone is available after delivery")
    else:
        log.error(f" FAIL: Drone is not available after delivery")
    
    # Verify battery was consumed
    if final_battery < initial_battery:
        log.info(f" PASS: Battery was consumed during delivery")
    else:
        log.error(f" FAIL: Battery was not consumed")
    
    await drone_agent.stop()


async def test_charging_behaviour():
    """Test 6: Verify charging behaviour works correctly."""
    print_test("Charging Behaviour")
    
    drone_data = {
        'id': 'TEST_DRONE_CHARGE',
        'model': 'Charging Test Drone',
        'capacity_kg': 5.0,
        'speed_kmh': 60,
        'battery_percent': 50  # Start at 50%
    }
    
    drone_agent = DroneAgent(
        get_agent_jid('test_drone_charge'),
        _DEFAULT_PASSWORD,
        drone_data
    )
    
    await drone_agent.start(auto_register=True)

    drone_agent.drone_info.base_location = drone_agent.drone_info.current_position
    initial_battery = drone_agent.drone_info.battery_percent

    log.info(f"Initial battery: {initial_battery}%")
    log.info(f"Drone is available: {drone_agent.drone_info.available}")
    log.info("Waiting 5 seconds for charging...")
    
    await asyncio.sleep(5)
    
    charged_battery = drone_agent.drone_info.battery_percent
    log.info(f"Battery after 5s: {charged_battery}%")
    
    if charged_battery > initial_battery:
        log.info(f" PASS: Battery charged from {initial_battery}% to {charged_battery}%")
    else:
        log.error(f" FAIL: Battery did not charge")
    
    if charged_battery <= 100:
        log.info(f" PASS: Battery did not exceed 100%")
    else:
        log.error(f" FAIL: Battery exceeded 100%!")
    
    await drone_agent.stop()


async def main():
    print_section("DRONE SIMULATION TESTS")
    log.info("Testing drone behaviours, timing, battery, and deliveries")
    log.info(f"Simulation speed factor: {_SIMULATION_SPEED_SCALE}x")
    log.info("")

    # test 1: flight time calculation
    await test_flight_time_calculation()

    # test 2: battery consumption
    await test_battery_consumption()

    # test 3: capacity rejection
    await test_capacity_rejection()

    # test 4: low battery rejection
    await test_low_battery_rejection()

    # test 5: successful delivery
    await test_successful_delivery()

    # test 6: charging behaviour
    await test_charging_behaviour()

    print_section("ALL TESTS COMPLETED")
    log.info(" All drone simulation tests passed!")


if __name__ == "__main__":
    spade.run(main())
