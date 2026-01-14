import os
import asyncio
from aiohttp import web
from typing import Dict
from service.company.company_agent import CompanyAgent

"""
===============================================================================
    Web UI for Company using aiohttp
===============================================================================
"""

class CompanyWebUI:
    def __init__(self, company: CompanyAgent, port: int = 6001):
        self.company = company
        self.port = port
        self.app = web.Application()
        self._setup_routes()
        self.runner = None

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get('/', self.handle_home)
        self.app.router.add_get('/inventory', self.handle_inventory_page)
        self.app.router.add_get('/packages', self.handle_packages_page)
        self.app.router.add_get('/drones', self.handle_drones_page)
        self.app.router.add_get('/api/inventory', self.handle_get_inventory)
        self.app.router.add_get('/api/packages', self.handle_get_packages)
        self.app.router.add_get('/api/drones', self.handle_get_drones)
        self.app.router.add_get('/api/stats', self.handle_get_stats)

    async def handle_home(self, request):
        """Render company dashboard."""
        html = self._render_dashboard()
        return web.Response(text=html, content_type='text/html')

    async def handle_inventory_page(self, request):
        """Render inventory page."""
        html = self._render_inventory_page()
        return web.Response(text=html, content_type='text/html')

    async def handle_packages_page(self, request):
        """Render packages page."""
        html = self._render_packages_page()
        return web.Response(text=html, content_type='text/html')

    async def handle_drones_page(self, request):
        """Render drones page."""
        html = self._render_drones_page()
        return web.Response(text=html, content_type='text/html')

    async def handle_get_inventory(self, request):
        """Get inventory as JSON."""
        inventory_data = []
        for item_id, item in self.company.inventory.items():
            inventory_data.append({
                'id': item.id,
                'name': item.name,
                'price': item.price_usd,
                'weight': item.weight_kg,
                'description': item.description,
                'company_id': item.company_id,
                'category': 'Produto'
            })
        return web.json_response({'inventory': inventory_data})

    async def handle_get_packages(self, request):
        """Get pending packages."""
        packages_list = []
        
        # Get packages from queue (non-blocking peek)
        temp_packages = []
        while not self.company.packages_to_send.empty():
            try:
                pkg = self.company.packages_to_send.get_nowait()
                temp_packages.append(pkg)
                packages_list.append({
                    'order_id': pkg.order_id,
                    'client_id': pkg.client_id,
                    'destination': str(pkg.location),
                    'weight': pkg.item.weight_kg,
                    'item_name': pkg.item.name,
                    'item_id': pkg.item.id,
                    'status': 'Na Fila'
                })
            except Exception as e:
                print(f"Error getting package: {e}")
                break
        
        # Put them back
        for pkg in temp_packages:
            await self.company.packages_to_send.put(pkg)
        
        # Add packages in delivery
        for pkg in self.company.packages_in_delivery:
            packages_list.append({
                'order_id': pkg.order_id,
                'client_id': pkg.client_id,
                'destination': str(pkg.location),
                'weight': pkg.item.weight_kg,
                'item_name': pkg.item.name,
                'item_id': pkg.item.id,
                'status': 'Em Entrega'
            })
        
        # Add delivered packages
        for pkg in self.company.packages_delivered:
            packages_list.append({
                'order_id': pkg.order_id,
                'client_id': pkg.client_id,
                'destination': str(pkg.location),
                'weight': pkg.item.weight_kg,
                'item_name': pkg.item.name,
                'item_id': pkg.item.id,
                'status': 'Entregue'
            })
        
        return web.json_response({'packages': packages_list, 'count': len(packages_list)})

    async def handle_get_drones(self, request):
        """Get rented drones."""
        drones_data = []
        for drone in self.company.rented_drones:
            drones_data.append({
                'id': drone.id,
                'model': drone.model,
                'capacity_kg': drone.capacity_kg,
                'speed_kmh': drone.speed_kmh,
                'battery_level': drone.battery_percent,
                'available': drone.available,
                'current_position': str(drone.current_position)
            })
        return web.json_response({'drones': drones_data, 'count': len(drones_data)})

    async def handle_get_stats(self, request):
        """Get company statistics."""
        total_items = len(self.company.inventory)
        total_value = sum(item.price_usd for item in self.company.inventory.values())
        
        return web.json_response({
            'company_id': self.company.jid.node,
            'budget': self.company.budget,
            'location': str(self.company.location),
            'inventory_items': len(self.company.inventory),
            'total_quantity': total_items,
            'total_value': total_value,
            'rented_drones': len(self.company.rented_drones)
        })

    def _render_dashboard(self) -> str:
        """Render company dashboard HTML."""
        template_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
        
        # If template doesn't exist, use inline HTML
        if not os.path.exists(template_path):
            return self._get_inline_dashboard()
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace variables
        content = content.replace("{{ company_id }}", self.company.jid.node)
        content = content.replace("{{ budget }}", f"{self.company.budget:.2f}")
        content = content.replace("{{ location }}", str(self.company.location))
        
        return content

    def _get_inline_dashboard(self) -> str:
        """Get inline dashboard HTML."""
        return f"""
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Empresa {self.company.jid.node} - Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .company-info {{
            color: #666;
            font-size: 1.1em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            border-left: 5px solid #667eea;
        }}
        .stat-label {{
            color: #999;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .section {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }}
        .section-title {{
            font-size: 1.5em;
            color: #667eea;
            margin-bottom: 20px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #667eea;
            border-bottom: 2px solid #667eea;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .refresh-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            margin-top: 20px;
            transition: all 0.3s;
        }}
        .refresh-btn:hover {{
            background: #218838;
            transform: translateY(-2px);
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 Empresa {self.company.jid.node}</h1>
            <div class="company-info">
                <p>📍 Localização: {self.company.location}</p>
                <p>💰 Orçamento: ${self.company.budget:.2f}</p>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">📦 Itens em Inventário</div>
                <div class="stat-value" id="inventory-count">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📊 Quantidade Total</div>
                <div class="stat-value" id="total-quantity">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">💵 Valor Total</div>
                <div class="stat-value" id="total-value">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">🚁 Drones Alugados</div>
                <div class="stat-value" id="drones-count">-</div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📦 Inventário</h2>
            <div id="inventory-container">
                <div class="loading">Carregando inventário...</div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📮 Pacotes Pendentes</h2>
            <div id="packages-container">
                <div class="loading">Carregando pacotes...</div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">🚁 Drones Alugados</h2>
            <div id="drones-container">
                <div class="loading">Carregando drones...</div>
            </div>
        </div>

        <button class="refresh-btn" onclick="loadAllData()">🔄 Atualizar Dados</button>
    </div>

    <script>
        async function loadStats() {{
            try {{
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('inventory-count').textContent = data.inventory_items;
                document.getElementById('total-quantity').textContent = data.total_quantity;
                document.getElementById('total-value').textContent = '$' + data.total_value.toFixed(2);
                document.getElementById('drones-count').textContent = data.rented_drones;
            }} catch (error) {{
                console.error('Error loading stats:', error);
            }}
        }}

        async function loadInventory() {{
            try {{
                const response = await fetch('/api/inventory');
                const data = await response.json();
                
                const container = document.getElementById('inventory-container');
                
                if (data.inventory.length === 0) {{
                    container.innerHTML = '<p>Nenhum item no inventário.</p>';
                    return;
                }}
                
                let html = '<table><tr><th>Nome</th><th>Preço</th><th>Peso</th><th>Quantidade</th><th>Categoria</th></tr>';
                
                data.inventory.forEach(item => {{
                    html += `<tr>
                        <td>${{item.name}}</td>
                        <td>$${{item.price.toFixed(2)}}</td>
                        <td>${{item.weight}} kg</td>
                        <td>${{item.quantity}}</td>
                        <td>${{item.category}}</td>
                    </tr>`;
                }});
                
                html += '</table>';
                container.innerHTML = html;
            }} catch (error) {{
                document.getElementById('inventory-container').innerHTML = '<p>Erro ao carregar inventário.</p>';
                console.error('Error loading inventory:', error);
            }}
        }}

        async function loadPackages() {{
            try {{
                const response = await fetch('/api/packages');
                const data = await response.json();
                
                const container = document.getElementById('packages-container');
                
                if (data.packages.length === 0) {{
                    container.innerHTML = '<p>Nenhum pacote pendente.</p>';
                    return;
                }}
                
                let html = '<table><tr><th>ID</th><th>Destino</th><th>Peso</th><th>Itens</th></tr>';
                
                data.packages.forEach(pkg => {{
                    html += `<tr>
                        <td>${{pkg.id}}</td>
                        <td>${{pkg.destination}}</td>
                        <td>${{pkg.weight}} kg</td>
                        <td>${{pkg.items_count}}</td>
                    </tr>`;
                }});
                
                html += '</table>';
                container.innerHTML = html;
            }} catch (error) {{
                document.getElementById('packages-container').innerHTML = '<p>Erro ao carregar pacotes.</p>';
                console.error('Error loading packages:', error);
            }}
        }}

        async function loadDrones() {{
            try {{
                const response = await fetch('/api/drones');
                const data = await response.json();
                
                const container = document.getElementById('drones-container');
                
                if (data.drones.length === 0) {{
                    container.innerHTML = '<p>Nenhum drone alugado.</p>';
                    return;
                }}
                
                let html = '<table><tr><th>ID</th><th>Alcance Máx.</th><th>Carga Máx.</th><th>Bateria</th></tr>';
                
                data.drones.forEach(drone => {{
                    html += `<tr>
                        <td>${{drone.id}}</td>
                        <td>${{drone.max_range}} km</td>
                        <td>${{drone.max_load}} kg</td>
                        <td>${{drone.battery_level}}%</td>
                    </tr>`;
                }});
                
                html += '</table>';
                container.innerHTML = html;
            }} catch (error) {{
                document.getElementById('drones-container').innerHTML = '<p>Erro ao carregar drones.</p>';
                console.error('Error loading drones:', error);
            }}
        }}

        async function loadAllData() {{
            await loadStats();
            await loadInventory();
            await loadPackages();
            await loadDrones();
        }}

        // Load data on page load
        window.addEventListener('load', loadAllData);
        
        // Auto-refresh every 5 seconds
        setInterval(loadAllData, 5000);
    </script>
</body>
</html>
"""

    def _render_inventory_page(self) -> str:
        """Render dedicated inventory page."""
        return self._get_page_template("Inventário", """
            <div class="section">
                <h2 class="section-title">📦 Inventário de Produtos</h2>
                <div id="inventory-container">
                    <div class="loading">
                        <div class="spinner"></div>
                        Carregando inventário...
                    </div>
                </div>
            </div>
            <script>
                async function loadInventory() {
                    try {
                        const response = await fetch('/api/inventory');
                        const data = await response.json();
                        const container = document.getElementById('inventory-container');
                        
                        if (data.inventory.length === 0) {
                            container.innerHTML = '<div class="empty-state">📭 Nenhum item no inventário.</div>';
                            return;
                        }
                        
                        let html = `<table><tr><th>ID</th><th>Nome</th><th>Preço</th><th>Peso</th><th>Descrição</th></tr>`;
                        data.inventory.forEach(item => {
                            html += `<tr>
                                <td><span class="badge">${item.id}</span></td>
                                <td><strong>${item.name}</strong></td>
                                <td>$${item.price.toFixed(2)}</td>
                                <td>${item.weight.toFixed(2)} kg</td>
                                <td>${item.description || 'N/A'}</td>
                            </tr>`;
                        });
                        html += '</table>';
                        container.innerHTML = html;
                    } catch (error) {
                        document.getElementById('inventory-container').innerHTML = 
                            '<div class="empty-state">❌ Erro ao carregar inventário.</div>';
                    }
                }
                loadInventory();
                setInterval(loadInventory, 5000);
            </script>
        """)

    def _render_packages_page(self) -> str:
        """Render dedicated packages page."""
        return self._get_page_template("Pacotes", """
            <div class="section">
                <h2 class="section-title">📦 Gestão de Pacotes</h2>
                <div id="packages-container">
                    <div class="loading">
                        <div class="spinner"></div>
                        Carregando pacotes...
                    </div>
                </div>
            </div>
            <script>
                async function loadPackages() {
                    try {
                        const response = await fetch('/api/packages');
                        const data = await response.json();
                        const container = document.getElementById('packages-container');
                        
                        if (data.packages.length === 0) {
                            container.innerHTML = '<div class="empty-state">📭 Nenhum pacote.</div>';
                            return;
                        }
                        
                        let html = `<table><tr><th>ID do Pedido</th><th>Cliente</th><th>Item</th><th>Destino</th><th>Peso</th><th>Status</th></tr>`;
                        data.packages.forEach(pkg => {
                            let statusClass = 'warning';
                            if (pkg.status === 'Em Entrega') statusClass = 'info';
                            if (pkg.status === 'Entregue') statusClass = 'success';
                            
                            html += `<tr>
                                <td><span class="badge">${pkg.order_id}</span></td>
                                <td><span class="badge info">${pkg.client_id}</span></td>
                                <td>${pkg.item_name}</td>
                                <td style="font-size: 0.9em;">${pkg.destination}</td>
                                <td>${pkg.weight.toFixed(2)} kg</td>
                                <td><span class="badge ${statusClass}">${pkg.status}</span></td>
                            </tr>`;
                        });
                        html += '</table>';
                        container.innerHTML = html;
                    } catch (error) {
                        document.getElementById('packages-container').innerHTML = 
                            '<div class="empty-state">❌ Erro ao carregar pacotes.</div>';
                    }
                }
                loadPackages();
                setInterval(loadPackages, 5000);
            </script>
        """)

    def _render_drones_page(self) -> str:
        """Render dedicated drones page."""
        return self._get_page_template("Drones", """
            <div class="section">
                <h2 class="section-title">🚁 Frota de Drones</h2>
                <div id="drones-container">
                    <div class="loading">
                        <div class="spinner"></div>
                        Carregando drones...
                    </div>
                </div>
            </div>
            <script>
                async function loadDrones() {
                    try {
                        const response = await fetch('/api/drones');
                        const data = await response.json();
                        const container = document.getElementById('drones-container');
                        
                        if (data.drones.length === 0) {
                            container.innerHTML = '<div class="empty-state">🚁 Nenhum drone alugado.</div>';
                            return;
                        }
                        
                        let html = `<table><tr><th>ID</th><th>Modelo</th><th>Capacidade</th><th>Velocidade</th><th>Bateria</th><th>Status</th><th>Posição</th></tr>`;
                        data.drones.forEach(drone => {
                            let batteryClass = 'success';
                            if (drone.battery_level < 50) batteryClass = 'warning';
                            if (drone.battery_level < 20) batteryClass = '';
                            
                            let statusClass = drone.available ? 'success' : 'warning';
                            let statusText = drone.available ? 'Disponível' : 'Em uso';
                            
                            html += `<tr>
                                <td><span class="badge">${drone.id}</span></td>
                                <td>${drone.model}</td>
                                <td>${drone.capacity_kg.toFixed(2)} kg</td>
                                <td>${drone.speed_kmh.toFixed(1)} km/h</td>
                                <td><span class="badge ${batteryClass}">${drone.battery_level}%</span></td>
                                <td><span class="badge ${statusClass}">${statusText}</span></td>
                                <td style="font-size: 0.85em;">${drone.current_position}</td>
                            </tr>`;
                        });
                        html += '</table>';
                        container.innerHTML = html;
                    } catch (error) {
                        document.getElementById('drones-container').innerHTML = 
                            '<div class="empty-state">❌ Erro ao carregar drones.</div>';
                    }
                }
                loadDrones();
                setInterval(loadDrones, 5000);
            </script>
        """)

    def _get_page_template(self, page_title: str, content: str) -> str:
        """Get a generic page template with navigation."""
        return f"""
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title} - Empresa {self.company.jid.node}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        .header {{
            background: white;
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.3);
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ color: #1e3c72; font-size: 2.5em; }}
        .nav {{
            display: flex;
            gap: 15px;
        }}
        .nav a {{
            color: #1e3c72;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 8px;
            transition: all 0.3s;
            font-weight: 600;
            font-size: 1em;
        }}
        .nav a:hover {{
            background: #1e3c72;
            color: white;
        }}
        .section {{
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 1.8em;
            color: #1e3c72;
            margin-bottom: 25px;
            border-bottom: 3px solid #1e3c72;
            padding-bottom: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
        }}
        th {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 18px;
            text-align: left;
            font-weight: 600;
            color: white;
            font-size: 1.05em;
        }}
        th:first-child {{ border-top-left-radius: 10px; }}
        th:last-child {{ border-top-right-radius: 10px; }}
        td {{
            padding: 16px 18px;
            border-bottom: 1px solid #e9ecef;
            color: #333;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover {{ background: #f8f9fa; }}
        .loading {{
            text-align: center;
            padding: 50px;
            color: #666;
            font-size: 1.2em;
        }}
        .spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #1e3c72;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .empty-state {{
            text-align: center;
            padding: 40px;
            color: #999;
            font-size: 1.1em;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            background: #e9ecef;
            color: #495057;
        }}
        .badge.success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge.warning {{
            background: #fff3cd;
            color: #856404;
        }}
        .badge.info {{
            background: #d1ecf1;
            color: #0c5460;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 Empresa {self.company.jid.node}</h1>
            <nav class="nav">
                <a href="/">Dashboard</a>
                <a href="/inventory">Inventário</a>
                <a href="/packages">Pacotes</a>
                <a href="/drones">Drones</a>
            </nav>
        </div>
        {content}
    </div>
</body>
</html>
"""

    async def start(self):
        """Start web server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '127.0.0.1', self.port)
        await site.start()
        print(f"Company Web UI started at http://127.0.0.1:{self.port}")

    async def stop(self):
        """Stop web server."""
        if self.runner:
            await self.runner.cleanup()
