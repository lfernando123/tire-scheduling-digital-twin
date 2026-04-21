def heuristic_sequence(demand):

    seq = []

    # sort by highest demand
    sorted_skus = sorted(demand, key=demand.get, reverse=True)

    for sku in sorted_skus:

        seq += [sku]*min(3, demand[sku])

    return seq[:6]