import asyncio
import spade
from service.central.central_agent import CentralAgent
from service.company.company_agent import CompanyAgent
from service.company.web_ui import CompanyWebUI
from service.drone.drone_agent import DroneAgent
from client.client_agent import ClientAgent
from client.web_ui import ClientWebUI
from common.geo_coord import GeoCoord
from config.config import *
from utils.logger import get_logger
from utils.utils import generate_id, DRONES_PATH, ITEMS_PATH
import json
from aiohttp import web
from service.central import web_server

"""
===============================================================================
    Run All Agents Together (Client + Service)
    This ensures all agents share the same XMPP server
===============================================================================
"""

_DEFAULT_PASSWORD = "123"
_WEB_PORT_START = 5001  # First client will use 5001, second 5002, etc.
_COMPANY_WEB_PORT_START = 6001  # First company will use 6001, second 6002, etc.

log = get_logger(name="run_all", log_dir="logs", console=True)

def _load_companies():
    with open(COMPANIES_PATH) as f:
        data = json.load(f)
    return [
        {
            "jid": get_agent_jid(c["id"]),
            "password": _DEFAULT_PASSWORD,
            "annual_revenue_usd": c["annual_revenue_usd"],
            "location": GeoCoord(c["location"]["lat"], c["location"]["lon"])
        }
        for c in data["companies"]
    ]

def _load_drones():
    with open(DRONES_PATH) as f:
        data = json.load(f)
    return [
        {
            "jid": get_agent_jid(d["id"]),
            "password": _DEFAULT_PASSWORD,
            "info": d
        }
        for d in data["drones"]
    ]

def _load_clients():
    with open(CLIENTS_PATH) as f:
        data = json.load(f)
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "jid": get_agent_jid(c["id"]),
            "password": _DEFAULT_PASSWORD,
            "location": GeoCoord(c["location"]["lat"], c["location"]["lon"]),
            "budget": c["budget"]
        }
        for c in data["clients"]
    ]

async def main():
    log.info("Starting all agents in single process...")
    
    # Load configurations
    companies = _load_companies()
    log.info(f"Loaded {len(companies)} companies")
    
    drones = _load_drones()
    log.info(f"Loaded {len(drones)} drones")
    
    clients = _load_clients()
    log.info(f"Loaded {len(clients)} clients")
    
    company_ids = [c["jid"].split("@")[0] for c in companies]
    
    # Start Central Agent
    log.info("Starting Central Agent...")
    central_agent = CentralAgent(get_agent_jid(CENTRAL_ID), _DEFAULT_PASSWORD, drones, company_ids)
    await central_agent.start(auto_register=True)
    
    # Start Companies
    log.info("Starting Companies...")
    company_agents = []
    company_web_uis = []
    for i, company in enumerate(companies):
        web_port = _COMPANY_WEB_PORT_START + i
        
        agent = CompanyAgent(
            company["jid"],
            company["password"],
            company["annual_revenue_usd"],
            company["location"],
        )
        company_agents.append(agent)
        await agent.start(auto_register=True)
        
        # Start Web UI for this company
        company_web_ui = CompanyWebUI(agent, port=web_port)
        await company_web_ui.start()
        company_web_uis.append(company_web_ui)
    
    # Start Drones
    log.info("Starting Drones...")
    drone_agents = []
    for drone in drones:
        agent = DroneAgent(drone["jid"], drone["password"], drone["info"])
        drone_agents.append(agent)
        await agent.start(auto_register=True)
    
    # Wait for all agents to connect
    await asyncio.sleep(2)
    
    # Start Clients from JSON
    log.info(f"Starting {len(clients)} Client Agent(s)...")
    client_agents = []
    web_uis = []
    
    for i, client in enumerate(clients):
        web_port = _WEB_PORT_START + i
        
        log.info(f"Starting Client {i+1}/{len(clients)}: {client['name']} on port {web_port}...")
        client_log = get_logger(name=f"client.{client['id']}", log_dir="logs", console=False)
        
        client_agent = ClientAgent(
            client["jid"],
            client["password"],
            client["budget"],
            client["location"],
            log=client_log
        )
        await client_agent.start(auto_register=True)
        client_agents.append(client_agent)
        
        # Start Web UI for this client
        web_ui = ClientWebUI(client_agent, port=web_port)
        await web_ui.start()
        web_uis.append(web_ui)
    
    # Start Central Dashboard
    log.info("Starting Central Dashboard on port 5000...")
    dashboard_app = web_server.create_app()
    dashboard_runner = web.AppRunner(dashboard_app)
    await dashboard_runner.setup()
    dashboard_site = web.TCPSite(dashboard_runner, '127.0.0.1', 5000)
    await dashboard_site.start()
    
    print(f"\n{'='*60}")
    print(f" Sistema iniciado!")
    print(f"{'='*60}")
    print(f" Dashboard Central: http://127.0.0.1:5000")
    print(f" Interfaces das Empresas:")
    for i, company in enumerate(companies):
        port = _COMPANY_WEB_PORT_START + i
        company_id = company['jid'].split('@')[0]
        print(f"   - {company_id}: http://localhost:{port}")
    print(f" Interfaces dos Clientes:")
    for i, client in enumerate(clients):
        port = _WEB_PORT_START + i
        print(f"   - {client['name']} ({client['id']}): http://localhost:{port}")
    print(f"{'='*60}\n")
    print("Todos os agentes estão a correr. Pressione Ctrl+C para parar.")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down all agents...")
    finally:
        await dashboard_runner.cleanup()
        for client_agent in client_agents:
            await client_agent.stop()
        for web_ui in web_uis:
            await web_ui.stop()
        for company_web_ui in company_web_uis:
            await company_web_ui.stop()
        for agent in company_agents:
            await agent.stop()
        for agent in drone_agents:
            await agent.stop()
        await central_agent.stop()

if __name__ == "__main__":
    spade.run(main())
