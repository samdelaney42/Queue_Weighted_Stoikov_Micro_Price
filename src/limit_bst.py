import level_linked_list as ll
from order_obj import Order
import copy
import log

class BinarySearchTree:
	"""
	Represents a binary search tree used in a limit order book.

	Attributes:
		limit_price (float): The price of the order.
		num_orders (int): Number of orders at this limit.
		total_volume (int): Total volume at this limit.
		left_child (BinarySearchTree): Left child node in the binary tree.
		right_child (BinarySearchTree): Right child node in the binary tree.
		parent (BinarySearchTree): Parent node in the binary tree.
		order_queue (LinkedList): Linked list to store orders at this limit.
	"""
	
	def __init__(self, order_price=None):
		"""
		Initializes a new instance of BinarySearchTree.

		Args:
			order_price (float): The price of the order.
		"""
		self.logger = log.get_logger('Limit BST')

		self.limit_price = order_price
		self.num_orders = 0
		self.total_volume = 0
		self.left_child = None
		self.right_child = None
		self.parent = None
		self.order_queue = None

### Event handlers

	def handleNewOrder(self, new_order):
		"""
		Handles a new order submission.

		Args:
			new_order (Order): The order object to be added.
		"""
		if self.checkLimit(new_order.price):
			limit_to_add_order = self.getLimit(new_order.price)
			limit_to_add_order.addOrderHelper(new_order)
		else:
			self.addLimit(new_order)

	def handleCancellation(self, order_to_cancel, shares_to_subtract_from_limit_total):
		"""
		Handles cancellation of an existing order.

		Args:
			order_to_cancel (Order): The order object to be canceled.
			shares_to_subtract_from_limit_total (int): Number of shares to cancel.
		"""
		if self.checkLimit(order_to_cancel.price):
			limit_to_cancel_order = self.getLimit(order_to_cancel.price)
			limit_to_cancel_order.cancelOrderHelper(shares_to_subtract_from_limit_total)
		else:
			self.logger.info("Limit {} does not exist".format(order_to_cancel.price))

	def handleDeletion(self, order_to_delete):
		"""
		Handles deletion of an existing order.

		Args:
			order_to_delete (Order): The order object to be deleted.
		"""
		if self.checkLimit(order_to_delete.price):
			limit_to_delete_order = self.getLimit(order_to_delete.price)
			limit_to_delete_order.deleteOrderHelper(order_to_delete)
			if (limit_to_delete_order.total_volume == 0) & (limit_to_delete_order.num_orders == 0):
				self.deleteLimit(limit_to_delete_order.limit_price)
				self.logger.info("No orders at limit {}: limit deleted from book".format(limit_to_delete_order.limit_price))
		else:
			self.logger.info("Limit {} does not exist".format(order_to_delete.price))

	def handleVisibleExecution(self, order_to_execute, shares_executed):
		"""
		Handles execution of an order.

		Args:
			order_to_execute (Order): The order object to be executed.
			shares_executed (int): Number of shares to execute.
		"""
		if self.checkLimit(order_to_execute.price):
			limit_to_execute_order = self.getLimit(order_to_execute.price)
			limit_to_execute_order.executeOrderHelper(shares_executed)
		else:
			self.logger.info("Limit {} does not exist".format(order_to_execute.price))

### Helper Functions

	def addOrderHelper(self, new_order):
		"""
		Helper function to add an order.

		Args:
			new_order (Order): The order object to be added.
		"""
		self.addOrderToQueue(new_order)
		self.increaseVolumeAtLimit(new_order.shares)
		self.increaseNumOrdersAtLimit()
		new_order.start_position = copy.copy(self.num_orders)

	def cancelOrderHelper(self, shares_to_cancel):
		"""
		Helper function to cancel an order.

		Args:
			shares_to_cancel (int): Number of shares to cancel.
		"""
		self.reduceVolumeAtLimit(shares_to_cancel)

	def deleteOrderHelper(self, order_to_delete):
		"""
		Helper function to delete an order.

		Args:
			order_to_delete (Order): The order object to be deleted.
		"""
		self.deleteOrderFromQueue(order_to_delete)
		self.reduceVolumeAtLimit(order_to_delete.shares)
		self.reduceNumOrdersAtLimit()

	def executeOrderHelper(self, shares_to_execute):
		"""
		Helper function to execute an order.

		Args:
			shares_to_execute (int): Number of shares to execute.
		"""
		self.reduceVolumeAtLimit(shares_to_execute)

