# from curses.ascii import alt
import random
from data.setup_matrix import SKUS
from data.recipes import recipes
from simulation.oven import Oven
from simulation.simulation_runner import run_simulation
from optimization.fitness_cache import fitness_cache
from simulation.kpi import KPI
import config
from collections import defaultdict

POP = 30
GEN = 45
LEN = 15
ELITE = 2
MUT_RATE = 0.2
weight_map = defaultdict(list)

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

    key = tuple(seq)

    if key in fitness_cache:
        return fitness_cache[key]

    if len(set(seq)) == 1:
        return 0

    result = run_simulation(seq)

    # --------------------------------
    # EXTRACT DATA
    # --------------------------------
    out_skus = [item["sku"] for item in out_seq]

    out_lines = [item["line"] for item in out_seq]

    # --------------------------------
    # BUILD WEIGHT MAP
    # --------------------------------
    weight_map = defaultdict(list)

    for item in out_seq:
        weight_map[item["sku"]].append(item["weight"])

    # --------------------------------
    # 1. SEQUENCE MATCH
    # --------------------------------
    match_score = 0

    for i in range(min(len(seq), len(out_skus))):

        if seq[i] == out_skus[i]:
            match_score += 1

    match_norm = match_score / len(seq)

    # --------------------------------
    # 2. SOFT GROUPING
    # --------------------------------
    soft_raw = soft_order_score(seq, weight_map)

    # theoretical max
    max_soft = sum([(i+1)**2 for i in range(len(seq))])

    soft_norm = soft_raw / max_soft

    # nonlinear amplification
    soft_final = soft_norm ** 2

    # --------------------------------
    # 3. ZIGZAG
    # --------------------------------
    pattern = select_pattern(out_seq)

    zigzag_raw = zigzag_score(
        out_lines,
        pattern
    )

    zigzag_norm = normalize(
        zigzag_raw,
        -len(seq),
        len(seq)
    )

    # --------------------------------
    # 4. THROUGHPUT
    # --------------------------------
    throughput_norm = result["throughput"] / (len(seq) + 1)

    # --------------------------------
    # 5. SETUP PENALTY
    # --------------------------------
    setup_penalty = 1 / (1 + result["setup"])

    # --------------------------------
    # FINAL SCORE
    # --------------------------------
    score = (
        0.40 * soft_final
        + 0.30 * match_norm
        + 0.20 * zigzag_norm
        + 0.10 * throughput_norm
    )

    # --------------------------------
    # HARD PENALTY
    # --------------------------------
    if soft_raw < len(seq):
        score *= 0.5

    if score > 1.5:
        print(seq)
        print("Sequence:", match_norm, "soft_orders1", soft_final, "zigzag", zigzag_norm, "throughput", throughput_norm, "setup", setup_penalty, "→", score)

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

# =========================================================
# CHROMOSOME GENERATION PIPELINE
# =========================================================

# ---------------------------------------------------------
# Chromosome 1
# Original curing out sequence
# ---------------------------------------------------------
def chromosome_1(out_seq, LEN):
    print("Chromosome 1:", [f'{item["sku"]}:{item["line"]}' for item in out_seq[:LEN]])
    return out_seq[:LEN]


# =========================================================
# VALID ZIGZAG PATTERNS
# =========================================================
ZIGZAG_PATTERNS = [
    ["l1a", "l2b", "l1b", "l2a"],
    ["l1b", "l2b", "l1a", "l2a"],
    ["l1a", "l2a", "l1b", "l2b"],
    ["l1b", "l2a", "l1a", "l2b"],
    ["l2a", "l1b", "l2b", "l1a"],
    ["l2a", "l1a", "l2b", "l1b"],
    ["l2b", "l1b", "l2a", "l1a"],
    ["l2b", "l1a", "l2a", "l1b"]
]


# =========================================================
# SELECT BEST PATTERN
# =========================================================
def select_pattern(prev_seq):

    """
    Select zigzag pattern based on
    last arranged chromosome.
    """

    if not prev_seq:
        return ZIGZAG_PATTERNS[0]

    first_line = prev_seq[0]["line"].lower()
    second_line = prev_seq[1]["line"].lower()
    i = 0

    for pattern in ZIGZAG_PATTERNS:

        if pattern[0] == first_line:
            if pattern[1] == second_line:
                return pattern
            else:
                rec_index = i
            
        i += 1

    return ZIGZAG_PATTERNS[rec_index]


