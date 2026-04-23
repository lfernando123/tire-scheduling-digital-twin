import random
from data.setup_matrix import SKUS
from data.recipes import recipes
from simulation.oven import Oven
from simulation.simulation_runner import run_simulation
from optimization.fitness_cache import fitness_cache
from simulation.kpi import KPI
import config

POP = 40
GEN = 60
LEN = 8
ELITE = 2
MUT_RATE = 0.2

def estimate_production_times(seq):

    times = []
    current_time = 0

    for sku in seq:

        r = recipes[sku]

        # estimate processing time
        t = 0

        if r["layers"] == 3:
            t += sum(config.HEEL_TIME)/2

        t += sum(config.SOFT_TIME)/2
        t += sum(config.TREAD_TIME)/2

        current_time += t
        times.append(current_time)

    return times

# def fitness(seq, out_seq):

#     result = run_simulation(seq)

#     # -----------------------------
#     # 1. Sequence Matching (MOST IMPORTANT)
#     # -----------------------------
#     out_skus = [item["sku"] for item in out_seq]
#     out_times = [item["time"] for item in out_seq]

#     seq_penalty = 0

#     for i in range(min(len(seq), len(out_skus))):
#         if seq[i] != out_skus[i]:
#             # earlier mismatch = higher penalty
#             seq_penalty += (len(seq) - i)

#     freq_penalty = 0

#     for sku in set(out_skus):
#         freq_penalty += abs(seq.count(sku) - out_skus.count(sku))

#     # prod_times = estimate_production_times(seq)

#     # time_penalty = 0

#     # for i in range(min(len(seq), len(out_skus))):

#     #     if seq[i] == out_skus[i]:
#     #         # correct SKU → check timing
#     #         time_diff = abs(prod_times[i] - out_times[i])
#     #         time_penalty += time_diff

#     #     else:
#     #         # wrong SKU → heavy penalty
#     #         time_penalty += 50

#     # -----------------------------
#     # 2. Soft Compound Changeovers (CRITICAL)
#     # -----------------------------
#     soft_change = 0

#     for i in range(1, len(seq)):
#         prev = seq[i-1]
#         curr = seq[i]

#         # only consider 3-layer tires (soft layer exists)
#         if recipes[prev]["layers"] == 3 and recipes[curr]["layers"] == 3:

#             if prev != curr:
#                 soft_change += 1

#     # -----------------------------
#     # 3. General Setup (Optional)
#     # -----------------------------
#     setup_penalty = result["setup"]

#     # -----------------------------
#     # FINAL SCORE
#     # -----------------------------
#     score = (
#         -10 * seq_penalty
#         -5 * freq_penalty
#         -2 * soft_change
#         -2 * result["setup"]
#         +3 * result["throughput"]
#     )

#     return score

def fitness(seq, out_seq):

    if len(set(seq)) == 1:
        return 0

    result = run_simulation(seq)

    out_skus = [item["sku"] for item in out_seq]

    # -----------------------------
    # 1. SEQUENCE MATCH (PRIORITY)
    # -----------------------------
    seq_penalty = 0

    for i in range(min(len(seq), len(out_skus))):
        if seq[i] != out_skus[i]:
            seq_penalty += (len(seq) - i)

    seq_score = 1 - (seq_penalty / (len(seq)**2 + 1))


    # -----------------------------
    # 2. SKU DISTRIBUTION MATCH
    # -----------------------------
    freq_penalty = 0

    for sku in set(out_skus):
        freq_penalty += abs(seq.count(sku) - out_skus.count(sku))

    freq_score = 1 - (freq_penalty / (len(seq) + 1))


    # -----------------------------
    # 3. SOFT CHANGEOVER
    # -----------------------------
    soft_change = 0

    for i in range(1, len(seq)):
        if recipes[seq[i]]["layers"] == 3 and recipes[seq[i-1]]["layers"] == 3:
            if seq[i] != seq[i-1]:
                soft_change += 1

    soft_score = 1 - (soft_change / (len(seq) + 1))


    # -----------------------------
    # 4. SETUP (normalize)
    # -----------------------------
    setup_score = 1 - (result["setup"] / (result["setup"] + 1000))


    # -----------------------------
    # 5. THROUGHPUT
    # -----------------------------
    throughput_score = result["throughput"] / (len(seq) + 1)


    # -----------------------------
    # FINAL SCORE (BALANCED)
    # -----------------------------
    score = (
        0.35 * seq_score       # 🔥 most important
        + 0.25 * freq_score
        + 0.15 * soft_score
        + 0.15 * throughput_score
        + 0.10 * setup_score
    )

    return score


