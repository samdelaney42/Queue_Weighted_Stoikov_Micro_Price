class Event:

	def __init__(self, data):
		self.time = data[0]
		self.type = data[1]
		self.order_id = data[2]
		self.shares = data[3]
		self.price = data[4]
		self.direction = data[5]