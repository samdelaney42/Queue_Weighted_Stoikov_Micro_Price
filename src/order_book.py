import limit_bst as tree
from  order_obj import Order
import numpy as np
import pandas as pd
from datetime import datetime
import log

class Book:
	"""
	Represents a limit order book.

	Attributes:
		buy (BinarySearchTree): A binary search tree representing buy orders.
		sell (BinarySearchTree): A binary search tree representing sell orders.
		best_bid (Order): The best bid order in the book.
		best_offer (Order): The best offer order in the book.
		orders (dict): All orders keyed by their IDs.
		visible_executions [list]: All visible executions 
		event_times [list]: Event times used later to index the formatted orderbook
		book_snapshot [list]: in order traversal of the book after each event
		hidden_executions [list]: All hidden executions
	"""
	
	def __init__(self):
		"""
		Initializes a new instance of Book.

		Sets up logging configuration and initializes necessary attributes.
		"""
		self.logger = log.get_logger('Order Book')

		# main variables
		self.buy = tree.BinarySearchTree(-9999999999)
		self.sell = tree.BinarySearchTree(9999999999)
		self.best_bid = None
		self.best_offer = None
		self.orders = {}

		# Storage variables
		self.event_time = None
		self.book_snapshot = []
		self.event_times = []
		self.visible_executions = []
		self.hidden_executions = []
		self.submissions = []
		self.cancelations = []
		self.deletions = []
		self.queues = []

	def  handleEvent(self, event, i):
		"""
		Handles incoming events and takes appropriate actions.

		Args:
			event (Event): The event object to be processed.
			i (int): Identifier for the event.

		Raises:
			ValueError: If the event type is not recognized.
		"""
		self.event_time = datetime.fromtimestamp(event.time).time()
		
		if event.type == 1:
			self.logger.info('{} New Order Submission'.format(i))
			self.newLimitOrderSubmission(event)
		elif event.type == 2:
			self.logger.info('{} Order Cancelation'.format(i))
			self.cancelationOfExistingLimitOrder(event)
		elif event.type == 3:
			self.logger.info('{} Order Deleteion'.format(i))
			self.deletionOfExistingLimitOrder(event)
		elif event.type == 4:
			self.logger.info('{} Visible Order Execution'.format(i))
			self.orderExecution(event)
		elif event.type == 5:
			self.logger.info('{} Hidden Order Execution'.format(i))
			self.hiddentExecution(event)
		
		# aggregate info for use later 
		self.event_times.append(self.event_time)
		self.book_snapshot.append([self.getAllLevels(), self.event_time])
		self.queues.append([self.getL5orderqueues(), self.event_time])
		self.updateNbbo()


	def newLimitOrderSubmission(self, event):
		"""
		Processes a new limit order submission event.

		Args:
			event (Event): The event object representing the new order submission.
		"""
		# turn event into order object 
		new_order = Order(event)
		# created first entry in life array:
		new_order.life.append([self.event_time, event.shares, event.type, event.price]) 
		# add to order dict keyd on id
		self.orders[int(new_order.id)] = new_order
		self.logger.info("Adding ID {} at {}, vol {}, in {} tree".format(new_order.id, new_order.price, new_order.shares, new_order.getDirection()))
		# check if buy or sell then add to approporiate tree
		if event.direction == 1:
			self.buy.handleNewOrder(new_order)
		elif event.direction == -1:
			self.sell.handleNewOrder(new_order)
		# add to new submissions
		self.submissions.append([self.event_time, new_order.id, new_order.price, new_order.shares, new_order.direction])

	def cancelationOfExistingLimitOrder(self, event):
		"""
		Cancels an existing limit order.

		Args:
			event (Event): The event object representing the order cancellation.
		"""
		# get the ID of the order to partially cancel and get the order from the dict
		order_to_cancel = self.orders.get(event.order_id)
		shares_to_subtract_from_limit_total = event.shares
		# check if order exists
		if order_to_cancel is not None:
			# update order life 
			order_to_cancel.life.append([self.event_time, event.shares, event.type, event.price])
			if order_to_cancel.shares != 0:
				self.logger.info("Canceling {} shares for ID {} at {} in {} tree".format(shares_to_subtract_from_limit_total, order_to_cancel.id, order_to_cancel.price, order_to_cancel.getDirection()))
				if order_to_cancel.direction == 1:
					self.buy.handleCancellation(order_to_cancel, shares_to_subtract_from_limit_total)
				elif order_to_cancel.direction == -1:
					self.sell.handleCancellation(order_to_cancel, shares_to_subtract_from_limit_total)
				# reduce the number of shares at this order by those in the event 
				order_to_cancel.shares = order_to_cancel.shares - shares_to_subtract_from_limit_total
				# update the order in the dict
				self.orders[order_to_cancel.id] = order_to_cancel
				# edit the number of total shares at that level in the book
				self.logger.info("ID {} has {} shares remaining".format(order_to_cancel.id, order_to_cancel.shares))
			# keep track of cancellations
			self.cancelations.append([self.event_time, order_to_cancel.id, order_to_cancel.price, shares_to_subtract_from_limit_total, order_to_cancel.direction])
		else:
			self.logger.info("ID {} does not exist".format(event.order_id))

	def deletionOfExistingLimitOrder(self, event):
		"""
		Deletes an existing limit order.

		Args:
			event (Event): The event object representing the order deletion.
		"""
		# get the ID of the order to delete and get the order from the dict
		order_to_delete = self.orders.get(event.order_id)
		# check if order exists
		if order_to_delete is not None:
			# update order life 
			# we call deletion if we execute an entire order, so we handle for orders with 0 shares
			if order_to_delete.shares != 0:
				order_to_delete.life.append([self.event_time, event.shares, event.type, event.price])
			# pass order to book to delete from relevant queue
			self.logger.info("Deleting ID {} at {} from queue in {} tree".format(order_to_delete.id, order_to_delete.price, order_to_delete.getDirection()))
			if order_to_delete.direction == 1:
				self.buy.handleDeletion(order_to_delete)
			elif order_to_delete.direction == -1:
				self.sell.handleDeletion(order_to_delete)
			# keep track of deletions
			self.deletions.append([self.event_time, order_to_delete.id, order_to_delete.price, order_to_delete.shares, order_to_delete.direction])
		else:
			self.logger.info("ID {} does not exist".format(event.order_id))

	def orderExecution(self, event):
		"""
		Executes an order.

		Args:
			event (Event): The event object representing the order execution.
		"""
		# get id of order to execute and num shares to execute
		order_to_execute = self.orders.get(event.order_id)
		shares_traded = event.shares
		# check if order exists
		if order_to_execute is not None:
			# update order life
			order_to_execute.life.append([self.event_time, event.shares, event.type, event.price])
			# determine the direction we are executing and send to respective buy or sell tree
			self.logger.info("Executing {} shares for ID {} at {} in {} tree".format(shares_traded, order_to_execute.id, order_to_execute.price, order_to_execute.getDirection()))
			if order_to_execute.direction == 1:
				self.buy.handleVisibleExecution(order_to_execute, shares_traded)
			elif order_to_execute.direction == -1:
				self.sell.handleVisibleExecution(order_to_execute, shares_traded)
			# get number of shares executed and remove it from the amount we we have saved in the executable order object
			# reduce shares at ID
			if order_to_execute.shares > 0:
				order_to_execute.shares = order_to_execute.shares - shares_traded
			else:
				self.logger.info("ID {} has 0 shares remaining".format(order_to_execute.id))
			# update the order in dict with new vlaues
			self.orders[order_to_execute.id] = order_to_execute
			self.logger.info("ID {} has {} shares remaining".format(order_to_execute.id, order_to_execute.shares))
			# Add to trades list
			self.visible_executions.append([self.event_time, order_to_execute.id, order_to_execute.price, shares_traded, order_to_execute.direction])
			# if there are 0 shares for this ID then remove the order from the queue
			if order_to_execute.shares == 0:
				self.deletionOfExistingLimitOrder(event)
		else:
			self.logger.info("ID {} does not exist".format(event.order_id))

	def hiddentExecution(self, event):
		self.hidden_executions.append([self.event_time, event.price, event.shares, event.direction])
		
	def getNbbo(self):
		"""
		Retrieves the National Best Bid and Offer (NBBO).

		Returns:
			tuple: A tuple containing the best offer price and best bid price.
		"""
		return self.best_offer, self.best_bid
	
	def updateNbbo(self):
		"""
		Updates the BBO based on the given order.

		Args:
			order (Order): The order object used to update NBBO.
		"""
		if len(self.buy.inOrderTraversal()) == 0:
			self.best_bid = None
		else:
			self.best_bid = self.buy.inOrderTraversal()[-1].limit_price
		if len(self.sell.inOrderTraversal()) == 0:
			self.best_offer = None
		else:
			self.best_offer = self.sell.inOrderTraversal()[0].limit_price
		
	def getXLevels(self, x):
		"""
		Retrieves the top X levels from buy and sell trees.

		Args:
			x (int): The number of levels to retrieve.

		Returns:
			list: A list containing top X buy levels and top X sell levels.
		"""
		b = self.buy.inOrderTraversal()[-x:]
		o = self.sell.inOrderTraversal()[:x]

		b = [[i.limit_price, i.total_volume, i.num_orders] for i in b]
		o = [[i.limit_price, i.total_volume, i.num_orders] for i in o]
		return [b, o]
	
	def getXLevelspricesonly(self, x):
		"""
		Retrieves the top X levels from buy and sell trees.

		Args:
			x (int): The number of levels to retrieve.

		Returns:
			list: A list containing top X buy levels and top X sell levels.
		"""
		b = self.buy.inOrderTraversal()[-x:]
		o = self.sell.inOrderTraversal()[:x]

		b = [i.limit_price for i in b]
		o = [i.limit_price for i in o]
		return [b, o]
	
	def getAllLevels(self):
		"""
		Retrieves all levels from buy and sell trees.

		Returns:
			list: A list containing all buy levels and all sell levels.
		"""
		b = self.buy.inOrderTraversal()
		o = self.sell.inOrderTraversal()

		b = [[i.limit_price, i.total_volume, i.num_orders] for i in b]
		o = [[i.limit_price, i.total_volume, i.num_orders] for i in o]
		return [b, o]
	
	def getL1orderqueue(self):
		"""
		Gets all the orders in the top of book order queue

		Returns:
			List: Bid L1 order queue
			List: Ask L1 order queue
		"""
		ask, bid = self.getNbbo()

		if ask == None:
			ask_queue = None
		else:
			ask_queue = self.getOrdersatlimit(ask)	
		if bid == None:
			bid_queue = None
		else:
			bid_queue = self.getOrdersatlimit(bid)
	
		return [bid_queue, ask_queue]
	
	def getL5orderqueues(self):
		"""
		Gets all the order queues up to 5 levels in the book

		Returns:
			List: Bid L5 order queue
			List: Ask L5 order queue
		"""
		book_levels = self.getXLevelspricesonly(5)
		bids = book_levels[0]
		asks = book_levels[1]

		ask_queues = []
		bid_queues = []

		for i in asks:
			if i == None:
				ask_queues.append(None)
			else:
				ask_queues.append(self.getOrdersatlimit(i))	

		for j in bids:
			if j == None:
				bid_queues.append(None)
			else:
				bid_queues.append(self.getOrdersatlimit(j))
	
		return [bid_queues, ask_queues]
	
	def getOrdersatlimit(self, limit):
		"""
		Gets all the orders in the queue from a specified level

		Returns:
			list: A list containing all the orders at a given level, index 0 being first in queue
		"""
		if self.buy.checkLimit(limit) == True:
			limit_to_get_queue = self.buy.getLimit(limit)
		elif self.sell.checkLimit(limit) == True:
			limit_to_get_queue = self.sell.getLimit(limit)
		else:
			self.logger.info("Limit {} does not exist".format(limit))
			return
		
		return limit_to_get_queue.order_queue.getOrderqueue()
	
	def getVisibleExecutions(self, split):
		"""
		Pull all executions recorded

		Returns:
			DataFrame: DF of buy and sell executions indexed by time
			DataFrame, DataFrame: Split bid and ask executions
		"""
		split = split
		visible_executions = pd.DataFrame(self.visible_executions, columns=['Time', 'ID', 'Price', 'Shares', 'Direction'])
		
		if split == True:
			visible_sells = visible_executions[visible_executions['Direction']==-1]
			visible_buys = visible_executions[visible_executions['Direction']==1]
			return visible_buys, visible_sells
		else:
			return visible_executions
		
	def getHiddenExecutions(self, split):
		"""
		Pull all executions recorded

		Returns:
			DataFrame: DF of buy and sell executions indexed by time
			DataFrame, DataFrame: Split bid and ask executions
		"""
		split = split
		hidden_executions = pd.DataFrame(self.hidden_executions, columns=['Time', 'Price', 'Shares', 'Direction'])
		
		if split == True:
			hidden_sells = hidden_executions[hidden_executions['Direction']==-1]
			hidden_buys = hidden_executions[hidden_executions['Direction']==1]
			return hidden_buys, hidden_sells
		else:
			return hidden_executions
		
	def getAllExecutions(self):
		"""
		Create a single DF containing both hidden and visible executions

		Returns:
			DataFrame: Containing merged version of all exectuions
		"""
		visible = self.getVisibleExecutions(split=False)
		hidden = self.getHiddenExecutions(split=False)

		visible['Type'] = ["Visible" for x in range(len(visible))]
		hidden['Type'] = ["Hidden" for x in range(len(hidden))]
		
		merged_executions = pd.concat([hidden, visible]).sort_values(by='Time')
		return merged_executions
	
	def getSubmissions(self):
		submissions = pd.DataFrame(self.submissions, columns=['Time', 'ID', 'Price', 'Shares', 'Direction'])
		return submissions

	def getDeletions(self):
		deletions = pd.DataFrame(self.deletions, columns=['Time', 'ID', 'Price', 'Shares', 'Direction'])
		return deletions

	def getCancellations(self):
		cancelations = pd.DataFrame(self.cancelations, columns=['Time', 'ID', 'Price', 'Shares', 'Direction'])
		return cancelations
	

