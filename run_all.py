import asyncio
import spade
from service.central.central_agent import CentralAgent
from service.company.company_agent import CompanyAgent
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
_CLIENT_NAME = "client" + generate_id()[:4]
_BUDGET = 5000.00
_CLIENT_LOCATION = GeoCoord.random_geocoord()
_WEB_PORT = 5001

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

async def main():
    log.info("Starting all agents in single process...")
    
    # Load configurations
    companies = _load_companies()
    log.info(f"Loaded {len(companies)} companies")
    
    drones = _load_drones()
    log.info(f"Loaded {len(drones)} drones")
    
    company_ids = [c["jid"].split("@")[0] for c in companies]
    
    # Start Central Agent
    log.info("Starting Central Agent...")
    central_agent = CentralAgent(get_agent_jid(CENTRAL_ID), _DEFAULT_PASSWORD, drones, company_ids)
    await central_agent.start(auto_register=True)
    
    # Start Companies
    log.info("Starting Companies...")
    company_agents = []
    for company in companies:
        agent = CompanyAgent(
            company["jid"],
            company["password"],
            company["annual_revenue_usd"],
            company["location"],
        )
        company_agents.append(agent)
        await agent.start(auto_register=True)
    
    # Start Drones
    log.info("Starting Drones...")
    drone_agents = []
    for drone in drones:
        agent = DroneAgent(drone["jid"], drone["password"], drone["info"])
        drone_agents.append(agent)
        await agent.start(auto_register=True)
    
    # Wait for all agents to connect
    await asyncio.sleep(2)
    
    # Start Client
    log.info(f"Starting Client Agent: {_CLIENT_NAME}...")
    client_log = get_logger(name=f"client.{_CLIENT_NAME}", log_dir="logs", console=False)
    client_agent = ClientAgent(
        get_agent_jid(_CLIENT_NAME),
        _DEFAULT_PASSWORD,
        _BUDGET,
        _CLIENT_LOCATION,
        log=client_log
    )
    await client_agent.start(auto_register=True)
    
    # Start Web UI
    log.info(f"Starting Web UI on port {_WEB_PORT}...")
    web_ui = ClientWebUI(client_agent, port=_WEB_PORT)
    await web_ui.start()
    
    # Start Central Dashboard
    log.info("Starting Central Dashboard on port 5000...")
    dashboard_app = web_server.create_app()
    dashboard_runner = web.AppRunner(dashboard_app)
    await dashboard_runner.setup()
    dashboard_site = web.TCPSite(dashboard_runner, '127.0.0.1', 5000)
    await dashboard_site.start()
    
    print(f"\n{'='*60}")
    print(f" Sistema iniciado com sucesso!")
    print(f"{'='*60}")
    print(f" Dashboard Central: http://127.0.0.1:5000")
    print(f" Interface Cliente: http://localhost:{_WEB_PORT}")
    print(f" Cliente ID: {_CLIENT_NAME}")
    print(f" Orçamento: ${_BUDGET:.2f}")
    print(f" Localização: {_CLIENT_LOCATION}")
    print(f"{'='*60}\n")
    print("Todos os agentes estão a correr. Pressione Ctrl+C para parar.")
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down all agents...")
    finally:
        await dashboard_runner.cleanup()
        await client_agent.stop()
        for agent in company_agents:
            await agent.stop()
        for agent in drone_agents:
            await agent.stop()
        await central_agent.stop()
        if web_ui:
            await web_ui.stop()

if __name__ == "__main__":
    spade.run(main())