# =========================================================
# Chromosome 2
# Zigzag arrangement
# =========================================================
def chromosome_2(c1, out_seq):

    """
    Strict zigzag arrangement.

    Must follow valid pattern order.
    """

    pattern = select_pattern(c1)

    remaining = c1.copy()

    seq = []

    p = 0

    other_out_seq = [item for item in out_seq if item not in c1]

    while remaining:

        target_line = pattern[p % len(pattern)]

        next_valid_line = pattern[(p+2) % len(pattern)]

        found = False

        prev_sku_time = remaining[0]["time"] if remaining else 0

        # --------------------------------
        # SEARCH NEXT VALID ITEM
        # --------------------------------
        for i, item in enumerate(remaining):

            line = item["line"].lower()

            if line == target_line:

                seq.append(item)

                remaining.pop(i)

                found = True

                break

        # --------------------------------
        # IF NOT FOUND
        # --------------------------------
        if not found:

            found2 = False

            for i, item in enumerate(other_out_seq):

                time = item["time"]

                line = item["line"].lower()

                if line == target_line and time - prev_sku_time <= 10:

                    seq.append(item)

                    other_out_seq.pop(i)

                    found2 = True

                    break

            if not found2:
                seq.append(remaining.pop(0))



        p += 1
    print("Chromosome 2:", [f'{item["sku"]}:{item["line"]}' for item in seq[:LEN]])
    return seq


# =========================================================
# Chromosome 3
# Same SKU grouping within 5 min
# =========================================================
def chromosome_3(c2, out_seq, LEN):

    """
    Group same SKU using nearby curing outputs.

    Rules:
    - Base window = first LEN items
    - Can pull same SKU from future outputs
    - Only within 5 min
    - Weight <= 40
    """

    base_window = c2[:LEN]

    seq = []

    used = set()

    for base in base_window:

        base_id = (
            base["sku"],
            base["time"],
            base["oven"]
        )

        if base_id in used:
            continue

        sku = base["sku"]

        t0 = base["time"]

        total_weight = 0

        # search entire pipeline
        for item in out_seq:

            item_id = (
                item["sku"],
                item["time"],
                item["oven"]
            )

            if item_id in used:
                continue

            # same SKU only
            if item["sku"] != sku:
                continue

            # within 5 min
            if abs(item["time"] - t0) > 5:
                continue

            # weight limit
            if total_weight + item["weight"] > 40:
                continue

            seq.append(item)

            used.add(item_id)

            total_weight += item["weight"]

            if len(seq) >= LEN:
                print("Chromosome 3:", [f'{item["sku"]}:{item["line"]}' for item in seq[:LEN]])
                return seq

    # fill remaining
    for item in base_window:

        item_id = (
            item["sku"],
            item["time"],
            item["oven"]
        )

        if item_id not in used:

            seq.append(item)

            used.add(item_id)

            if len(seq) >= LEN:
                break
    
    print("Chromosome 3:", [item["sku"] for item in seq])
    return seq


# =========================================================
# Chromosome 4
# Zigzag while preserving grouping
# =========================================================
def chromosome_4(c3):

    pattern = select_pattern(c3)

    grouped = {
        "l1a": [],
        "l1b": [],
        "l2a": [],
        "l2b": []
    }

    # preserve grouping
    for item in c3:

        line = item["line"].lower()

        grouped[line].append(item)

    seq = []

    while True:

        added = False

        for p in pattern:

            if grouped[p]:

                seq.append(grouped[p].pop(0))

                added = True

        if not added:
            break

    print("Chromosome 4:", [f'{item["sku"]}:{item["line"]}' for item in seq[:LEN]])
    return seq


# =========================================================
# Minor deterministic refinement
# =========================================================
def minor_adjustment(prev):

    """
    Small local deterministic improvements.
    """

    seq = prev.copy()

    n = len(seq)

    # -----------------------------------------------------
    # Rule 1
    # Bring same SKUs together
    # -----------------------------------------------------
    for i in range(1, n-1):

        prev_sku = seq[i-1]["sku"]
        curr_sku = seq[i]["sku"]
        next_sku = seq[i+1]["sku"]

        if prev_sku == next_sku and curr_sku != prev_sku:

            seq[i], seq[i+1] = seq[i+1], seq[i]

            return seq

    # -----------------------------------------------------
    # Rule 2
    # Improve zigzag balance
    # -----------------------------------------------------
    for i in range(1, n-1):

        prev_line = seq[i-1]["line"][-1].lower()
        curr_line = seq[i]["line"][-1].lower()

        if prev_line == curr_line:

            seq[i], seq[i+1] = seq[i+1], seq[i]

            return seq

    # -----------------------------------------------------
    # Rule 3
    # Small local swap
    # -----------------------------------------------------
    for i in range(0, n-2, 2):

        seq[i], seq[i+1] = seq[i+1], seq[i]

        return seq

    print("Chromosome 5:", [item["sku"] for item in seq])
    return seq


