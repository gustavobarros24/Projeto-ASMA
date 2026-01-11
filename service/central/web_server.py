"""
Web Server for Central Agent Dashboard
Separate from SPADE agent - uses aiohttp (already installed with SPADE)
"""
from aiohttp import web, ClientSession
import os
import asyncio

# Central Agent API base URL
CENTRAL_API = "http://127.0.0.1:10000"

async def index_handler(request):
    """Main dashboard page"""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    html_content = html_content.replace("{{ agent_jid }}", "central@localhost")
    return web.Response(text=html_content, content_type='text/html')

async def proxy_get(request, endpoint):
    """Generic GET proxy to central agent API"""
    try:
        async with ClientSession() as session:
            async with session.get(f"{CENTRAL_API}{endpoint}", timeout=5) as response:
                data = await response.json()
                return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def proxy_post(request, endpoint):
    """Generic POST proxy to central agent API"""
    try:
        body = await request.json()
        async with ClientSession() as session:
            async with session.post(f"{CENTRAL_API}{endpoint}", json=body, timeout=5) as response:
                data = await response.json()
                return web.json_response(data)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# Route handlers
async def get_drones(request):
    return await proxy_get(request, "/api/drones")

async def get_companies(request):
    return await proxy_get(request, "/api/companies")

async def get_negotiations(request):
    return await proxy_get(request, "/api/negotiations")

async def get_stats(request):
    return await proxy_get(request, "/api/stats")

async def toggle_drone(request):
    return await proxy_post(request, "/api/toggle-drone")

async def test_mode(request):
    return await proxy_post(request, "/api/test-mode")

def create_app():
    app = web.Application()
    
    # Routes
    app.router.add_get('/', index_handler)
    app.router.add_get('/api/drones', get_drones)
    app.router.add_get('/api/companies', get_companies)
    app.router.add_get('/api/negotiations', get_negotiations)
    app.router.add_get('/api/stats', get_stats)
    app.router.add_post('/api/toggle-drone', toggle_drone)
    app.router.add_post('/api/test-mode', test_mode)
    
    return app

if __name__ == '__main__':
    print("="*80)
    print("Central Agent Web Dashboard")
    print("="*80)
    print("Dashboard: http://127.0.0.1:5000")
    print("Central Agent API: http://127.0.0.1:10000")
    print("="*80)
    print("Press Ctrl+C to stop\n")
    
    app = create_app()
    web.run_app(app, host='127.0.0.1', port=5000, print=None)