### Attribute change functions

	def addLimit(self, new_order):
		"""
		Adds a new limit to the tree and sets the given order at the head of the queue.

		Args:
			new_order (Order): The order object to be added.
		"""
		if new_order.price < self.limit_price:
			if self.left_child is not None:
				self.left_child.addLimit(new_order)
			else:
				self.logger.info("Creating new limit")
				self.left_child = BinarySearchTree(new_order.price)
				self.left_child.addOrderHelper(new_order)
				self.left_child.parent = self
				return
		if new_order.price > self.limit_price:
			if self.right_child is not None:
				self.right_child.addLimit(new_order)
			else:
				self.logger.info("Creating new limit")
				self.right_child = BinarySearchTree(new_order.price)
				self.right_child.addOrderHelper(new_order)
				self.right_child.parent = self
				return
			
	def deleteLimit(self, limit):
		"""
		Deletes a limit from the tree.

		Args:
			limit (float): The price of the limit to be deleted.
		"""
		# Find the node in the left subtree if the limit is less than root value
		if limit < self.limit_price:
			self.left_child = self.left_child.deleteLimit(limit)
		# Find the node in the right subtree if the limit is greater than root value
		elif limit > self.limit_price:
			self.right_child = self.right_child.deleteLimit(limit)
		# Delete the node if root.value == limit
		else: 
			# Case 1: Node has no child or only one child
			if not self.right_child:
				return self.left_child
			elif not self.left_child:
				return self.right_child
			# Case 2: Node has two children
			# Find the in-order predecessor (maximum value in the left subtree)
			temp_val = self.right_child
			while temp_val.left_child:
				temp_val = temp_val.left_child
			# Update the current node val with the successor val
			self.limit_price = temp_val.limit_price
			self.num_orders = temp_val.num_orders
			self.total_volume = temp_val.total_volume
			self.order_queue = temp_val.order_queue
			# Delete the in-order predecessor from the left subtree
			self.right_child = self.right_child.deleteLimit(temp_val.limit_price)
		return self

	def addOrderToQueue(self, new_order):
		"""
		Adds an order to the queue.

		Args:
			new_order (Order): The order object to be added.
		"""
		if self.order_queue == None:
			self.order_queue = ll.LinkedList()
			self.order_queue = self.order_queue.addOrder(new_order)
		else:
			self.order_queue = self.order_queue.addOrder(new_order)
	
	def deleteOrderFromQueue(self, order_to_delete):
		"""
		Deletes an order from the queue.

		Args:
			order_to_delete (Order): The order object to be deleted.
		"""
		self.order_queue.deleteOrder(order_to_delete)
		return
	
	def reduceVolumeAtLimit(self, shares):
		"""
		Reduces the total volume at the limit.

		Args:
			shares (int): Number of shares to reduce.
		"""
		self.total_volume = self.total_volume - shares
		self.logger.info("Total vol at {} has been reduced by {}".format(self.limit_price, shares))
	
	def increaseVolumeAtLimit(self, shares):
		"""
		Increases the total volume at the limit.

		Args:
			shares (int): Number of shares to increase.
		"""
		self.total_volume = self.total_volume + shares
		self.logger.info("Total vol at {} has been increased by {}".format(self.limit_price, shares))

	def reduceNumOrdersAtLimit(self):
		"""Reduces the number of orders at the limit by 1."""
		self.num_orders = self.num_orders - 1
		self.logger.info("Num orders at {} has been reduced by 1".format(self.limit_price))

	def increaseNumOrdersAtLimit(self):
		"""Increases the number of orders at the limit by 1."""
		self.num_orders = self.num_orders + 1
		self.logger.info("Num orders at {} has been increased by 1".format(self.limit_price))

### Misc Functions

	def checkLimit(self, limit):
		"""
		Checks if the given limit exists in the tree.

		Args:
			limit (float): The price of the limit to be checked.

		Returns:
			bool: True if the limit exists, False otherwise.
		"""
		if limit == self.limit_price:
			self.logger.info('limit {} exists'.format(limit))
			return True
		if (limit < self.limit_price) & (self.left_child is not None):
			return self.left_child.checkLimit(limit)
		elif (limit > self.limit_price) & (self.right_child is not None):
			return self.right_child.checkLimit(limit)
		else:
			self.logger.info('limit {} does not exist'.format(limit))
			return False
		
	def getLimit(self, limit):
		"""
		Gets the limit object for the given limit price.

		Args:
			limit (float): The price of the limit to be retrieved.

		Returns:
			BinarySearchTree: The limit object if found, None otherwise.
		"""
		if limit == self.limit_price:
			return self
		if (limit < self.limit_price) & (self.left_child is not None):
			return self.left_child.getLimit(limit)
		elif (limit > self.limit_price) & (self.right_child is not None):
			return self.right_child.getLimit(limit)
		else:
			return False

	def inOrderTraversal(self):
		"""
		Performs in-order traversal of the binary tree.

		Returns:
			list: A list containing nodes in in-order traversal.
		"""
		elements = []
		if self.left_child:
			elements += self.left_child.inOrderTraversal()
		if self.num_orders != 0:
			elements.append(self)
		if self.right_child:
			elements += self.right_child.inOrderTraversal()
		return elements
