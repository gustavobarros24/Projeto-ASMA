"""
Web API module for Central Agent
Handles all HTTP endpoints and responses
"""
from aiohttp import web
from config.config import CENTRAL_ID

class CentralWebAPI:
    """Web API handler for Central Agent"""
    
    def __init__(self, central_agent):
        self.agent = central_agent
    
    def setup_routes(self):
        """Configure all API routes"""
        self.agent.web.add_get("/api/drones", self.get_drones_handler, None)
        self.agent.web.add_get("/api/companies", self.get_companies_handler, None)
        self.agent.web.add_get("/api/negotiations", self.get_negotiations_handler, None)
        self.agent.web.add_get("/api/stats", self.get_stats_handler, None)
        self.agent.web.add_post("/api/toggle-drone", self.toggle_drone_handler, None)
        self.agent.web.add_post("/api/test-mode", self.test_mode_handler, None)
    
    def start(self, hostname="127.0.0.1", port=10000):
        """Start the web server"""
        self.agent.web.start(hostname=hostname, port=port)
    
    # API Handlers
    async def get_drones_handler(self, request):
        """Get all drones with their status"""
        drones_data = []
        for drone in self.agent.drones:
            drones_data.append({
                "id": drone.id,
                "model": drone.model,
                "capacity_kg": drone.capacity_kg,
                "speed_kmh": drone.speed_kmh,
                "battery_percent": drone.battery_percent,
                "available": drone.available
            })
        return {"drones": drones_data}
    
    async def get_companies_handler(self, request):
        """Get all registered companies"""
        return {"companies": self.agent.companies}
    
    async def get_negotiations_handler(self, request):
        """Get active negotiations"""
        if not self.agent.negotiate_behaviour:
            return {"negotiations": [], "enabled": False}
        
        negotiations_data = []
        for request_id, negotiation in self.agent.negotiate_behaviour.pending_negotiations.items():
            negotiations_data.append({
                "request_id": request_id,
                "companies_asked": negotiation.companies_asked,
                "responses_count": len(negotiation.responses),
                "responses": {
                    company: {"has_drone": bool(response.drone)}
                    for company, response in negotiation.responses.items()
                }
            })
        
        return {
            "negotiations": negotiations_data,
            "enabled": True
        }
    
    async def get_stats_handler(self, request):
        """Get central agent statistics"""
        total_drones = len(self.agent.drones)
        available_drones = sum(1 for d in self.agent.drones if d.available)
        total_capacity = sum(d.capacity_kg for d in self.agent.drones)
        available_capacity = sum(d.capacity_kg for d in self.agent.drones if d.available)
        avg_battery = sum(d.battery_percent for d in self.agent.drones) / total_drones if total_drones > 0 else 0
        
        # Import here to avoid circular import
        from service.central.central_agent import FORCE_NEGOTIATION_TEST
        
        return {
            "agent_jid": str(self.agent.jid),
            "companies": len(self.agent.companies),
            "drones": {
                "total": total_drones,
                "available": available_drones,
                "busy": total_drones - available_drones,
                "total_capacity": total_capacity,
                "available_capacity": available_capacity,
                "avg_battery": round(avg_battery, 1)
            },
            "negotiations": {
                "active": len(self.agent.negotiate_behaviour.pending_negotiations) if self.agent.negotiate_behaviour else 0,
                "enabled": bool(self.agent.companies)
            },
            "test_mode": FORCE_NEGOTIATION_TEST
        }
    
    async def toggle_drone_handler(self, request):
        """Toggle drone availability"""
        try:
            data = await request.json()
            drone_id = data.get("drone_id")
            
            drone = next((d for d in self.agent.drones if d.id == drone_id), None)
            if not drone:
                return {"error": f"Drone {drone_id} not found", "success": False}
            
            drone.available = not drone.available
            return {
                "success": True,
                "drone_id": drone_id,
                "available": drone.available
            }
        except Exception as e:
            return {"error": str(e), "success": False}
    
    async def test_mode_handler(self, request):
        """Toggle test mode"""
        try:
            data = await request.json()
            enabled = data.get("enabled", False)
            
            # Import and modify global variable
            import service.central.central_agent as central_module
            central_module.FORCE_NEGOTIATION_TEST = enabled
            
            # Update all drones
            for drone in self.agent.drones:
                drone.available = not enabled
            
            return {
                "success": True,
                "test_mode": enabled,
                "message": "Test mode enabled - all drones unavailable" if enabled else "Test mode disabled"
            }
        except Exception as e:
            return {"error": str(e), "success": False}
