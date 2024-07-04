# Stoikov_Micro_Price

Walk through of Sasha Stoikovs paper on the Micro Price

Paper can be found here: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2970694

Using a MSFT data set, we observe a similar result to Stoikov:

as spreads widen, the price adjustment is less affected by imbalance

![Adj](https://github.com/samdelaney42/L2_Order_Book_Handler/blob/main/data/images/adj.png)

Interestingly, when it comes to the stationary distribution, we see far fewer observations of a 'balanced imbalance' for a 1 tick spread.
Both one and two tick spreads have more observations at the extreme ends of imbalance rather than in the middle.

![Count](https://github.com/samdelaney42/L2_Order_Book_Handler/blob/main/data/images/counts.png)
