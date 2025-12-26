# Enemies module - TODO
# Will contain:
# - Base Enemy class
# - Enemy types: Walker, Shooter, Charger
# - Enemy AI
# - Death/damage handling

class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.health = 1
        self.alive = True
    
    def update(self, dt, player):
        pass
    
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.die()
    
    def die(self):
        self.alive = False
    
    def draw(self, surface, camera):
        pass


class Walker(Enemy):
    """Simple enemy that walks back and forth"""
    pass


class Shooter(Enemy):
    """Enemy that shoots projectiles at player"""
    pass


class Charger(Enemy):
    """Enemy that charges at player when in range"""
    pass