def crossover(p1, p2):

    point = random.randint(1, LEN-2)

    child = p1[:point] + p2[point:]

    return child


def mutate(seq, SKUS):

    seq = seq.copy()

    if random.random() < MUT_RATE:
        i = random.randint(0, LEN-1)
        seq[i] = random.choice(SKUS)

    return seq

def perturb_sequence(seq, SKUS, intensity=0.2):
    """
    Apply small random changes to a sequence
    intensity = % of sequence to modify
    """

    new_seq = seq.copy()
    n = len(seq)

    num_changes = max(1, int(n * intensity))

    for _ in range(num_changes):

        move = random.choice(["swap", "replace", "shuffle"])

        # -----------------------
        # 1. SWAP (exchange two positions)
        # -----------------------
        if move == "swap":
            i, j = random.sample(range(n), 2)
            new_seq[i], new_seq[j] = new_seq[j], new_seq[i]

        # -----------------------
        # 2. REPLACE (change SKU)
        # -----------------------
        elif move == "replace":
            i = random.randint(0, n-1)
            new_seq[i] = random.choice(SKUS)

        # -----------------------
        # 3. SHUFFLE BLOCK
        # -----------------------
        elif move == "shuffle":
            start = random.randint(0, n-2)
            end = min(n, start + random.randint(2, 4))

            block = new_seq[start:end]
            random.shuffle(block)

            new_seq[start:end] = block

    return new_seq


def GA(out_seq):

    SKUS = list(recipes.keys())

    # -----------------------
    # Initial Population
    # -----------------------
    pop = []

    # Use curing out sequence as priority 
    base_seq = [item["sku"] for item in out_seq[:LEN]]

    # 1. Base sequence
    pop.append(base_seq)

    # 2. Perturbations (30%)
    for _ in range(int(POP * 0.3)):
        pop.append(perturb_sequence(base_seq, SKUS, 0.3))

    # 3. Sequence repetition (40%)
    for _ in range(int(POP * 0.4)):
        seq = []
        while len(seq) < LEN:
            sku = random.choice([item["sku"] for item in out_seq])
            repeat = random.randint(1,3)
            for _ in range(repeat):
                if len(seq) < LEN:
                    seq.append(sku)
        pop.append(seq)

    # 4. Random (remaining)
    while len(pop) < POP:
        seq = [random.choice(SKUS) for _ in range(LEN)]
        pop.append(seq)

    # priority_skus = [item["sku"] for item in out_seq]

    # for _ in range(POP-1):

    #     seq = []

    #     while len(seq) < LEN:

    #         # pick SKU from out_seq priority
    #         sku = random.choice(priority_skus) if priority_skus else random.choice(SKUS)

    #         # repeat count (IMPORTANT)
    #         repeat = random.randint(1, 3)

    #         for _ in range(repeat):
    #             if len(seq) < LEN:
    #                 seq.append(sku)

    #     pop.append(seq)
    

    print(pop)


    # -----------------------
    # GA Evolution
    # -----------------------
    for g in range(GEN):

        # evaluate
        pop = sorted(pop, key=lambda x: fitness(x, out_seq), reverse=True)

        new_pop = pop[:ELITE]  # elitism

        while len(new_pop) < POP:

            p1 = random.choice(pop[:10])
            p2 = random.choice(pop[:10])

            child = crossover(p1, p2)
            child = mutate(child, SKUS)

            new_pop.append(child)

        pop = new_pop
    
    best = max(pop, key=lambda x: fitness(x, out_seq))

    return best