###############################
# Methods to format the output of our orderbook
###############################


	def formatBook(self, start_from, levels):
		"""
		Helper method to take the book snapshot list and format it to match the LOBSTER output

		Returns:
			DataFrame: DF in the same format as Lobster
		"""
		levels = levels
		start_from = start_from
		book_stripped, self.time = self.stripTime(self.book_snapshot)
		symetric_book = self.symetricBook(book_stripped, self.time)
		book = self.outputBook(symetric_book, start_from, levels)
		return book
	
	def  stripTime(self, book_snapshot):
		"""
		Take the orderbook snapshot list and seperate the order info and time stamps

		Returns:
			[List]: nested list of only price, volume, and orders after each event
			[List]: Time stamps associated with each event
		"""
		book = []
		time = []
		for i in range(len(book_snapshot)):
			book.append(book_snapshot[i][0])
			time.append(book_snapshot[i][1])
		return book, time

	def symetricBook(self, book_stripped, time_list):
		"""
		Takes the orderbook only data and formats it to keep only 5 levels at any time
		If, for example, there are only 2 levels with orders, the reamining 3 levels 
		are filled with [0, 0, 0]

		Returns:
			[List]: nested list of 5 levels on each side of order book
		"""

		symetric_book = []
		count = 0
		for x in book_stripped:
			bid = x[0]
			ask = x[1]

			if len(bid) <= 5:
				bid = bid[::-1]
				for y in range((5-len(bid))):
					bid.append([0, 0, 0])
			elif len(bid) > 5:
				bid = bid[::-1]
				bid = bid[:5]
			
			if len(ask) <= 5:
				for z in range((5-len(ask))):
					ask.append([0, 0, 0])
			elif len(ask) > 5:
				ask = ask[:5]
			time = time_list[count]

			symetric_book.append([time, ask, bid])
			count += 1

		return symetric_book
	
	def outputBook(self, symetric_book, start_from, levels):
		"""
		Takes symetrical nested list and coverts to DF correctly labeled

		Returns:
			DataFrame: LOBSTER formatted df
		"""
		
		colnames = ['Ask_1','Ask_1_Vol','Ask_1_Ord',
			  		'Bid_1','Bid_1_Vol','Bid_1_Ord',
					'Ask_2','Ask_2_Vol','Ask_2_Ord',
					'Bid_2','Bid_2_Vol','Bid_2_Ord',
					'Ask_3','Ask_3_Vol','Ask_3_Ord',
					'Bid_3','Bid_3_Vol','Bid_3_Ord',
					'Ask_4','Ask_4_Vol','Ask_4_Ord',
					'Bid_4','Bid_4_Vol','Bid_4_Ord',
					'Ask_5','Ask_5_Vol','Ask_5_Ord',
					'Bid_5','Bid_5_Vol','Bid_5_Ord']
		df_rows = []
		idx = []
		for snap_shot in symetric_book:
			idx.append(snap_shot[0])
			ask = snap_shot[1]
			bid = snap_shot[2]
			df_row = []
			for level in range(len(ask)):
				df_row.append(ask[level])
				df_row.append(bid[level])
			a = np.array(df_row)
			a = a.flatten()
			a = list(a)
			df_rows.append(a)

		df_rows = df_rows[start_from:]
		time = idx
		time = time[start_from:]

		cols_to_drop = [x for x in range((6*levels), 30)]

		my_output = pd.DataFrame(df_rows, columns = colnames)
		my_output['Time'] = time
		my_output = my_output.drop(my_output.columns[cols_to_drop],axis=1)
		
		return my_output
	
	def splitBidsAsks(self, formatted_book):
		"""
		This method splits our formatted book into bids and asks

		Returns:
			DataFrame, DataFrame: Bids and Asks 
		"""

		levels = int(len(formatted_book.columns)/6)

		asks_to_drop = []
		bids_to_drop = []
		for i in range(levels):
			asks_to_drop += ['Ask_{}'.format(i+1),'Ask_{}_Vol'.format(i+1),'Ask_{}_Ord'.format(i+1)]
			bids_to_drop += ['Bid_{}'.format(i+1),'Bid_{}_Vol'.format(i+1),'Bid_{}_Ord'.format(i+1)]

		asks = formatted_book
		bids = formatted_book

		asks = asks.drop(columns=bids_to_drop)
		bids = bids.drop(columns=asks_to_drop)

		return bids, asks
	
	def getMid(self, bids, asks):
		"""
		Calculate the mid of the best bid and ask

		Return:
			DataFrame: includes only mid price and time
		"""
		mid = (bids.Bid_1 + asks.Ask_1)/2
		mid = pd.DataFrame(mid, columns=['Price'])
		mid['Time'] = bids.Time
		return mid
	
	def getQueues(self, start_from, level):
		"""
		Get the queue lengths and orders in each queue for either 1 or 5 levels

		Returns:
			DataFrame: Bid queues and their lengths 
			DataFrame: Ask queues and their lengths 
		"""

		bid_queues, ask_queues = self.formatQueues()
		bid_queues['Time'] = self.event_times
		ask_queues['Time'] = self.event_times

		bid_queue_lens = self.queueFromatHelper(bid_queues['Bid_Q_lens'])
		ask_queue_lens = self.queueFromatHelper(ask_queues['Ask_Q_lens'])

		bid_queues = pd.concat([bid_queues, bid_queue_lens], axis=1).drop(columns=['Bid_Q_lens'])
		ask_queues = pd.concat([ask_queues, ask_queue_lens], axis=1).drop(columns=['Ask_Q_lens'])

		bid_queues = bid_queues[start_from:]
		ask_queues = ask_queues[start_from:]

		if level == 1:
			bid_queues = bid_queues.drop(columns=['Bid_5', 'Bid_4', 'Bid_3', 'Bid_2', 'l5', 'l4', 'l3', 'l2'])
			ask_queues = ask_queues.drop(columns=['Ask_5', 'Ask_4', 'Ask_3', 'Ask_2', 'l5', 'l4', 'l3', 'l2'])
			return bid_queues, ask_queues
		else:
			return bid_queues, ask_queues
		
	def queueFromatHelper(self, data):
		l1 = []
		l2 = []
		l3 = []
		l4 = []
		l5 = []
		for x in range(len(data)):
			l1.append(data[x][-1])
			l2.append(data[x][-2])
			l3.append(data[x][-3])
			l4.append(data[x][-4])
			l5.append(data[x][-5])

		return pd.DataFrame({"l1":l1, "l2":l2, "l3":l3, "l4":l4, "l5":l5})


	def formatQueues(self):
		"""
		Get the queue lengths and orders in each queue for 5 price levels

		Returns:
			DataFrame: L5 Bid queues and their lengths 
			DataFrame: L5 Ask queues and their lengths 
		"""
		formatted_bid_queues = []
		formatted_ask_queues = []
		
		for i in self.queues:
			entire_book = i[0]
			bid_qs = entire_book[0]
			ask_qs = entire_book[1]
			symetric_bids = []
			symetric_asks = []
			bid_lens = []
			ask_lens = []

			if len(bid_qs) != 5:
				for a in range(5-len(bid_qs)):
					symetric_bids.append(None)
					bid_lens.append(0)
				for b in bid_qs:
					symetric_bids.append(b)
					if type(b[0]) != list:
						bid_lens.append(1)
					else:
						bid_lens.append(len(b))
			else:
				for c in bid_qs:
					symetric_bids.append(c)
					if type(c[0]) != list:
						bid_lens.append(1)
					else:
						bid_lens.append(len(c))
			symetric_bids.append(bid_lens)

			if len(ask_qs) != 5:
				for x in range(5-len(ask_qs)):
					symetric_asks.append(None)
					ask_lens.append(0)
				for y in ask_qs:
					symetric_asks.append(y)
					if type(y[0]) != list:
						ask_lens.append(1)
					else:
						ask_lens.append(len(y))
			else:
				for z in ask_qs:
					symetric_asks.append(z)
					if type(z[0]) != list:
						ask_lens.append(1)
					else:
						ask_lens.append(len(z))
			symetric_asks.append(ask_lens)

			formatted_bid_queues.append(symetric_bids)
			formatted_ask_queues.append(symetric_asks)

		bid_queues = pd.DataFrame(formatted_bid_queues, columns = ['Bid_5', 'Bid_4', 'Bid_3', 'Bid_2', 'Bid_1', 'Bid_Q_lens'])
		ask_queues = pd.DataFrame(formatted_ask_queues, columns = ['Ask_1', 'Ask_2', 'Ask_3', 'Ask_4', 'Ask_5', 'Ask_Q_lens'])
		return bid_queues, ask_queues
	
