import random
from simulation.oven import Oven

SKUS = ["A","B","C","D","E","F","G","H"]

class OvenSystem:

    def __init__(self, n_ovens=45):

        self.ovens = []

        for i in range(n_ovens):

            sku = random.choice(SKUS)

            oven = Oven(i, sku)

            self.ovens.append(oven)


    def update(self, time_passed):

        for oven in self.ovens:
            oven.update(time_passed)


    def get_demand(self, horizon=30):

        """
        Count how many ovens will finish within next 30 minutes
        """

        demand = {}

        for oven in self.ovens:

            if oven.remaining_time <= horizon:

                demand[oven.sku] = demand.get(oven.sku, 0) + 1

        return demand
    
    def get_out_sequence(self, horizon=30):

        """
        Return ordered list of SKUs based on curing completion
        """

        # select ovens finishing within horizon
        finishing = [
            oven for oven in self.ovens
            if oven.remaining_time <= horizon
        ]

        # sort by remaining time (earliest first)
        finishing.sort(key=lambda x: x.remaining_time)

        # return SKU sequence
        return [oven.sku for oven in finishing]