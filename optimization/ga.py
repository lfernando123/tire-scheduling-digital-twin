import random
from data.setup_matrix import SKUS
from data.recipes import recipes
from simulation.oven import Oven
from simulation.simulation_runner import run_simulation
from optimization.fitness_cache import fitness_cache

POP = 40
GEN = 30
LEN = 8
ELITE = 2
MUT_RATE = 0.2

def sequence_penalty(seq, out_seq):

    penalty = 0

    for i in range(min(len(seq), len(out_seq))):

        if seq[i] != out_seq[i]:
            penalty += 1

    return penalty


def fitness(seq, out_seq):

    result = run_simulation(seq)

    # -----------------------------
    # 1. Sequence Matching (MOST IMPORTANT)
    # -----------------------------
    out_skus = [item["sku"] for item in out_seq]

    seq_penalty = 0

    for i in range(min(len(seq), len(out_skus))):
        if seq[i] != out_skus[i]:
            # earlier mismatch = higher penalty
            seq_penalty += (len(seq) - i)

    # -----------------------------
    # 2. Soft Compound Changeovers (CRITICAL)
    # -----------------------------
    soft_change = 0

    for i in range(1, len(seq)):
        prev = seq[i-1]
        curr = seq[i]

        # only consider 3-layer tires (soft layer exists)
        if recipes[prev]["layers"] == 3 and recipes[curr]["layers"] == 3:

            if prev != curr:
                soft_change += 1

    # -----------------------------
    # 3. General Setup (Optional)
    # -----------------------------
    setup_penalty = result["setup"]

    # -----------------------------
    # FINAL SCORE
    # -----------------------------
    score = (
        -10 * seq_penalty      # VERY IMPORTANT
        -8  * soft_change      # CRITICAL
        -2  * setup_penalty    # less important
        +3  * result["throughput"]
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


def GA(out_seq):

    SKUS = list(recipes.keys())

    # -----------------------
    # Initial Population
    # -----------------------
    pop = []

    # Heuristic seed
    # Use curing out sequence as priority
    base_seq = [item["sku"] for item in out_seq[:LEN]]

    if len(base_seq) < LEN:
        base_seq += [random.choice(SKUS)] * (LEN - len(base_seq))

    # ensure valid length
    if len(base_seq) < LEN:
        base_seq += [random.choice(SKUS)] * (LEN - len(base_seq))

    pop.append(base_seq)

    # random population
    for _ in range(POP-1):
        seq = [random.choice(SKUS) for _ in range(LEN)]
        pop.append(seq)

    for seq in pop:
        for x in seq:
            if not isinstance(x, str):
                print("ERROR: Non-string in sequence →", x)

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