##############
# Mthods to format output for graphing
##############

	def groupAttributes(self, bids, asks):
		"""
		This function takes bid and ask attributes (side, vol, level, time) and creates a df containing 
		lists of each for each time increment.

		Returns:
			DataFrame: grouped attributes of the book at each time increment
		"""

		b_name = ['Bid 5', 'Bid 4', 'Bid 3', 'Bid 2', 'Best Best']
		a_name = ['Best ask', 'Ask 2', 'Ask 3', 'Ask 4', 'Ask 5']

		transpose_bids = []
		transpose_asks = []

		for i in range(len(bids)):

			bid_time = bids.iloc[i]['Time']
			bid_prices = [bids.iloc[i].Bid_5, bids.iloc[i].Bid_4, bids.iloc[i].Bid_3, bids.iloc[i].Bid_2, bids.iloc[i].Bid_1]
			bid_vols = [bids.iloc[i].Bid_5_Vol, bids.iloc[i].Bid_4_Vol, bids.iloc[i].Bid_3_Vol, bids.iloc[i].Bid_2_Vol, bids.iloc[i].Bid_1_Vol]
			bid_levels = b_name
			transpose_bids.append([bid_time, bid_vols, bid_prices, bid_levels])

			ask_time = asks.iloc[i]['Time']
			ask_prices = [asks.iloc[i].Ask_1, asks.iloc[i].Ask_2, asks.iloc[i].Ask_3, asks.iloc[i].Ask_4, asks.iloc[i].Ask_5]
			ask_vols = [asks.iloc[i].Ask_1_Vol, asks.iloc[i].Ask_2_Vol, asks.iloc[i].Ask_3_Vol, asks.iloc[i].Ask_4_Vol, asks.iloc[i].Ask_5_Vol]
			ask_levels = a_name
			transpose_asks.append([ask_time, ask_vols, ask_prices, ask_levels])

		transpose_bids = pd.DataFrame(transpose_bids, columns=['Time','Bid_vol','Bid_Prices','Bid_level'])
		transpose_asks = pd.DataFrame(transpose_asks, columns=['Time','Ask_vol','Ask_Prices','Ask_level'])

		flat_book = self.flattenBook(transpose_bids, transpose_asks)
		return flat_book

	def flattenBook(self, transpose_bids, transpose_asks):
		"""
		Squash each row in the above method by time so we can graph the output

		Returns:
			DataFrame: transposed book to graph with
		"""
		flattened_limits = []
		for i in range(len(transpose_bids)):
			ts = transpose_bids.iloc[i]['Time']
			bs = transpose_bids.iloc[i]['Bid_vol']
			ns = transpose_bids.iloc[i]['Bid_level']
			ps = transpose_bids.iloc[i]['Bid_Prices']
			for j in range(len(bs)):
				flattened_limits.append([ts, bs[j], ns[j], ps[j], 'Bid'])
			bs = transpose_asks.iloc[i]['Ask_vol']
			ns = transpose_asks.iloc[i]['Ask_level']
			ps = transpose_asks.iloc[i]['Ask_Prices']
			for k in range(len(bs)):
				flattened_limits.append([ts, bs[k], ns[k], ps[k], 'Ask'])

		flattened_limits = pd.DataFrame(flattened_limits, columns=['Time', 'Vol', 'Level', 'Price', 'Side'])
		return flattened_limits
