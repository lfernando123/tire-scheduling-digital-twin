class Monorail:

    def __init__(self,size=6):
        self.size = size
        self.positions = [None]*size

    def move(self):
        last = self.positions[-1]
        for i in range(self.size-1,0,-1):
            if self.positions[i] is None:
                self.positions[i] = self.positions[i-1]
                self.positions[i-1] = None
        if self.positions[0] is None:
            self.positions[0] = last