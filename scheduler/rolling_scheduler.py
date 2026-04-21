from optimization.ga import GA
from simulation.oven_system import OvenSystem
from simulation.simulation_runner import run_simulation
from data.setup_matrix import setup_matrix


def print_setup_matrix(SKUS):

    print("\n=== SETUP MATRIX ===")

    header = "     " + " ".join([f"{s:>4}" for s in SKUS])
    print(header)

    for i in SKUS:
        row = f"{i:>4} "
        for j in SKUS:
            row += f"{setup_matrix[(i,j)]:>4} "
        print(row)


def scheduler(env):

    oven_system = OvenSystem(45)

    out_seq = oven_system.get_out_sequence(30)

    while True:

        # update oven state
        oven_system.update(30)

        # get demand
        demand = oven_system.get_demand(30)

        out_seq = oven_system.get_out_sequence(30)

        # run GA
        best_seq = GA(demand, out_seq)

        # ==========================
        # 🔥 PRINT EVERYTHING HERE
        # ==========================
        print("\n==============================")
        print("TIME:", env.now)
        print("==============================")

        print("\n=== CURING OUT SEQUENCE ===")
        print(out_seq)

        # 1. Oven demand
        print("\n=== OVEN DEMAND ===")
        for k,v in demand.items():
            print(f"{k}: {v}")

        # 2. Setup matrix
        if demand:
            print_setup_matrix(list(demand.keys()))

        # 3. Best sequence
        print("\n=== BEST SEQUENCE ===")
        print(best_seq)

        # 4. Demand vs Production
        print("\n=== DEMAND vs PRODUCTION ===")
        for sku in demand:
            produced = best_seq.count(sku)
            print(f"{sku}: Demand={demand[sku]}, Produced={produced}")

        # 5. KPI results
        result = run_simulation(best_seq)

        print("\n=== KPI RESULTS ===")
        print(result)

        # next cycle
        yield env.timeout(30)