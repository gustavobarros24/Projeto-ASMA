import json
import asyncio

from typing import Dict
from client_agent import *
from utils.logger import *
from utils.utils import *

"""
===============================================================================

	UI

===============================================================================
"""

# temporary file, only for tests. it will be eliminated in the future...

def _load_companies(path: str) -> Dict[str, dict]:
	"""
	Load companies from a JSON file.
	Returns a dict keyed by company id.
	"""
	with open(path, "r", encoding="utf-8") as f:
		data = json.load(f)

	companies = {}
	for company in data.get("companies", []):
		companies[company["id"]] = company

	return companies

async def terminal_ui(client: ClientAgent):
	loop = asyncio.get_running_loop()
	"""
	Very simple terminal UI.
	Blocking input is OK here because the agent runs independently.
	"""
	HELP = """
Commands:
help                         Show this help
fetch <company_jid>          Fetch inventory from a company
list                         List cached inventory
buy <company_jid> <item_id>  Buy an item
clear                        Clear inventory cache
exit                         Exit
"""

	print(HELP)
	companies = _load_companies( COMPANIES_PATH )

	while True:
		for cid, company in companies.items():
			print(
				f"- {cid}: {company['name']} | {company['url']}"
			)
		
		try:
			raw = await loop.run_in_executor(None, input)
			raw = raw.strip()
		except (EOFError, KeyboardInterrupt):
			print("\nExiting...")
			break

		if not raw:
			continue

		parts = raw.split()
		cmd = parts[0]

		if cmd == "help":
			print(HELP)

		elif cmd == "fetch" and len(parts) == 2:
			company_jid = parts[1]
			await client.get_inventory(company_jid)
			print(f"Requested inventory from {company_jid}")


		elif cmd == "list":
			if not client.available_items_cache:
				print("Inventory cache is empty")
				continue

			for item_id, item in client.available_items_cache.items():
				print(
					f"- {item_id}: {item.name} | "
					f"price={item.price_usd} | company={item.company_id}"
				)

		elif cmd == "buy" and len(parts) == 3:
			company_jid = parts[1]
			item_id = parts[2]

			if item_id not in client.available_items_cache:
				print("Item not in cache. Fetch inventory first.")
				continue

			await client.buy_item(company_jid, item_id)
			print(f"Buy request sent for item {item_id}")

		elif cmd == "clear":
			await client.clean_cache()
			print("Inventory cache cleared")

		elif cmd == "exit":
			print("Shutting down...")
			break

		else:
			print("Unknown command. Type 'help'.")