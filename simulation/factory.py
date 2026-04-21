import simpy
import config

class Factory:

    def __init__(self,env):
        self.env = env

        self.heel = simpy.Resource(env,1)
        self.soft = simpy.Resource(env,1)
        self.gray = simpy.Resource(env,1)
        self.black = simpy.Resource(env,1)

        self.hoist = simpy.Resource(env,config.HOISTS)
        self.ovens = simpy.Resource(env,config.OVENS)

        self.heel_comp = config.MAX_COMPOUND
        self.soft_comp = config.MAX_COMPOUND

        self.prev_sku = None