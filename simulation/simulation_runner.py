import simpy
import config
from simulation.factory import Factory
from simulation.kpi import KPI
from simulation.process import tire_process

def run_simulation(sequence):

    env = simpy.Environment()
    factory = Factory(env)
    kpi = KPI()

    while env.now < config.SIM_TIME:
        for sku in sequence:
            env.process(tire_process(env,sku,factory,kpi))

    env.run(until=config.SIM_TIME)

    return {
        "throughput":kpi.throughput,
        "setup":kpi.setup,
        "starvation":kpi.starvation,
        "blocking":kpi.blocking
    }