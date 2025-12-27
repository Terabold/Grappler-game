"""
Enemy system - Basic patrol and chase enemies
"""
import pygame
import math
from .room import TILE_SOLID, TILE_SPIKE

class Enemy:
    """Base enemy class - patrols back and forth, takes damage."""
    
    def __init__(self, x, y, enemy_type="walker"):
        self.x = float(x)
        self.y = float(y)
        self.width = 28
        self.height = 28
        
        self.vx = 0.0
        self.vy = 0.0
        
        self.enemy_type = enemy_type
        self.speed = 80
        self.direction = 1  # 1 = right, -1 = left
        
        # Combat
        self.health = 30
        self.max_health = 30
        self.damage = 20
        self.knockback = 300
        
        # State
        self.alive = True
        self.on_ground = False
        self.hit_timer = 0.0  # Flash when hit
        self.attack_cooldown = 0.0
        
        # AI
        self.patrol_timer = 0.0
        self.patrol_duration = 2.0
        self.chase_range = 200
        self.chase_speed = 120
        self.chasing = False
    
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)
    
    @property
    def center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    def take_damage(self, amount, knockback_x=0, knockback_y=0):
        """Take damage and apply knockback."""
        if not self.alive:
            return False
        
        self.health -= amount
        self.hit_timer = 0.15
        self.vx = knockback_x
        self.vy = knockback_y - 150
        
        if self.health <= 0:
            self.alive = False
        
        return True
    
    def update(self, dt, room_manager, player):
        """Update enemy AI and physics."""
        if not self.alive:
            return
        
        self.hit_timer = max(0, self.hit_timer - dt)
        self.attack_cooldown = max(0, self.attack_cooldown - dt)
        
        # Check if player is in range
        px, py = player.center
        ex, ey = self.center
        dist = math.sqrt((px - ex) ** 2 + (py - ey) ** 2)
        
        self.chasing = dist < self.chase_range and player.health > 0
        
        if self.chasing:
            # Chase player
            if px > ex + 10:
                self.direction = 1
            elif px < ex - 10:
                self.direction = -1
            self.vx = self.direction * self.chase_speed
        else:
            # Patrol
            self.patrol_timer += dt
            if self.patrol_timer >= self.patrol_duration:
                self.patrol_timer = 0
                self.direction *= -1
            self.vx = self.direction * self.speed
        
        # Apply gravity
        self.vy = min(self.vy + 1200 * dt, 600)
        
        # Move with collision
        self._move_with_collision(dt, room_manager)
        
        # Check collision with player
        if self.attack_cooldown <= 0 and self.rect.colliderect(player.rect):
            if player.take_damage(self.damage, self.direction * self.knockback, 0):
                self.attack_cooldown = 1.0
    
    def _move_with_collision(self, dt, room_manager):
        """Simple collision for enemies."""
        # Move X
        self.x += self.vx * dt
        rect = self.rect
        
        for tile in room_manager.get_solid_collisions(rect):
            # Handle both Tile objects and plain Rects
            tile_rect = tile.rect if hasattr(tile, 'rect') else tile
            if self.vx > 0:
                self.x = tile_rect.left - self.width
                self.direction = -1
            elif self.vx < 0:
                self.x = tile_rect.right
                self.direction = 1
            self.vx = 0
        
        # Move Y
        self.y += self.vy * dt
        rect = self.rect
        
        self.on_ground = False
        for tile in room_manager.get_solid_collisions(rect):
            tile_rect = tile.rect if hasattr(tile, 'rect') else tile
            if self.vy >= 0:
                self.y = tile_rect.top - self.height
                self.vy = 0
                self.on_ground = True
            elif self.vy < 0:
                self.y = tile_rect.bottom
                self.vy = 0
        
        # Check for edge and turn around
        if self.on_ground and not self.chasing:
            test_x = self.x + (self.width if self.direction > 0 else -4)
            test_rect = pygame.Rect(int(test_x), int(self.y + self.height), 4, 4)
            
            ground_ahead = False
            for tile in room_manager.get_solid_collisions(test_rect):
                ground_ahead = True
                break
            
            if not ground_ahead:
                self.direction *= -1
    
    def draw(self, surface, camera):
        """Draw enemy."""
        if not self.alive:
            return
        
        screen_pos = camera.apply(self.center)
        
        # Body
        color = (255, 100, 100) if self.hit_timer > 0 else (180, 60, 60)
        rect = pygame.Rect(
            screen_pos[0] - self.width // 2,
            screen_pos[1] - self.height // 2,
            self.width,
            self.height
        )
        pygame.draw.rect(surface, color, rect)
        
        # Eyes
        eye_y = screen_pos[1] - 4
        eye_offset = 4 * self.direction
        pygame.draw.circle(surface, (255, 255, 255), (int(screen_pos[0] + eye_offset - 3), int(eye_y)), 3)
        pygame.draw.circle(surface, (255, 255, 255), (int(screen_pos[0] + eye_offset + 3), int(eye_y)), 3)
        pygame.draw.circle(surface, (0, 0, 0), (int(screen_pos[0] + eye_offset - 3 + self.direction), int(eye_y)), 2)
        pygame.draw.circle(surface, (0, 0, 0), (int(screen_pos[0] + eye_offset + 3 + self.direction), int(eye_y)), 2)
        
        # Health bar (if damaged)
        if self.health < self.max_health:
            bar_width = 30
            bar_height = 4
            bar_x = screen_pos[0] - bar_width // 2
            bar_y = screen_pos[1] - self.height // 2 - 8
            
            # Background
            pygame.draw.rect(surface, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
            # Health
            health_width = int(bar_width * (self.health / self.max_health))
            pygame.draw.rect(surface, (200, 60, 60), (bar_x, bar_y, health_width, bar_height))


class EnemyManager:
    """Manages all enemies in the current level."""
    
    def __init__(self):
        self.enemies = []
        self.spawn_points = []  # Store original spawn points for respawn
    
    def add_enemy(self, x, y, enemy_type="walker"):
        """Add an enemy."""
        enemy = Enemy(x, y, enemy_type)
        self.enemies.append(enemy)
        self.spawn_points.append((x, y, enemy_type))
    
    def reset(self):
        """Reset all enemies to original positions."""
        self.enemies.clear()
        for x, y, enemy_type in self.spawn_points:
            self.enemies.append(Enemy(x, y, enemy_type))
    
    def clear(self):
        """Remove all enemies."""
        self.enemies.clear()
        self.spawn_points.clear()
    
    def update(self, dt, room_manager, player):
        """Update all enemies."""
        for enemy in self.enemies:
            enemy.update(dt, room_manager, player)
    
    def draw(self, surface, camera):
        """Draw all enemies."""
        for enemy in self.enemies:
            enemy.draw(surface, camera)
    
    def check_sword_hit(self, attack_rect, damage, knockback_dir):
        """Check if sword attack hits any enemy."""
        hits = 0
        for enemy in self.enemies:
            if enemy.alive and attack_rect.colliderect(enemy.rect):
                enemy.take_damage(damage, knockback_dir * 200, 0)
                hits += 1
        return hits
