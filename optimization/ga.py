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


def fitness(seq, out_seq):

    # ----------------------
    # SAFE CACHE KEY
    # ----------------------
    key = tuple(seq)   # only sequence (safe)

    if key in fitness_cache:
        return fitness_cache[key]

    if len(set(seq)) == 1:
        return 0

    result = run_simulation(seq)

    out_skus = [item["sku"] for item in out_seq]

    # -----------------------------
    # 1. SEQUENCE MATCH (PRIORITY)
    # -----------------------------
    # seq_penalty = 0

    # for i in range(min(len(seq), len(out_skus))):
    #     if seq[i] != out_skus[i]:
    #         seq_penalty += (len(seq) - i)

    # seq_score = 1 - (seq_penalty / (len(seq)**2 + 1))

    out_weights = [item["soft_weight"] for item in out_seq]

    # -------------------------
    # COMPONENT SCORES
    # -------------------------
    s1 = sequence_score(seq, out_skus)
    s2 = soft_order_score(seq, out_weights)
    s3 = zigzag_score(seq)


    # # -----------------------------
    # # 2. SKU DISTRIBUTION MATCH
    # # -----------------------------
    # freq_penalty = 0

    # for sku in set(out_skus):
    #     freq_penalty += abs(seq.count(sku) - out_skus.count(sku))

    # freq_score = 1 - (freq_penalty / (len(seq) + 1))


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
    # 6. TIME VIOLATION (PENALTY)
    # -----------------------------

    prod_times = estimate_times(seq)

    time_violation = 0

    for i in range(len(seq)):
        for j in range(i+1, len(seq)):

            if seq[i] == seq[j]:

                if abs(prod_times[j] - prod_times[i]) > 10:
                    time_violation += 1
    
    time_score = 1 / (1 + time_violation)


    # -----------------------------
    # FINAL SCORE (BALANCED)
    # -----------------------------
    score = (
        0.20 * s1
        + 0.20 * s2
        + 0.20 * s3
        + 0.20 * throughput_score
        + 0.10 * setup_score
        + 0.10 * time_score
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


def tournament(pop, out_seq, tournament_size=3):
    """
    Tournament selection: select best individual from random sample
    """
    tournament_pop = random.sample(pop, min(tournament_size, len(pop)))
    return max(tournament_pop, key=lambda x: fitness(x, out_seq))


def GA(out_seq):

    SKUS = list(recipes.keys())

    # -----------------------
    # Initial Population
    # -----------------------

    pop = []

    out_skus = [item["sku"] for item in out_seq]
    out_times = [item["time"] for item in out_seq]
    out_weights = [item["soft_weight"] for item in out_seq]

    # -----------------------------
    # 1. BASE SEQUENCE (STRICT ORDER)
    # -----------------------------
    base_seq = out_skus[:LEN]

    if len(base_seq) < LEN:
        base_seq += [random.choice(out_skus) for _ in range(LEN - len(base_seq))]

    pop.append(base_seq)

    seq = []

    # 2. grouped
    pop.append(seq_grouped(out_skus, out_times, out_weights, LEN))

    # 3. zigzag
    pop.append(seq_zigzag(out_skus, LEN))


    # -----------------------------
    # 2. GROUPED + TIME-AWARE GENERATION
    # -----------------------------
    for _ in range(POP-1):

        seq = []
        i = 0

        while len(seq) < LEN and i < len(out_skus):

            sku = out_skus[i]
            base_time = out_times[i]

            # group SKUs within 10-minute window
            group = [sku]

            j = i + 1

            while j < len(out_skus):

                if out_skus[j] == sku and (out_times[j] - base_time) <= 10:
                    group.append(out_skus[j])
                    j += 1
                else:
                    break

            # add grouped SKUs (with slight variation)
            repeat = len(group)

            # slight randomness
            repeat += random.randint(0,1)

            for _ in range(repeat):
                if len(seq) < LEN:
                    seq.append(sku)

            i = j

        # fill remaining
        while len(seq) < LEN:
            seq.append(random.choice(out_skus))



        pop.append(seq)

    print(pop)

    # -----------------------
    # GA Evolution
    # -----------------------
    # for g in range(GEN):

    #     # evaluate
    #     pop = sorted(pop, key=lambda x: fitness(x, out_seq), reverse=True)

    #     new_pop = pop[:ELITE]  # elitism

    #     while len(new_pop) < POP:

    #         p1 = random.choice(pop[:10])
    #         p2 = random.choice(pop[:10])

    #         child = crossover(p1, p2)
            
    #         child = mutate(child, SKUS)

    #         new_pop.append(child)

    #     pop = new_pop

    for g in range(GEN):

        pop = sorted(pop, key=lambda x: fitness(x, out_seq), reverse=True)

        new_pop = pop[:ELITE]

        while len(new_pop) < POP:

            p1 = tournament(pop, out_seq)
            p2 = tournament(pop, out_seq)

            child = block_crossover(p1, p2, out_skus)

            child = smart_mutation(child, out_skus, out_times, out_weights)

            child = repair_sequence(child, out_times, out_weights)

            new_pop.append(child)

    pop = new_pop
    
    best = max(pop, key=lambda x: fitness(x, out_seq))

    return best

def estimate_times(seq):

    times = []
    t = 0

    for sku in seq:

        r = recipes[sku]

        pt = 0

        if r["layers"] == 3:
            pt += sum(config.HEEL_TIME)/2

        pt += sum(config.SOFT_TIME)/2
        pt += sum(config.TREAD_TIME)/2

        t += pt
        times.append(t)

    return times


def seq_grouped(out_skus, out_times, out_weights, LEN):

    seq = []

    skus = out_skus.copy()
    times = out_times.copy()
    weights = out_weights.copy()

    while skus and len(seq) < LEN:

        base_sku = skus[0]
        base_time = times[0]

        total_weight = 0
        group = []

        for i in range(len(skus)):

            if skus[i] != base_sku:
                continue

            if abs(times[i] - base_time) > 10:
                continue

            if total_weight + weights[i] > 40:
                continue

            group.append(i)
            total_weight += weights[i]

        # add to sequence
        for idx in group:
            if len(seq) < LEN:
                seq.append(skus[idx])

        # remove used
        for idx in sorted(group, reverse=True):
            skus.pop(idx)
            times.pop(idx)
            weights.pop(idx)

        # fallback
        if not group:
            seq.append(skus.pop(0))
            times.pop(0)
            weights.pop(0)

    return seq

def zigzag_indices(n):

    # split into two big lines
    half = n // 2

    line1 = list(range(0, half))
    line2 = list(range(half, n))

    # split each line into 2 sub-lines
    def split_line(line):
        mid = len(line) // 2
        return line[:mid], line[mid:]

    l1a, l1b = split_line(line1)
    l2a, l2b = split_line(line2)

    # zig-zag pattern
    order = []

    max_len = max(len(l1a), len(l1b), len(l2a), len(l2b))

    for i in range(max_len):

        if i < len(l1a): order.append(l1a[i])
        if i < len(l1b): order.append(l1b[i])
        if i < len(l2a): order.append(l2a[i])
        if i < len(l2b): order.append(l2b[i])

    return order

def seq_zigzag(out_skus, LEN):

    n = len(out_skus)

    indices = zigzag_indices(n)

    seq = []

    for idx in indices:
        if idx < n and len(seq) < LEN:
            seq.append(out_skus[idx])

    # fill if needed
    while len(seq) < LEN:
        seq.append(out_skus[-1])

    return seq


def block_crossover(p1, p2, out_skus):

    n = len(p1)

    # choose a block from parent 1
    start = random.randint(0, n//2)
    end = random.randint(start+1, n)

    child = p1[start:end]

    # fill remaining from parent 2 (order preserved)
    for sku in p2:
        if len(child) >= n:
            break
        child.append(sku)

    # ensure valid length
    return child[:n]


def smart_mutation(seq, out_skus, out_times, out_weights):

    new_seq = seq.copy()
    n = len(seq)

    if random.random() < 0.3:

        i = random.randint(0, n-1)

        # try to align with curing sequence
        if i < len(out_skus):
            new_seq[i] = out_skus[i]

    if random.random() < 0.3:

        # swap nearby elements (preserve structure)
        i = random.randint(0, n-2)
        j = i + 1

        new_seq[i], new_seq[j] = new_seq[j], new_seq[i]

    if random.random() < 0.3:

        # enforce grouping
        i = random.randint(1, n-1)
        new_seq[i] = new_seq[i-1]

    return new_seq


def repair_sequence(seq, out_times, out_weights):

    repaired = []

    total_weight = 0
    last_time = None

    for i, sku in enumerate(seq):

        if i < len(out_times):
            t = out_times[i]
            w = out_weights[i]
        else:
            repaired.append(sku)
            continue

        # reset if constraint violated
        if last_time is not None:

            if abs(t - last_time) > 10 or total_weight + w > 40:
                total_weight = 0

        repaired.append(sku)

        total_weight += w
        last_time = t

    return repaired

def sequence_score(seq, out_skus):

    score = 0

    for i in range(min(len(seq), len(out_skus))):
        if seq[i] == out_skus[i]:
            score += 1

    # normalize (0–1)
    return score / len(seq)

def zigzag_score(seq):

    score = 0

    direction = 1  # alternate pattern

    for i in range(1, len(seq)):

        if seq[i] == seq[i-1]:
            val = 0
        else:
            val = 1 if direction == 1 else -1

        score += val

        direction *= -1  # flip

    # normalize
    return (score + len(seq)) / (2 * len(seq))



def soft_order_score(seq, out_weights):

    if not seq:
        return 0

    scores = []

    count = 1
    total_weight = out_weights[0]

    scores.append(count)

    for i in range(1, len(seq)):

        if seq[i] == seq[i-1] and total_weight + out_weights[i] <= 40:
            count += 1
            total_weight += out_weights[i]
        else:
            count = 1
            total_weight = out_weights[i]

        scores.append(count)

    total_score = sum(scores)
    max_possible = sum(range(1, len(seq)+1))

    return total_score / max_possible