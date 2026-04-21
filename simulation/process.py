import random
import config
from data.recipes import recipes
from data.setup_matrix import setup_matrix
from simulation import kpi

def tri(t):
    return random.triangular(*t)

def tire_process(env, sku, factory, kpi):

    r = recipes[sku]

    # SETUP
    if factory.prev_sku:
        s = setup_matrix[(factory.prev_sku,sku)]
        kpi.setup += s
        yield env.timeout(s)

    factory.prev_sku = sku

    # HEEL
    with factory.heel.request() as req:
        yield req

        wait_time = env.now - wait_start
        kpi.blocking += wait_time

        if factory.heel_comp < r["heel"]:
            yield env.timeout(5)
            factory.heel_comp = config.MAX_COMPOUND

        factory.heel_comp -= r["heel"]

        yield env.timeout(tri(config.HEEL_TIME))

    # SOFT
    if r["layers"] == 3:
        with factory.soft.request() as req:
            yield req

            if factory.soft_comp < r["soft"]:
                yield env.timeout(5)
                factory.soft_comp = config.MAX_COMPOUND

            factory.soft_comp -= r["soft"]

            yield env.timeout(tri(config.SOFT_TIME))

    # TREAD
    with (factory.gray if r["color"]=="gray" else factory.black).request() as req:
        yield req
        yield env.timeout(tri(config.TREAD_TIME))

    # HOIST
    with factory.hoist.request() as req:
        yield req
        yield env.timeout(random.uniform(*config.HOIST_TIME))

    wait_start = env.now

    # OVEN
    with factory.ovens.request() as req:
        yield req
        yield env.timeout(max(random.normalvariate(*config.CURING_TIME[:2]),40))

    wait_time = env.now - wait_start

    kpi.starvation += wait_time

    kpi.throughput += 1
    factory.prev_sku = sku