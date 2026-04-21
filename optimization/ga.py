import random
from data.setup_matrix import SKUS
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


def fitness(seq, demand, out_seq):

    key = tuple(seq)

    if key in fitness_cache:
        return fitness_cache[key]

    result = run_simulation(seq)

    # demand matching penalty
    demand_penalty = 0
    for sku in demand:
        produced = seq.count(sku)
        needed = demand[sku]
        demand_penalty += abs(needed - produced)

    penalty_seq = sequence_penalty(seq, out_seq)

    score = (
        5 * result["throughput"]
        - 3 * result["setup"]
        - 4 * result["starvation"]
        - 2 * result["blocking"]
        - 2 * demand_penalty
        - 3 * penalty_seq
    )

    fitness_cache[key] = score
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


def GA(demand, out_seq):

    SKUS = list(demand.keys()) if demand else ["A","B","C"]

    # -----------------------
    # Initial Population
    # -----------------------
    pop = []

    # Heuristic seed
    # Use curing out sequence as priority
    base_seq = out_seq[:LEN]

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

    # -----------------------
    # GA Evolution
    # -----------------------
    for g in range(GEN):

        # evaluate
        pop = sorted(pop, key=lambda x: fitness(x, demand, out_seq), reverse=True)

        new_pop = pop[:ELITE]  # elitism

        while len(new_pop) < POP:

            p1 = random.choice(pop[:10])
            p2 = random.choice(pop[:10])

            child = crossover(p1, p2)
            child = mutate(child, SKUS)

            new_pop.append(child)

        pop = new_pop

    best = max(pop, key=lambda x: fitness(x, demand, out_seq))

    return best