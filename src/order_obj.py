import copy
import pandas as pd

class Order:
	"""
	Represents an order in the limit order book.

	Attributes:
		entryTime (object): The time when the order was entered.
		type (object): The type of the order.
		id (object): The unique identifier of the order.
		shares (object): The number of shares in the order.
		price (object): The price of the order.
		direction (object): The direction of the order.
		next (Order): Reference to the next order in the linked list.
		prev (Order): Reference to the previous order in the linked list.
		life (list): Each event following submission recorded here
	"""
	def __init__(self, data):
		"""
		Initializes a new instance of Order.

		Args:
			data (list): A list containing order data.
		"""
		self.entryTime = copy.copy(data.time)
		self.id = copy.copy(data.order_id)
		self.shares = copy.copy(data.shares)
		self.price = copy.copy(data.price)
		self.direction = copy.copy(data.direction)
		self.next = None
		self.prev = None
		self.life = []
		self.start_position = None

	def getOrder(self):
		"""
		Retrieves order details.

		Returns:
			list: A list containing order ID, price, and shares.
		"""
		return [self.id, self.price, self.shares]
	
	def getLife(self):
		"""
		Takes order life array and converts it to a DF

		Returns:
			DataFrame: adding price and cumulative decrease of shares over life of order
		"""
		life_cycle = pd.DataFrame(self.life, columns=['Time', 'Shares', 'Type', 'Price'])
		starting_reduction = [0]
		cumulative_reduction = [int(sum(life_cycle.iloc[1:x+1]['Shares'])) for x in range(1,len(life_cycle))]
		total_reduction = starting_reduction + cumulative_reduction
		shares_reduction = [self.life[0][1] - x for x in total_reduction]
		life_cycle['Share_Life'] = shares_reduction
		return life_cycle

	def getDirection(self):
		"""
		Retrieves the direction of the order.

		Returns:
			str: The direction of the order ('buy' or 'sell').
		"""
		if self.direction == 1:
			return 'buy'
		else:
			return 'sell'