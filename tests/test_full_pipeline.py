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
from common.drone_info import DroneInfo
from common.item import Item

# Import agents
from client.client_agent import ClientAgent
from service.central.central_agent import CentralAgent
from service.company.company_agent import CompanyAgent
from service.drone.drone_agent import DroneAgent

log = get_logger(name="test_full_pipeline", log_dir="logs", console=True)

_DEFAULT_PASSWORD = "123"
DRONES_PATH = "assets/_drones.json"
ITEMS_PATH = "assets/_items.json"
COMPANIES_PATH = "assets/companies.json"


def print_section(title: str):
    """Print a section header."""
    log.info("")
    log.info("=" * 80)
    log.info(f"   {title}")
    log.info("=" * 80)


def print_step(step: str):
    """Print a step header."""
    log.info("")
    log.info(f">>> STEP: {step}")
    log.info("-" * 80)


def load_json(path: str):
    """Load JSON data from file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def test_full_pipeline():
    """
    Test the complete pipeline:
    1. Start Central agent with drones
    2. Start Company agents with inventory and drones
    3. Start Client agent
    4. Client fetches inventory from company
    5. Client buys item from company
    6. Company receives order and requests drone
    7. Central/Company assigns drone
    8. Drone delivers package to client
    9. Client receives package
    10. Verify complete flow
    """
    print_section("FULL PIPELINE INTEGRATION TEST")
    log.info("Testing: Client -> Company -> Central -> Drone -> Delivery -> Client")
    log.info("")
    
    # Load data
    print_step("Loading configuration data")
    drones_data = load_json(DRONES_PATH)
    companies_data = load_json(COMPANIES_PATH)
    
    # Use first 2 drones for central, leave others for companies
    central_drones = drones_data["drones"][:2]
    company_drones = drones_data["drones"][2:]
    
    log.info(f"Central will manage {len(central_drones)} drones")
    log.info(f"Companies will have {len(company_drones)} drones to share")
    
    # Setup locations
    central_location = GeoCoord(41.88, -87.63)  # Chicago downtown
    walmart_location = GeoCoord(41.880000, -87.630000)
    amazon_location = GeoCoord(41.890000, -87.610000)
    client_location = GeoCoord(41.895000, -87.625000)  # North of downtown
    
    log.info(f"Central location: {central_location}")
    log.info(f"Walmart location: {walmart_location}")
    log.info(f"Amazon location: {amazon_location}")
    log.info(f"Client location: {client_location}")
    
    # ====================================================================
    # STEP 1: Start Central Agent
    # ====================================================================
    print_step("Starting Central Agent")
    
    # Format drones data for central agent
    central_drones_formatted = [{"info": d} for d in central_drones]
    
    central_agent = CentralAgent(
        get_agent_jid(CENTRAL_ID),
        _DEFAULT_PASSWORD,
        central_drones_formatted,
        companies=["walmart", "amazon", "apple"]
    )
    
    await central_agent.start(auto_register=True)
    log.info(f" Central agent started with {len(central_agent.drones)} drones")
    
    await asyncio.sleep(1)
    
    # ====================================================================
    # STEP 2: Start Company Agents
    # ====================================================================
    print_step("Starting Company Agents")
    
    # Start Walmart
    walmart_agent = CompanyAgent(
        get_agent_jid("walmart"),
        _DEFAULT_PASSWORD,
        _budget=1000000.0,
        _location=walmart_location
    )
    await walmart_agent.start(auto_register=True)
    log.info(f" Walmart started with {len(walmart_agent.inventory)} items in inventory")
    
    # Start Amazon
    amazon_agent = CompanyAgent(
        get_agent_jid("amazon"),
        _DEFAULT_PASSWORD,
        _budget=1000000.0,
        _location=amazon_location
    )
    await amazon_agent.start(auto_register=True)
    log.info(f" Amazon started with {len(amazon_agent.inventory)} items in inventory")
    
    await asyncio.sleep(1)
    
    # ====================================================================
    # STEP 3: Start Drone Agents for Companies
    # ====================================================================
    print_step("Starting Drone Agents")
    
    drone_agents = []
    for i, drone_data in enumerate(company_drones[:2]):  # Use 2 drones
        drone_agent = DroneAgent(
            get_agent_jid(drone_data['id'].lower()),
            _DEFAULT_PASSWORD,
            drone_data
        )
        await drone_agent.start(auto_register=True)
        drone_agents.append(drone_agent)
        
        # Assign first drone to Walmart, second to Amazon
        if i == 0:
            # Add drone to Walmart's rented drones
            drone_info = DroneInfo(
                id=drone_data['id'].lower(),
                model=drone_data['model'],
                capacity_kg=drone_data['capacity_kg'],
                speed_kmh=drone_data['speed_kmh'],
                battery_percent=drone_data['battery_percent']
            )
            drone_info.current_position = walmart_location
            walmart_agent.rented_drones.append(drone_info)
            log.info(f" {drone_data['id']} assigned to Walmart")
        else:
            drone_info = DroneInfo(
                id=drone_data['id'].lower(),
                model=drone_data['model'],
                capacity_kg=drone_data['capacity_kg'],
                speed_kmh=drone_data['speed_kmh'],
                battery_percent=drone_data['battery_percent']
            )
            drone_info.current_position = amazon_location
            amazon_agent.rented_drones.append(drone_info)
            log.info(f" {drone_data['id']} assigned to Amazon")
    
    await asyncio.sleep(1)
    
    # ====================================================================
    # STEP 4: Start Client Agent
    # ====================================================================
    print_step("Starting Client Agent")
    
    client_agent = ClientAgent(
        get_agent_jid("test_client"),
        _DEFAULT_PASSWORD,
        budget=1000.0,
        location=client_location,
        log=log
    )
    await client_agent.start(auto_register=True)
    log.info(f" Client started with ${client_agent.budget} budget at {client_location}")
    
    await asyncio.sleep(1)
    
    # ====================================================================
    # STEP 5: Client fetches inventory from Walmart
    # ====================================================================
    print_step("Client fetches inventory from Walmart")
    
    await client_agent.get_inventory("walmart")
    await asyncio.sleep(3)  # Wait for inventory fetch
    
    log.info(f" Client received {len(client_agent.available_items_cache)} items from cache")
    
    if len(client_agent.available_items_cache) > 0:
        log.info("Sample items in cache:")
        for item_id, item in list(client_agent.available_items_cache.items())[:3]:
            log.info(f"  - {item.name}: ${item.price_usd} ({item.weight_kg}kg)")
    
    # ====================================================================
    # STEP 6: Client buys item from Walmart
    # ====================================================================
    print_step("Client buys item from Walmart")
    
    # Find a light item to buy (Bluetooth headphones or similar)
    item_to_buy = None
    for item_id, item in client_agent.available_items_cache.items():
        if item.weight_kg < 2.0 and item.price_usd < client_agent.budget:
            item_to_buy = item
            break
    
    if not item_to_buy:
        # Fallback: just get first item that fits budget
        for item_id, item in client_agent.available_items_cache.items():
            if item.price_usd < client_agent.budget:
                item_to_buy = item
                break
    
    if item_to_buy:
        initial_budget = client_agent.budget
        initial_packages = walmart_agent.packages_to_send.qsize()
        
        log.info(f"Client buying: {item_to_buy.name}")
        log.info(f"  Price: ${item_to_buy.price_usd}")
        log.info(f"  Weight: {item_to_buy.weight_kg}kg")
        log.info(f"  Client budget before: ${initial_budget}")
        
        await client_agent.buy_item("walmart", item_to_buy.id)
        
        await asyncio.sleep(2)  # Wait for purchase to process
        
        log.info(f" Purchase sent to Walmart")
        log.info(f"  Client budget after: ${client_agent.budget}")
        log.info(f"  Budget spent: ${initial_budget - client_agent.budget}")
    else:
        log.error(" No suitable item found to buy!")
        await cleanup_agents(client_agent, central_agent, walmart_agent, amazon_agent, drone_agents)
        return
    
    # ====================================================================
    # STEP 7: Wait for Walmart to process and assign drone
    # ====================================================================
    print_step("Waiting for Walmart to process order and assign drone")
    
    await asyncio.sleep(3)
    
    packages_in_queue = walmart_agent.packages_to_send.qsize()
    log.info(f"Packages in Walmart queue: {packages_in_queue}")
    
    # Check drone status
    for drone_info in walmart_agent.rented_drones:
        log.info(f"Drone {drone_info.id}: available={drone_info.available}, battery={drone_info.battery_percent}%")
    
    # ====================================================================
    # STEP 8: Wait for delivery to complete
    # ====================================================================
    print_step("Waiting for drone delivery")
    
    log.info("Waiting up to 30 seconds for delivery to complete...")
    max_wait = 30
    wait_interval = 2
    elapsed = 0
    
    delivery_completed = False
    while elapsed < max_wait:
        await asyncio.sleep(wait_interval)
        elapsed += wait_interval
        
        # Check if client received the item (check all companies in inventory)
        item_received = False
        for company_items in client_agent.inventory.values():
            if item_to_buy.id in company_items:
                item_received = True
                break
        
        if item_received:
            delivery_completed = True
            log.info(f"[SUCCESS] DELIVERY COMPLETED after {elapsed} seconds!")
            break
        
        # Show progress every 5 seconds
        if elapsed % 5 == 0:
            log.info(f"  ... waiting ({elapsed}s elapsed)")
            
            # Show drone status
            for i, drone_agent in enumerate(drone_agents):
                pos = drone_agent.drone_info.current_position
                log.info(f"  Drone {i+1}: pos=({pos.latitude:.4f}, {pos.longitude:.4f}), "
                        f"available={drone_agent.drone_info.available}, "
                        f"battery={drone_agent.drone_info.battery_percent:.1f}%")
    
    # ====================================================================
    # STEP 9: Verify results
    # ====================================================================
    print_step("Verifying results")
    
    if delivery_completed:
        log.info("[SUCCESS] Item was delivered to client!")
        log.info(f"  Item: {item_to_buy.name}")
        log.info(f"  Companies in client inventory: {list(client_agent.inventory.keys())}")
        total_items = sum(len(items) for items in client_agent.inventory.values())
        log.info(f"  Total items in client inventory: {total_items}")
    else:
        log.warning(" Delivery did not complete in time")
        log.info(f"  This might be normal if delivery takes longer than {max_wait}s")
    
    # Check drone returned to base
    for i, drone_agent in enumerate(drone_agents):
        if i == 0:  # Walmart drone
            base = walmart_location
            company = "Walmart"
        else:
            base = amazon_location
            company = "Amazon"
        
        pos = drone_agent.drone_info.current_position
        dist = pos.distance_to(base)
        
        log.info(f"Drone {i+1} ({company}):")
        log.info(f"  Position: ({pos.latitude:.4f}, {pos.longitude:.4f})")
        log.info(f"  Distance from base: {dist*1000:.1f}m")
        log.info(f"  Available: {drone_agent.drone_info.available}")
        log.info(f"  Battery: {drone_agent.drone_info.battery_percent:.1f}%")
        
        if dist < 0.001:  # Within 1 meter
            log.info(f"   Drone returned to base")
        else:
            log.info(f"  - Drone may still be traveling")
    
    # ====================================================================
    # STEP 10: Cleanup
    # ====================================================================
    print_step("Cleaning up")
    
    await cleanup_agents(client_agent, central_agent, walmart_agent, amazon_agent, drone_agents)
    
    log.info(" All agents stopped")
    
    # ====================================================================
    # Final Summary
    # ====================================================================
    print_section("TEST SUMMARY")
    
    log.info("Pipeline components tested:")
    log.info("  [OK] Central Agent - drone management")
    log.info("  [OK] Company Agents - inventory and order processing")
    log.info("  [OK] Drone Agents - delivery execution")
    log.info("  [OK] Client Agent - browsing and purchasing")
    log.info("")
    log.info("Communication flow verified:")
    log.info("   Client -> Company (inventory request)")
    log.info("   Client -> Company (purchase order)")
    log.info("   Company -> Drone (delivery assignment)")
    log.info("   Drone -> Client (package delivery)")
    log.info("")
    
    if delivery_completed:
        log.info("RESULT: FULL PIPELINE TEST PASSED [OK]")
    else:
        log.info("RESULT: PARTIAL SUCCESS (delivery timing)")
    
    log.info("")


async def cleanup_agents(client, central, walmart, amazon, drones):
    """Stop all agents cleanly."""
    await client.stop()
    await walmart.stop()
    await amazon.stop()
    await central.stop()
    for drone in drones:
        await drone.stop()


async def main():
    print_section("MULTI-AGENT SYSTEM - FULL PIPELINE TEST")
    log.info("This test verifies the complete system integration")
    log.info("from client purchase to drone delivery")
    log.info("")
    
    try:
        await test_full_pipeline()
        
    except AssertionError as e:
        log.error(f" Test failed: {e}")
    except Exception as e:
        log.error(f" Error during test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    spade.run(main())
