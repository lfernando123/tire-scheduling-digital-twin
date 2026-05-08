from locale import normalize

from optimization.ga import GA, LEN
from simulation.oven_system import OvenSystem
from simulation.simulation_runner import run_simulation
from data.setup_matrix import setup_matrix
from scheduler.heuristic_scheduler import heuristic_scheduler
from optimization.ga import GA
import matplotlib.pyplot as plt


def print_setup_matrix(SKUS):

    print("\n=== SETUP MATRIX ===")

    header = "     " + " ".join([f"{s:>4}" for s in SKUS])
    print(header)

    for i in SKUS:
        row = f"{i:>4} "
        for j in SKUS:
            row += f"{setup_matrix[(i,j)]:>4} "
        print(row)

def plot_comparison(heur_kpi, ga_kpi):

    metrics = ["throughput", "setup", "blocking", "starvation"]

    heur_values = [heur_kpi[m] for m in metrics]
    ga_values = [ga_kpi[m] for m in metrics]

    x = range(len(metrics))

    width = 0.35

    plt.figure()

    plt.bar([i - width/2 for i in x], heur_values, width=width, label="Heuristic")
    plt.bar([i + width/2 for i in x], ga_values, width=width, label="GA")

    plt.xticks(x, metrics)
    plt.xlabel("Metrics")
    plt.ylabel("Values")
    plt.title("GA vs Heuristic Comparison")

    plt.legend()

    plt.tight_layout()
    plt.show()


def scheduler(env):

    oven_system = OvenSystem(90)

    out_seq = oven_system.get_out_sequence(30)

    while True:

        # update oven state
        oven_system.update(30)

        # get demand
        demand = oven_system.get_demand(30)

        out_seq = oven_system.get_out_sequence(30)

        # Heuristic
        heur_seq = heuristic_scheduler(out_seq, LEN=LEN)

        # run GA
        best_seq = GA(out_seq)

        # ==========================
        # 🔥 PRINT EVERYTHING HERE
        # ==========================
        print("\n==============================")
        print("TIME:", env.now)
        print("==============================")

        print("\n=== CURING OUT SEQUENCE ===")
        for item in out_seq:
            print(f"Time: {round(item['time'],2)} min → SKU {item['sku']} (Oven {item['oven']})")

        # # 1. Oven demand
        # print("\n=== OVEN DEMAND ===")
        # for k,v in demand.items():
        #     print(f"{k}: {v}")

        # # 2. Setup matrix
        # if demand:
        #     print_setup_matrix(list(demand.keys()))

        # 3. Best sequence
        print("\n=== GA BEST SEQUENCE ===")
        print(best_seq)

        # 3. Best sequence
        print("\n=== HEURISTIC BEST SEQUENCE ===")
        print(heur_seq)

        # 4. Demand vs Production
        print("\n=== DEMAND vs PRODUCTION ===")
        for sku in demand:
            produced = best_seq.count(sku)
            print(f"{sku}: Demand={demand[sku]}, Produced={produced}")

        # 5. GA KPI results
        result = run_simulation(best_seq)

        heur_kpi = run_simulation(heur_seq)

        print("\n=== GA KPI RESULTS ===")
        print(result)

        print("\n=== HEURISTIC KPI RESULTS ===")
        print(heur_kpi)

        h_norm, g_norm = normalize_pair(heur_kpi, result)
        plot_comparison(h_norm, g_norm)

        # next cycle
        yield env.timeout(30)


def normalize_pair(heur_kpi, ga_kpi):

    norm_heur = {}
    norm_ga = {}

    for key in heur_kpi:

        max_val = max(heur_kpi[key], ga_kpi[key]) + 1e-6

        norm_heur[key] = heur_kpi[key] / max_val
        norm_ga[key] = ga_kpi[key] / max_val

    return norm_heur, norm_ga