# =========================================================
# Convert chromosome to SKU sequence
# =========================================================
def to_sku_seq(chromosome):

    return [x["sku"] for x in chromosome]


# =========================================================
# FINAL INITIAL POPULATION GENERATION
# =========================================================
def generate_population(out_seq, LEN, POP):

    pop = []

    # -----------------------------------------------------
    # Chromosome 1
    # -----------------------------------------------------
    c1 = chromosome_1(out_seq, LEN)
    pop.append(c1)

    # -----------------------------------------------------
    # Chromosome 2
    # -----------------------------------------------------
    c2 = chromosome_2(c1, out_seq)
    pop.append(c2)

    # -----------------------------------------------------
    # Chromosome 3
    # -----------------------------------------------------
    c3 = chromosome_3(c2, out_seq, LEN)
    pop.append(c3)

    # -----------------------------------------------------
    # Chromosome 4
    # -----------------------------------------------------
    c4 = chromosome_4(c3)
    pop.append(c4)

    # -----------------------------------------------------
    # Chromosome 5+
    # -----------------------------------------------------
    current = c4

    while len(pop) < POP:

        current = minor_adjustment(current)

        pop.append(current.copy())

    return pop


# =========================================================
# FINAL GA
# =========================================================
def GA(out_seq):

    fitness_cache.clear()

    # -----------------------------------------------------
    # INITIAL POPULATION
    # -----------------------------------------------------
    pop = generate_population(out_seq, LEN, POP)

    # -----------------------------------------------------
    # GA EVOLUTION
    # -----------------------------------------------------
    for g in range(GEN):

        # -------------------------------------------------
        # SORT POPULATION
        # -------------------------------------------------
        pop = sorted(
            pop,
            key=lambda x: fitness(
                to_sku_seq(x),
                out_seq
            ),
            reverse=True
        )

        # -------------------------------------------------
        # ELITISM
        # -------------------------------------------------
        new_pop = pop[:ELITE]

        # -------------------------------------------------
        # GENERATE NEW CHROMOSOMES
        # -------------------------------------------------
        while len(new_pop) < POP:

            # ---------------------------------------------
            # SELECT PARENT
            # deterministic selection
            # ---------------------------------------------
            parent = new_pop[-1]

            # ---------------------------------------------
            # MINOR REFINEMENT
            # ---------------------------------------------
            child = minor_adjustment(parent)

            # ---------------------------------------------
            # KEEP FULL CHROMOSOME
            # ---------------------------------------------
            new_pop.append(child.copy())

        # -------------------------------------------------
        # UPDATE POPULATION
        # -------------------------------------------------
        pop = new_pop

        # -------------------------------------------------
        # PRINT GENERATION BEST
        # -------------------------------------------------
        best_gen = pop[0]

        best_score = fitness(
            to_sku_seq(best_gen),
            out_seq
        )

        print(
            f"Generation {g+1} "
            f"Best Score = {round(best_score,4)}"
        )

    # -----------------------------------------------------
    # FINAL BEST
    # -----------------------------------------------------
    best = max(
        pop,
        key=lambda x: fitness(
            to_sku_seq(x),
            out_seq
        )
    )

    # -----------------------------------------------------
    # PRINT FINAL RESULT
    # -----------------------------------------------------
    print("\n=== BEST CHROMOSOME ===")

    print(to_sku_seq(best))

    print("\n=== FULL DATA ===")

    for item in best:

        print(
            f'{item["sku"]} | '
            f'Time={item["time"]} | '
            f'Line={item["line"]} | '
            f'Oven={item["oven"]}'
        )

    # -----------------------------------------------------
    # RETURN SKU SEQUENCE
    # -----------------------------------------------------
    return to_sku_seq(best)


def seq_direct(out_skus, LEN):

    seq = out_skus[:LEN]

    if len(seq) < LEN:
        seq += [out_skus[-1]] * (LEN - len(seq))

    return seq

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


