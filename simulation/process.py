import random
import config
from data.recipes import recipes
from data.setup_matrix import setup_matrix


def tri(t):
    return random.triangular(*t)


def tire_process(env, sku, factory, kpi):

    r = recipes[sku]

    # ----------------------
    # SETUP
    # ----------------------
    if factory.prev_sku:
        s = setup_matrix[(factory.prev_sku, sku)]
        kpi.setup += s
        yield env.timeout(s)

    factory.prev_sku = sku

    # ----------------------
    # HEEL (with blocking)
    # ----------------------
    req = factory.heel.request()
    wait_start = env.now

    yield req   # wait happens here

    wait_time = env.now - wait_start
    kpi.blocking += wait_time

    if factory.heel_comp < r["heel"]:
        yield env.timeout(5)
        factory.heel_comp = config.MAX_COMPOUND

    factory.heel_comp -= r["heel"]

    yield env.timeout(tri(config.HEEL_TIME))

    factory.heel.release(req)

    # ----------------------
    # SOFT
    # ----------------------
    if r["layers"] == 3:

        req = factory.soft.request()
        yield req

        if factory.soft_comp < r["soft"]:
            yield env.timeout(5)
            factory.soft_comp = config.MAX_COMPOUND

        factory.soft_comp -= r["soft"]

        yield env.timeout(tri(config.SOFT_TIME))

        factory.soft.release(req)

    # ----------------------
    # TREAD
    # ----------------------
    tread_machine = factory.gray if r["color"] == "gray" else factory.black

    req = tread_machine.request()
    yield req

    yield env.timeout(tri(config.TREAD_TIME))

    tread_machine.release(req)

    # ----------------------
    # HOIST
    # ----------------------
    req = factory.hoist.request()
    yield req

    yield env.timeout(random.uniform(*config.HOIST_TIME))

    factory.hoist.release(req)

    # ----------------------
    # OVEN (with starvation)
    # ----------------------
    req = factory.ovens.request()
    wait_start = env.now

    yield req   # waiting happens here

    wait_time = env.now - wait_start
    kpi.starvation += wait_time

    # curing time
    yield env.timeout(max(random.normalvariate(*config.CURING_TIME[:2]), 40))

    factory.ovens.release(req)

    # ----------------------
    # FINISH
    # ----------------------
    kpi.throughput += 1