from spade.behaviour import CyclicBehaviour
from common.package import *
from utils.logger import *
from utils.utils import *
from common.packet import *
from utils.communication import *

"""
===============================================================================

	Receiver Behaviour (Company)

===============================================================================
"""

_TIMEOUT = 1 # second
_LENDING_FEE_PER_KM = 0.20  # fee per km for lending drone
_BASE_LENDING_FEE = 2.0     # base fee for lending

#log = logging.getLogger( __name__ )

class ReceiverBehaviour( CyclicBehaviour ):
	def __init__( self, *, log = None):
		super().__init__()
		self.log = log
		# Track drones lent to other companies: {drone_id: {"lender": company_id, "drone": DroneInfo}}
		self.borrowed_drones = {}

	async def run( self ):
		log = self.log

		msg = await self.receive( timeout = _TIMEOUT )
		if not msg:
			return

		log.info( "Received a message..." )
		try:
			packet = Packet.deserialize( msg.body )
		except Exception:
			log.warning("Failed to deserialize packet")
			return

		if isinstance( packet, FetchInventoryPacket ):
			log.info( f"Received inventory fetch request from { packet.sender_id }..." )
			await self.handle_fetch( packet )
		elif isinstance( packet, BuyItemPacket ):
			log.info( f"Received buy request from { packet.sender_id } for item { packet.item_id }..." )
			await self.handle_buy( packet )
		elif isinstance( packet, ResponseDronePacket ):
			log.info( f"Received response drone from { packet.sender_id }..." )
			await self.handle_response_drone( packet )
		elif isinstance( packet, RequestDroneLendPacket ):
			log.info( f"Received drone lend request from { packet.sender_id } for { packet.requester_company_id }..." )
			await self.handle_drone_lend_request( packet )
		elif isinstance( packet, ConfirmDroneLendPacket ):
			log.info( f"Received drone lend confirmation from { packet.sender_id }..." )
			await self.handle_drone_lend_confirm( packet )
		elif isinstance( packet, DroneLentPacket ):
			log.info( f"Received lent drone notification from { packet.sender_id }..." )
			await self.handle_drone_lent( packet )
		elif isinstance( packet, DroneReturnedPacket ):
			log.info( f"Received drone returned notification from { packet.sender_id }..." )
			await self.handle_drone_returned( packet )
		elif isinstance(packet, DroneStatusPacket):
			log.info(f"Received status update from drone {packet.sender_id}...")
			await self.handle_drone_release(packet)
		elif isinstance(packet, RefuseJobPacket):
			log.warning(f"Drone {packet.sender_id} refused job: {packet.reason}")
			await self.handle_job_refusal(packet)
		else:
			log.warning( f"Received unexpected packet: { packet }..." )

	async def handle_fetch( self, packet: FetchInventoryPacket ):
		log = self.log

		inventory_packet = InventoryPacket( self.agent.jid.node, self.agent.inventory )
		msg = new_message( inventory_packet, packet.sender_id )
		await self.send( msg )
		log.info( f"Sent inventory to { packet.sender_id }...")

	async def handle_buy( self, packet: BuyItemPacket ):
		log = self.log

		inventory = self.agent.inventory
		item_id = packet.item_id
		sender_id = packet.sender_id
		if item_id in inventory:
			item = inventory[item_id]
			log.info( f"Item { item_id } sold to { sender_id }..." )

			log.info( "Creating package to send..." )
			package = Package( packet.order_id, sender_id, packet.client_location,  item )

			log.info( "Putting in queue, to be eventually sent..." )
			await self.agent.packages_to_send.put( package )
		else:
			log.info( f"Item { item_id } doesn't exist in this company..." )

	async def handle_response_drone(self, packet: ResponseDronePacket):
		log = self.log

		if packet.drone:
			log.info(f"Renting new drone: {packet.drone.id} costing {packet.cost}...")

			packet.drone.available = True

			self.agent.rented_drones.append(packet.drone)
			self.agent.budget -= packet.cost
		else:
			log.info("No available drone...")

	async def handle_drone_lend_request(self, packet: RequestDroneLendPacket):
		"""Handle request from central to lend a drone to another company."""
		log = self.log

		# Don't lend to ourselves
		if packet.requester_company_id.upper() == self.agent.jid.node.upper():
			log.info("Ignoring lend request for ourselves")
			return

		# Find an available drone that can handle the package
		available_drone = None
		for drone in self.agent.rented_drones:
			if drone.available and drone.capacity_kg >= packet.package_weight:
				available_drone = drone
				break

		if available_drone:
			# Calculate lending cost based on distance
			dist_to_pickup = available_drone.current_position.distance_to(packet.pickup_location)
			dist_delivery = packet.pickup_location.distance_to(packet.client_location)
			total_distance = dist_to_pickup + dist_delivery
			lending_cost = _BASE_LENDING_FEE + (total_distance * _LENDING_FEE_PER_KM)

			log.info(f"Offering drone {available_drone.id} for lending (cost: {lending_cost:.2f})")
			
			response = ResponseDroneLendPacket(
				sender_id=self.agent.jid.node,
				request_id=packet.request_id,
				has_drone=True,
				drone=available_drone,
				lending_cost=lending_cost
			)
		else:
			log.info("No available drone to lend")
			response = ResponseDroneLendPacket(
				sender_id=self.agent.jid.node,
				request_id=packet.request_id,
				has_drone=False,
				drone=None,
				lending_cost=0.0
			)

		msg = new_message(response, packet.sender_id)
		await self.send(msg)
		log.info(f"Sent lend response to {packet.sender_id}")

	async def handle_drone_lend_confirm(self, packet: ConfirmDroneLendPacket):
		"""Handle confirmation from central about drone lending."""
		log = self.log

		if packet.accepted:
			# Find and mark the drone as unavailable (being lent)
			for drone in self.agent.rented_drones:
				if drone.id == packet.drone_id:
					drone.available = False
					log.info(f"Drone {drone.id} is now being lent to {packet.requester_company_id}")
					
					# Track that we lent this drone
					if not hasattr(self.agent, 'lent_drones'):
						self.agent.lent_drones = {}
					self.agent.lent_drones[drone.id] = {
						'borrower': packet.requester_company_id,
						'request_id': packet.request_id
					}
					break
		else:
			log.info(f"Drone {packet.drone_id} lending was not accepted")

	async def handle_drone_lent(self, packet: DroneLentPacket):
		"""Handle notification that we received a lent drone from another company."""
		log = self.log

		log.info(f"Received lent drone {packet.drone.id} from {packet.lender_company_id} (cost: {packet.lending_cost:.2f})")
		
		# Add the lent drone to our available drones temporarily
		packet.drone.available = True
		self.agent.rented_drones.append(packet.drone)
		self.agent.budget -= packet.lending_cost

		# Track this as a borrowed drone so we can return it later
		self.borrowed_drones[packet.drone.id] = {
			'lender': packet.lender_company_id,
			'drone': packet.drone,
			'request_id': packet.request_id
		}

		log.info(f"Drone {packet.drone.id} added to available drones (borrowed from {packet.lender_company_id})")

	async def handle_drone_returned(self, packet: DroneReturnedPacket):
		"""Handle notification that our lent drone has been returned."""
		log = self.log

		log.info(f"Drone {packet.drone_id} has been returned")

		# Find the drone and mark it as available again
		for drone in self.agent.rented_drones:
			if drone.id == packet.drone_id:
				drone.available = True
				log.info(f"Drone {drone.id} is now available again")
				break

		# Remove from lent drones tracking
		if hasattr(self.agent, 'lent_drones') and packet.drone_id in self.agent.lent_drones:
			del self.agent.lent_drones[packet.drone_id]

	async def return_borrowed_drone(self, drone_id: str):
		"""Return a borrowed drone to its lender after delivery is complete."""
		log = self.log

		if drone_id not in self.borrowed_drones:
			log.warning(f"Drone {drone_id} not found in borrowed drones")
			return

		borrowed_info = self.borrowed_drones[drone_id]
		lender_id = borrowed_info['lender']

		log.info(f"Returning drone {drone_id} to {lender_id}")

		# Remove drone from our list
		self.agent.rented_drones = [d for d in self.agent.rented_drones if d.id != drone_id]

		# Send return notification to central
		return_packet = ReturnDronePacket(
			sender_id=self.agent.jid.node,
			drone_id=drone_id,
			lender_company_id=lender_id
		)
		msg = new_message(return_packet, CENTRAL_ID)
		await self.send(msg)

		# Clean up tracking
		del self.borrowed_drones[drone_id]
		log.info(f"Drone {drone_id} returned to {lender_id}")

	async def handle_drone_release(self, packet: DroneStatusPacket):
		log = self.log
		updated_drone = packet.drone_info
		drone_id = updated_drone.id

		if drone_id in self.borrowed_drones:
			log.info(f"Borrowed drone {drone_id} finished delivery: returning to lender...")
			await self.return_borrowed_drone(drone_id)
			return

		is_rented = any(d.id == drone_id for d in self.agent.rented_drones)

		if is_rented:
			self.agent.rented_drones = [d for d in self.agent.rented_drones if d.id != drone_id]
			log.info(f"Drone {drone_id} finished delivery!")
		else:
			log.debug(f"Received update from drone {drone_id} not currently rented: ignoring....")

	async def handle_job_refusal(self, packet: RefuseJobPacket):
		log = self.log
		drone_id = packet.sender_id

		log.warning(f"Drone {drone_id} refused job: {packet.reason}")

		if drone_id in self.borrowed_drones:
			await self.return_borrowed_drone(drone_id)

		self.agent.rented_drones = [d for d in self.agent.rented_drones if d.id != drone_id]

		log.info(f"Re-queueing package {packet.package.order_id}...")
		await self.agent.packages_to_send.put(packet.package)