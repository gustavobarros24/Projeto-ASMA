# Projeto-ASMA

Sistema Multi-Agente para gestão e entrega de drones com interface web.

# Setup

## 1. Create the Conda Environment

Run the following command in your terminal or Anaconda Prompt:

```bash
conda env create -f environment.yml
```

## 2. Activate Environment

Activate the environment with:

```bash
conda activate ASMA
```

# 3. Update Environment

Update the environment with:

```bash
conda env update -f environment.yml --prune
```

## 4. SPADE Setup

For SPADE to work, the DOMAIN needs to be the PC name.

---

## Teste rápido de multiplos clientes

**A forma mais simples de executar tudo num único processo! wow**

### Executar tudo de uma vez
```bash
python -m tests.run_all
```

Isto inicia automaticamente:
- ✅ Agente Central (API na porta 10000)
- ✅ Agentes de Empresas (WALMART, AMAZON, APPLE, IKEA, ALIBABA, NIKE)
- ✅ Agentes de Drones (5 drones)
- ✅ Agente Cliente (cliente com orçamento de $5000)
- ✅ Dashboard Central (porta 5000)
- ✅ Interface Web do Cliente (porta 5001)

### Acessos
- **Dashboard Central**: http://127.0.0.1:5000
  - Monitorizar drones, empresas e negociações
  
- **Interface do Cliente**: http://localhost:5001
  - Ver empresas disponíveis
  - Buscar inventário de produtos
  - Comprar items
  - Acompanhar entregas

### Vantagens
- ✅ Todos os agentes no mesmo processo → comunicação XMPP funciona perfeitamente
- ✅ Apenas 1 comando para iniciar tudo
- ✅ Interface completa para o cliente fazer compras
- ✅ Sistema completo operacional

---

## Opção 2: Sistema Separado (Backend + Frontend)

### Terminal 1 - Iniciar Agentes (Backend)
```bash
python service/main.py
```

Isto inicia:
- Agente Central (com API na porta 10000)
- Agentes de Empresas (WALMART, AMAZON, APPLE, IKEA, ALIBABA, NIKE)
- Agentes de Drones

### Terminal 2 - Iniciar Dashboard Web (Frontend)
```bash
python service/central/web_server.py
```

Isto inicia:
- Servidor web na porta 5000
- Dashboard interativo

### Abrir no Browser
```
Dashboard Central: http://127.0.0.1:5000
```

**Nota**: Esta opção NÃO inclui o cliente. Use `run_all.py` para ter sistema completo com interface do cliente.

---

## 📱 Interface Web do Cliente

### Páginas Disponíveis

**1. Home (Lista de Empresas)**
- Visualiza todas as empresas disponíveis
- Mostra orçamento atual e localização do cliente
- Clica numa empresa para ver produtos

**2. Página da Empresa**
- Botão "🔄 Encontrar Inventário" para carregar produtos
- Lista de produtos com nome, preço, peso e descrição
- Botão "🛒 Comprar" para cada item
- Atualização automática após buscar inventário

**3. Minhas Compras**
- Estatísticas: pedidos pendentes, items comprados, total gasto
- ⏳ Pedidos Pendentes: Entregas em curso
- ✅ Items Recebidos: Produtos já entregues com sucesso
- Detalhes completos de cada compra

### Fluxo de Compra
1. Cliente acede à interface web
2. Escolhe uma empresa
3. Clica "Encontrar Inventário" (sistema pede à empresa)
4. Escolhe produto e clica "Comprar"
5. Sistema processa:
   - Cliente envia pedido → Empresa
   - Empresa solicita drone → Central
   - Central atribui drone disponível
   - Drone recolhe e entrega o pacote
6. Item aparece em "Minhas Compras" quando entregue

---

##  Dashboard - Funcionalidades

- **Estatísticas em Tempo Real**: Total de drones, disponibilidade, capacidade
- **Gestão de Drones**: Ver status, bateria, capacidade de cada drone
- **Empresas Registadas**: Lista de todas as empresas no sistema
- **Negociações Ativas**: Monitorizar negociações de empréstimo de drones entre empresas
- **Controlos**:
  - Refresh manual dos dados
  - Test Mode: Força negociações (marca todos os drones como indisponíveis)
  - Toggle de disponibilidade de drones individuais

### Auto-refresh
O dashboard atualiza automaticamente a cada 5 segundos.

---

##  Modo de Teste (Test Mode)

### O que é?
Modo especial para testar a funcionalidade de **negociação de drones entre empresas**.

### Como ativar?
1. No dashboard, clique em "Enable Test Mode"
2. Todos os drones da central ficam indisponíveis
3. Sistema é forçado a negociar com outras empresas

### Para que serve?
Testa se quando uma empresa (ex: WALMART) precisa de um drone mas a central não tem disponível:
- Sistema pergunta a outras empresas (AMAZON, APPLE, etc.)
- Negoceia empréstimo de drones
- Completa a entrega com drone emprestado

---

## API Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/drones` | GET | Lista todos os drones e status |
| `/api/companies` | GET | Lista empresas registadas |
| `/api/negotiations` | GET | Negociações ativas |
| `/api/stats` | GET | Estatísticas gerais |
| `/api/toggle-drone` | POST | Alterna disponibilidade de drone |
| `/api/test-mode` | POST | Ativa/desativa modo de teste |

---

![](https://imgs.search.brave.com/hvxr59zlk5sOIJJQ12_HzcWd5u-aMxfbApap8Zj7wRQ/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly9jZG4u/d2FsbHBhcGVyc2Fm/YXJpLmNvbS80OS8x/My9FVHBrOHQuanBn)