def seq_zigzag(out_seq, LEN, last_line="l1a"):

    pattern = select_pattern(last_line)

    grouped = {p: [] for p in ["l1a","l1b","l2a","l2b"]}

    # group SKUs by line
    for item in out_seq:

        line = item["line"].lower()

        if line in grouped:
            grouped[line].append(item["sku"])

    seq = []

    while len(seq) < LEN:

        added = False

        for p in pattern:

            if grouped[p]:

                seq.append(grouped[p].pop(0))

                added = True

                if len(seq) >= LEN:
                    break

        if not added:
            break

    return seq


def build_chromosome(out_skus, out_times, out_weights, LEN):

    seq = []

    # copy lists (important)
    skus = out_skus.copy()
    times = out_times.copy()
    weights = out_weights.copy()

    while skus and len(seq) < LEN:

        # take first item
        base_sku = skus[0]
        base_time = times[0]

        total_weight = 0
        group_indices = []

        # -----------------------------
        # FIND VALID GROUP
        # -----------------------------
        for idx in range(len(skus)):

            if skus[idx] != base_sku:
                continue

            # check time constraint
            if abs(times[idx] - base_time) > 10:
                continue

            # check weight constraint
            if total_weight + weights[idx] > 40:
                continue

            group_indices.append(idx)
            total_weight += weights[idx]

        # -----------------------------
        # ADD GROUP TO SEQUENCE
        # -----------------------------
        for idx in group_indices:
            if len(seq) < LEN:
                seq.append(skus[idx])

        # -----------------------------
        # REMOVE USED ITEMS (reverse order!)
        # -----------------------------
        for idx in sorted(group_indices, reverse=True):
            skus.pop(idx)
            times.pop(idx)
            weights.pop(idx)

        # -----------------------------
        # SAFETY: if nothing grouped
        # -----------------------------
        if not group_indices:
            seq.append(skus.pop(0))
            times.pop(0)
            weights.pop(0)

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

            if total_weight + w > 40:
                repaired.append(random.choice(seq))

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


def zigzag_score(lines, pattern):

    score = 0

    expected = []

    while len(expected) < len(lines):
        expected.extend(pattern)

    expected = expected[:len(lines)]

    for i in range(len(lines)):

        if lines[i].lower() == expected[i]:
            score += 1
        else:
            score -= 1

    return score


def soft_order_score(seq, weight_map, max_weight=40):

    """
    Nonlinear grouping reward.

    Example:
    A A A → 1² + 2² + 3²
    """

    if not seq:
        return 0

    total_score = 0

    run_length = 1

    # initial weight
    first_weights = weight_map.get(seq[0], [0])

    if isinstance(first_weights, list):
        total_weight = sum(first_weights) / len(first_weights)
    else:
        total_weight = first_weights

    # first tire
    total_score += run_length ** 2

    for i in range(1, len(seq)):

        weights_list = weight_map.get(seq[i], [0])

        if isinstance(weights_list, list):
            w = sum(weights_list) / len(weights_list)
        else:
            w = weights_list

        # continue grouping
        if seq[i] == seq[i-1] and (total_weight + w) <= max_weight:

            run_length += 1
            total_weight += w

        # reset group
        else:

            run_length = 1
            total_weight = w

        # nonlinear reward
        total_score += run_length ** 2

    return total_score


def normalize(value, min_val, max_val):

    if max_val - min_val == 0:
        return 0

    return (value - min_val) / (max_val - min_val)


def bottleneck_score(result, seq, weight_map):

    util = result.get("util", {"soft":0,"oven":0,"heel":0,"tread":0})
    bottleneck = max(util, key=util.get)

    score = 0

    # -------------------------
    # SOFT BOTTLENECK
    # -------------------------
    if bottleneck == "soft":

        # reward grouping (reuse your soft score logic)
        score = soft_order_score(seq, weight_map)

    # -------------------------
    # OVEN BOTTLENECK
    # -------------------------
    elif bottleneck == "oven":

        # reward sequence matching (smooth flow)
        score = 1 / (1 + result["blocking"])

    # -------------------------
    # HEEL / TREAD BOTTLENECK
    # -------------------------
    else:

        score = 1 / (1 + result["setup"])

    return score


def tournament(pop, out_seq, k=3):
    candidates = random.sample(pop, k)
    return max(candidates, key=lambda x: fitness(x, out_seq))

def get_perturb_rate(gen, GEN):

    # start high → decrease over time
    return 0.6 - (0.3 * (gen / GEN))


def get_mutation_rate(gen, GEN):

    return 0.3 - (0.2 * (gen / GEN))


def population_diversity(pop):

    unique = set(tuple(p) for p in pop)

    return len(unique) / len(pop)