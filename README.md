# Queue_Weighted_Stoikov_Micro_Price

Here, I use my L2 Order Book Handler implementaiton to expand on Stoikov's Micro Price paper.

Original paper can be found here: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2970694

Instead of using volume at the top of the book to calculate imbalance, I use order queue length.

If we assume that each order represents a different market participant, it may be a better indicatior of demand and therfore fair price rather than volume.

Only limit prices and volumes are present in the LOBSTER order book data - my implementation allows us to include order queue length in the output.

Using the MSFT 50 LOBSTER message data set, I first walk through the paper and re create the results:

We find, as Stoikov does, that as spreads widen, the price adjustment is less affected by imbalance (1 tick spread steeper than 2).

![comparsion](https://github.com/samdelaney42/Stoikov_Micro_Price/blob/main/data/images/adj.png)

When using queue lenght to calculate imbalance, we see slightly different behaviour:

We see that for a 1 tick spread, the price adjustment is very close the weighted mid and almost linear whereas the 2 tick spread is much shallower, indicating that queue length imbalance is significantly less informative as spread widnes

![comparsion_2](https://github.com/samdelaney42/Stoikov_Micro_Price/blob/main/data/images/q_adj.png)

With regard to observation frequency, the difference between edge and middle imbalances for a 1 tick spread is more signifcant than for 2 ticks.
Interestingly, they have an almost identical distribution pattern too.

![comparsion_3](https://github.com/samdelaney42/Stoikov_Micro_Price/blob/main/data/images/q_counts.png)


