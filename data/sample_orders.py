import random

def generate_orders():

    demand = {}

    SKUS = ["A","B","C","D","E","F","G","H"]

    for sku in SKUS:

        demand[sku] = random.randint(5,20)

    return demand