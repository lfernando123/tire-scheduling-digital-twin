import random
from data.recipes import recipes

class Oven:

    def __init__(self, oven_id, sku):

        self.oven_id = oven_id
        self.sku = sku

        # initialize random remaining curing time
        self.remaining_time = random.uniform(0.3 * recipes[sku]["curing"], recipes[sku]["curing"])

        self.soft_weight = recipes[sku]["weight"]

        if self.oven_id <= 23:
            self.line = "l1a"
        elif self.oven_id > 23 and self.oven_id <= 46:
            self.line = "l1b"
        elif self.oven_id > 46 and self.oven_id <= 68:
            self.line = "l2a"
        else:
            self.line = "l2b"

    def update(self, time_passed):

        self.remaining_time -= time_passed

        if self.remaining_time <= 0:

            # reset with new curing cycle
            self.remaining_time = recipes[self.sku]["curing"]