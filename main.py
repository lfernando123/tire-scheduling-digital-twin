import simpy
from scheduler.rolling_scheduler import scheduler

env = simpy.Environment()

env.process(scheduler(env))

env.run(until=30)