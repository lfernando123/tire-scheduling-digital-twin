import itertools
import random

SKUS = ["A","B","C","D","E","F","G","H"]

setup_matrix = {}

for i in SKUS:
    for j in SKUS:

        if i == j:
            setup_matrix[(i,j)] = 0
        else:
            # realistic variation
            setup_matrix[(i,j)] = random.randint(3,10)