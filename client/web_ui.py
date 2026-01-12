import json
import os
import asyncio
from aiohttp import web
from typing import Dict
from client.client_agent import ClientAgent
from config.config import COMPANIES_PATH

"""
===============================================================================
    Web UI for Client using aiohttp (comes with SPADE)
===============================================================================
"""

class ClientWebUI:
    def __init__(self, client: ClientAgent, port: int = 5001):
        self.client = client
        self.port = port
        self.app = web.Application()
        self._setup_routes()
        self.companies = self._load_companies()
        self.runner = None

    def _load_companies(self) -> Dict[str, dict]:
        """Load companies from JSON file."""
        try:
            with open(COMPANIES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            companies = {}
            for company in data.get("companies", []):
                companies[company["id"]] = company
            return companies
        except Exception as e:
            print(f"Error loading companies: {e}")
            return {}

    def _load_template(self, template_name: str, **context) -> str:
        """Load and render a template with context."""
        template_path = os.path.join(os.path.dirname(__file__), "templates", template_name)
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple template replacement
        for key, value in context.items():
            if isinstance(value, dict):
                # For dict values, convert to JSON
                content = content.replace(f"{{{{ {key} }}}}", json.dumps(value))
            else:
                content = content.replace(f"{{{{ {key} }}}}", str(value))
        
        # Handle Jinja2-like loops and conditionals (simplified)
        return content

    def _render_home(self) -> str:
        """Render home page."""
        template_path = os.path.join(os.path.dirname(__file__), "templates", "home.html")
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace variables
        content = content.replace("{{ budget }}", f"{self.client.budget:.2f}")
        content = content.replace("{{ location }}", str(self.client.location))
        content = content.replace("{{ client_id }}", self.client.jid.local)
        
        # Build companies grid
        companies_html = ""
        for company_id, company in self.companies.items():
            companies_html += f'''
                <a href="/company/{company_id}" class="company-card">
                    <div class="company-name">{company['name']}</div>
                    <div class="company-url">🌐 {company['url']}</div>
                    <div class="company-id">ID: {company_id}</div>
                </a>
            '''
        
        # Replace companies placeholder
        content = content.replace("<!-- Companies will be inserted here -->", companies_html)
        
        return content

    def _render_company(self, company_id: str) -> str:
        """Render company page."""
        template_path = os.path.join(os.path.dirname(__file__), "templates", "company.html")
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        company = self.companies.get(company_id, {})
        
        # Replace variables
        content = content.replace("{{ company.name }}", company.get('name', 'Unknown'))
        content = content.replace("{{ company.url }}", company.get('url', ''))
        content = content.replace("{{ company_id }}", company_id)
        content = content.replace("{{ budget }}", f"{self.client.budget:.2f}")
        content = content.replace("{{ location }}", str(self.client.location))
        content = content.replace("{{ client_id }}", self.client.jid.local)
        
        # Get items for this company
        items = {}
        for item_id, item in self.client.available_items_cache.items():
            if item.company_id == company_id:
                items[item_id] = item
        
        # Build items grid
        items_html = ""
        if items:
            items_html = f'<h2 class="section-title">📦 Produtos Disponíveis ({len(items)})</h2><div class="items-grid">'
            for item_id, item in items.items():
                # Escape quotes for JavaScript
                safe_name = item.name.replace("'", "\\'").replace('"', '&quot;')
                items_html += f'''
        <div class="item-card">
            <div class="item-name">{item.name}</div>
            <div class="item-price">💵 {item.price_usd:.2f} USD</div>
            <div class="item-details">📦 Peso: {item.weight_kg} kg</div>
            <div class="item-details">📄 {item.description}</div>
            <div class="item-details">🔖 ID: {item_id}</div>
            <button class="buy-btn" onclick="buyItem('{item_id}', '{safe_name}', {item.price_usd})">
                🛒 Comprar
            </button>
        </div>
                '''
            items_html += '</div>'
        else:
            items_html = '<div class="alert alert-info">Nenhum produto carregado. Clique em "🔄 Encontrar Inventário" para ver os produtos disponíveis.</div>'
        
        # Replace items placeholder
        content = content.replace("<!-- Items will be inserted here -->", items_html)
        
        return content

    def _render_purchases(self) -> str:
        """Render purchases page."""
        template_path = os.path.join(os.path.dirname(__file__), "templates", "purchases.html")
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Calculate stats
        total_items = sum(len(items) for items in self.client.inventory.values())
        total_spent = sum(
            item.price_usd 
            for items in self.client.inventory.values() 
            for item in items.values()
        )
        
        # Replace variables
        content = content.replace("{{ budget }}", f"{self.client.budget:.2f}")
        content = content.replace("{{ location }}", str(self.client.location))
        content = content.replace("{{ client_id }}", self.client.jid.local)
        content = content.replace("{{ pending_orders|length }}", str(len(self.client.pending_orders)))
        content = content.replace("{{ total_items }}", str(total_items))
        content = content.replace('{{ "%.2f"|format(total_spent) }}', f"{total_spent:.2f}")
        
        # Build purchases HTML
        purchases_html = ""
        
        if self.client.pending_orders or self.client.inventory:
            # Stats
            purchases_html += '<div class="stats">'
            purchases_html += f'''
    <div class="stat-card">
        <div class="stat-value">{len(self.client.pending_orders)}</div>
        <div class="stat-label">Pedidos Pendentes</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{total_items}</div>
        <div class="stat-label">Items Comprados</div>
    </div>
    <div class="stat-card">
        <div class="stat-value">{total_spent:.2f} USD</div>
        <div class="stat-label">Total Gasto</div>
    </div>
            '''
            purchases_html += '</div><div class="purchases-list">'
            
            # Pending orders
            if self.client.pending_orders:
                purchases_html += '<h2 style="color: #333; margin-top: 20px;"> Pedidos Pendentes</h2>'
                for order_id, company_id in self.client.pending_orders.items():
                    purchases_html += f'''
    <div class="purchase-card">
        <div class="purchase-header">
            <div>
                <div class="purchase-item-name">Pedido #{order_id[:8]}</div>
                <div class="detail-item">Empresa: {company_id}</div>
            </div>
        </div>
        <span class="status-badge status-pending">Aguardando Entrega</span>
    </div>
                    '''
            
            # Delivered items
            if self.client.inventory:
                purchases_html += '<h2 style="color: #333; margin-top: 30px;"> Items Recebidos</h2>'
                for company_id, items in self.client.inventory.items():
                    for item_id, item in items.items():
                        purchases_html += f'''
    <div class="purchase-card">
        <div class="purchase-header">
            <div>
                <div class="purchase-item-name">{item.name}</div>
            </div>
            <div class="purchase-price"> {item.price_usd:.2f} USD</div>
        </div>
        <div class="purchase-details">
            <div>
                <div class="detail-label">Empresa</div>
                <div class="detail-item">{company_id}</div>
            </div>
            <div>
                <div class="detail-label">Peso</div>
                <div class="detail-item">{item.weight_kg} kg</div>
            </div>
            <div>
                <div class="detail-label">Descrição</div>
                <div class="detail-item">{item.description}</div>
            </div>
            <div>
                <div class="detail-label">ID do Item</div>
                <div class="detail-item" style="font-family: monospace; font-size: 12px;">{item_id}</div>
            </div>
        </div>
        <span class="status-badge status-delivered"> Entregue</span>
    </div>
                        '''
            
            purchases_html += '</div>'
        else:
            purchases_html = '''
<div class="empty-state">
    <div class="empty-state-icon">🛒</div>
    <div class="empty-state-title">Nenhuma compra realizada</div>
    <div class="empty-state-text">Você ainda não fez nenhuma compra. Explore as empresas disponíveis!</div>
    <a href="/" class="goto-home-btn">🏢 Ver Empresas</a>
</div>
            '''
        
        # Replace content placeholder
        content = content.replace("<!-- Content will be inserted here -->", purchases_html)
        
        return content

    def _setup_routes(self):
        """Setup aiohttp routes."""
        
        async def home_handler(request):
            """Home page with list of companies."""
            html = self._render_home()
            return web.Response(text=html, content_type='text/html')

        async def company_handler(request):
            """Company page with items."""
            company_id = request.match_info['company_id']
            if company_id not in self.companies:
                return web.Response(text="Company not found", status=404)
            
            html = self._render_company(company_id)
            return web.Response(text=html, content_type='text/html')

        async def purchases_handler(request):
            """Purchases page."""
            html = self._render_purchases()
            return web.Response(text=html, content_type='text/html')

        async def fetch_inventory_handler(request):
            """API endpoint to fetch inventory from a company."""
            company_id = request.match_info['company_id']
            try:
                await self.client.get_inventory(company_id)
                return web.json_response({
                    'success': True,
                    'message': f'Inventory request sent to {company_id}'
                })
            except Exception as e:
                return web.json_response({
                    'success': False,
                    'message': str(e)
                }, status=500)

        async def buy_item_handler(request):
            """API endpoint to buy an item."""
            try:
                data = await request.json()
                company_id = data.get('company_id')
                item_id = data.get('item_id')
                
                if not company_id or not item_id:
                    return web.json_response({
                        'success': False,
                        'message': 'Missing company_id or item_id'
                    }, status=400)
                
                if item_id not in self.client.available_items_cache:
                    return web.json_response({
                        'success': False,
                        'message': 'Item not found in cache'
                    }, status=404)
                
                await self.client.buy_item(company_id, item_id)
                
                return web.json_response({
                    'success': True,
                    'message': f'Purchase request sent for item {item_id}'
                })
            except Exception as e:
                return web.json_response({
                    'success': False,
                    'message': str(e)
                }, status=500)

        async def client_info_handler(request):
            """API endpoint to get client information."""
            return web.json_response({
                'client_id': self.client.jid.local,
                'budget': self.client.budget,
                'location': str(self.client.location),
                'pending_orders': len(self.client.pending_orders),
                'cache_size': len(self.client.available_items_cache),
                'inventory_size': sum(len(items) for items in self.client.inventory.values())
            })

        # Register routes
        self.app.router.add_get('/', home_handler)
        self.app.router.add_get('/company/{company_id}', company_handler)
        self.app.router.add_get('/purchases', purchases_handler)
        self.app.router.add_post('/api/fetch_inventory/{company_id}', fetch_inventory_handler)
        self.app.router.add_post('/api/buy_item', buy_item_handler)
        self.app.router.add_get('/api/client_info', client_info_handler)

    async def start(self):
        """Start the aiohttp server."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, '0.0.0.0', self.port)
            await site.start()
            print(f" Web server started successfully on http://0.0.0.0:{self.port}")
        except Exception as e:
            print(f" Error starting web server: {e}")
            raise

    async def stop(self):
        """Stop the aiohttp server."""
        if self.runner:
            await self.runner.cleanup()
