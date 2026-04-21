import random
from data.recipes import recipes

class Oven:

    def __init__(self, oven_id, sku):

        self.oven_id = oven_id
        self.sku = sku

        # initialize random remaining curing time
        self.remaining_time = random.uniform(0.3 * recipes[sku]["curing"], recipes[sku]["curing"])

    def update(self, time_passed):

        self.remaining_time -= time_passed

        if self.remaining_time <= 0:

            # reset with new curing cycle
            self.remaining_time = recipes[self.sku]["curing"]