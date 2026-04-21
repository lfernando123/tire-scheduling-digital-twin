import simpy
import config
from simulation.factory import Factory
from simulation.kpi import KPI
from simulation.process import tire_process


def job_generator(env, sequence, factory, kpi):

    i = 0

    while True:

        sku = sequence[i % len(sequence)]

        env.process(tire_process(env, sku, factory, kpi))

        i += 1

        # control release rate (VERY IMPORTANT)
        yield env.timeout(1)   # 1 minute between jobs


def run_simulation(sequence):

    env = simpy.Environment()
    factory = Factory(env)
    kpi = KPI()

    # start job generator
    env.process(job_generator(env, sequence, factory, kpi))

    # run simulation
    env.run(until=config.SIM_TIME)

    return {
        "throughput": kpi.throughput,
        "setup": kpi.setup,
        "starvation": kpi.starvation,
        "blocking": kpi.blocking
    }