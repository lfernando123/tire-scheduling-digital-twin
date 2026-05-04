import random
from data.recipes import recipes


def heuristic_scheduler(out_seq, LEN=20):

    # -----------------------------
    # 1. Extract SKUs from out sequence
    # -----------------------------
    out_skus = [item["sku"] for item in out_seq]

    if not out_skus:
        return [random.choice(list(recipes.keys())) for _ in range(LEN)]

    # -----------------------------
    # 2. Count frequency
    # -----------------------------
    freq = {}

    for sku in out_skus:
        freq[sku] = freq.get(sku, 0) + 1

    # -----------------------------
    # ORDER + GROUP HEURISTIC
    # -----------------------------
    seq = []

    i = 0

    while len(seq) < LEN and i < len(out_skus):

        sku = out_skus[i]

        # count consecutive same SKU
        count = 1
        while i + 1 < len(out_skus) and out_skus[i+1] == sku:
            count += 1
            i += 1

        # repeat slightly more for stability
        repeat = count + (1 if recipes[sku]["layers"] == 3 else 0)

        for _ in range(repeat):
            if len(seq) < LEN:
                seq.append(sku)

        i += 1

    # -----------------------------
    # 5. Fill remaining positions
    # -----------------------------
    all_skus = list(recipes.keys())

    while len(seq) < LEN:
        seq.append(random.choice(all_skus))

    # -----------------------------
    # 6. Small local smoothing (reduce switching)
    # -----------------------------
    for i in range(1, len(seq)-1):

        if seq[i] != seq[i-1] and seq[i] != seq[i+1]:
            # try to reduce isolated SKU
            if random.random() < 0.5:
                seq[i] = seq[i-1]

    return seq