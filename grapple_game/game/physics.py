# Physics module
# Contains: Gravity, collision detection, grapple rope physics

import math
import pygame

# Physics constants
GRAVITY = 1400  # pixels per second squared
TERMINAL_VELOCITY = 800
JUMP_VELOCITY = -500
COYOTE_TIME = 0.1  # seconds after leaving ground you can still jump
JUMP_BUFFER_TIME = 0.1  # seconds before landing that jump input is remembered

# Grapple constants
GRAPPLE_SPEED = 1200  # How fast the hook travels
GRAPPLE_MAX_LENGTH = 400  # Maximum grapple distance
ROPE_GRAVITY = 1200  # Gravity while swinging
ROPE_DAMPING = 0.995  # Slight damping on swing
SWING_BOOST = 200  # Extra horizontal speed when releasing


def apply_gravity(velocity_y, dt):
    """Apply gravity to vertical velocity"""
    velocity_y += GRAVITY * dt
    return min(velocity_y, TERMINAL_VELOCITY)


def check_collision(rect, collision_rects):
    """Check if rect collides with any collision rects, return first collision"""
    for col_rect in collision_rects:
        if rect.colliderect(col_rect):
            return col_rect
    return None


def get_all_collisions(rect, collision_rects):
    """Get all collision rects that overlap with rect"""
    results = []
    for col_rect in collision_rects:
        if rect.colliderect(col_rect):
            results.append(col_rect)
    return results


def raycast(start, end, room_manager, steps=50):
    """
    Cast a ray from start to end, return first collision point and tile.
    Returns (hit_point, hit_tile) or (None, None) if no hit.
    """
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    
    for i in range(1, steps + 1):
        t = i / steps
        x = start[0] + dx * t
        y = start[1] + dy * t
        
        # Check collision at this point
        point_rect = pygame.Rect(x - 2, y - 2, 4, 4)
        collisions = room_manager.get_collisions(point_rect)
        
        if collisions:
            return (x, y), collisions[0]
    
    return None, None


class GrappleHook:
    """
    Grappling hook with rope physics.
    States: inactive, firing, attached, retracting
    """
    
    def __init__(self):
        self.state = "inactive"
        
        # Hook position (tip of the grapple)
        self.hook_x = 0
        self.hook_y = 0
        
        # Anchor point (where hook attached to wall)
        self.anchor_x = 0
        self.anchor_y = 0
        
        # Firing direction
        self.fire_dx = 0
        self.fire_dy = 0
        
        # Rope properties
        self.rope_length = 0
        self.max_rope_length = GRAPPLE_MAX_LENGTH
        
        # Swing physics (for attached state)
        self.angle = 0  # Angle from anchor (0 = straight down)
        self.angular_velocity = 0
        self.current_length = 0  # Can shorten rope while attached
        
        # Visual
        self.rope_color = (150, 120, 80)
        self.hook_color = (200, 180, 140)
    
    def fire(self, start_x, start_y, target_x, target_y):
        """Fire grapple towards target position"""
        if self.state != "inactive":
            return
        
        self.state = "firing"
        self.hook_x = start_x
        self.hook_y = start_y
        
        # Calculate direction
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist > 0:
            self.fire_dx = dx / dist
            self.fire_dy = dy / dist
        else:
            self.fire_dx = 0
            self.fire_dy = -1  # Default: fire upward
        
        self.rope_length = 0
    
    def release(self):
        """Release the grapple"""
        self.state = "inactive"
        self.angular_velocity = 0
    
    def update(self, dt, player, room_manager):
        """Update grapple state and physics"""
        
        if self.state == "firing":
            self._update_firing(dt, player, room_manager)
        
        elif self.state == "attached":
            self._update_attached(dt, player, room_manager)
    
    def _update_firing(self, dt, player, room_manager):
        """Update hook while it's traveling"""
        # Move hook
        move_dist = GRAPPLE_SPEED * dt
        self.hook_x += self.fire_dx * move_dist
        self.hook_y += self.fire_dy * move_dist
        self.rope_length += move_dist
        
        # Check if hook hit something
        hook_rect = pygame.Rect(self.hook_x - 4, self.hook_y - 4, 8, 8)
        collisions = room_manager.get_collisions(hook_rect)
        
        if collisions:
            # Attached to wall
            self.state = "attached"
            self.anchor_x = self.hook_x
            self.anchor_y = self.hook_y
            
            # Calculate initial angle and length from player to anchor
            dx = player.x + player.width / 2 - self.anchor_x
            dy = player.y + player.height / 2 - self.anchor_y
            self.current_length = math.sqrt(dx * dx + dy * dy)
            self.angle = math.atan2(dx, dy)  # atan2(x, y) for angle from vertical
            
            # Convert player's current velocity to angular velocity
            # Project velocity onto tangent direction
            tangent_x = math.cos(self.angle)
            tangent_y = -math.sin(self.angle)
            tangent_vel = player.vx * tangent_x + player.vy * tangent_y
            
            if self.current_length > 0:
                self.angular_velocity = tangent_vel / self.current_length
        
        elif self.rope_length > self.max_rope_length:
            # Missed - retract
            self.state = "inactive"
    
    def _update_attached(self, dt, player, room_manager):
        """Update swing physics while attached"""
        # Pendulum physics
        # Angular acceleration = -g/L * sin(angle)
        gravity_accel = -ROPE_GRAVITY / max(self.current_length, 1) * math.sin(self.angle)
        
        self.angular_velocity += gravity_accel * dt
        self.angular_velocity *= ROPE_DAMPING  # Small damping
        self.angle += self.angular_velocity * dt
        
        # Calculate player position from angle
        new_x = self.anchor_x + math.sin(self.angle) * self.current_length - player.width / 2
        new_y = self.anchor_y + math.cos(self.angle) * self.current_length - player.height / 2
        
        # Check for collision at new position
        test_rect = pygame.Rect(new_x, new_y, player.width, player.height)
        collisions = room_manager.get_collisions(test_rect)
        
        if collisions:
            # Hit a wall while swinging - stop angular motion in that direction
            self.angular_velocity *= -0.3  # Bounce back slightly
        else:
            player.x = new_x
            player.y = new_y
        
        # Update player velocity based on swing (for when they release)
        player.vx = self.angular_velocity * self.current_length * math.cos(self.angle)
        player.vy = -self.angular_velocity * self.current_length * math.sin(self.angle)
    
    def shorten_rope(self, amount):
        """Shorten the rope (climb up)"""
        if self.state == "attached":
            self.current_length = max(50, self.current_length - amount)
    
    def lengthen_rope(self, amount):
        """Lengthen the rope (drop down)"""
        if self.state == "attached":
            self.current_length = min(self.max_rope_length, self.current_length + amount)
    
    def get_release_velocity(self):
        """Get velocity boost when releasing grapple"""
        if self.state != "attached":
            return 0, 0
        
        # Calculate current swing velocity
        vx = self.angular_velocity * self.current_length * math.cos(self.angle)
        vy = -self.angular_velocity * self.current_length * math.sin(self.angle)
        
        # Add a small boost in the direction of motion
        speed = math.sqrt(vx * vx + vy * vy)
        if speed > 0:
            vx += (vx / speed) * SWING_BOOST * 0.5
            vy += (vy / speed) * SWING_BOOST * 0.5
        
        return vx, vy
    
    def draw(self, surface, camera, player):
        """Draw the grapple rope and hook"""
        if self.state == "inactive":
            return
        
        # Player center (rope attachment point)
        player_cx = player.x + player.width / 2
        player_cy = player.y + player.height / 2
        
        if self.state == "firing":
            # Draw rope from player to hook
            start = camera.apply((player_cx, player_cy))
            end = camera.apply((self.hook_x, self.hook_y))
            pygame.draw.line(surface, self.rope_color, start, end, 2)
            
            # Draw hook
            hook_screen = camera.apply((self.hook_x, self.hook_y))
            pygame.draw.circle(surface, self.hook_color, (int(hook_screen[0]), int(hook_screen[1])), 5)
        
        elif self.state == "attached":
            # Draw rope from player to anchor
            start = camera.apply((player_cx, player_cy))
            end = camera.apply((self.anchor_x, self.anchor_y))
            pygame.draw.line(surface, self.rope_color, start, end, 3)
            
            # Draw anchor point
            anchor_screen = camera.apply((self.anchor_x, self.anchor_y))
            pygame.draw.circle(surface, self.hook_color, (int(anchor_screen[0]), int(anchor_screen[1])), 6)


class PhysicsBody:
    """Mixin class that can be added to entities for physics"""
    
    def __init__(self):
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.coyote_timer = 0  # Time since leaving ground
        self.jump_buffer_timer = 0  # Time since jump was pressed
        self.was_on_ground = False
    
    def apply_physics(self, dt, room_manager):
        """Apply gravity and update coyote time"""
        # Apply gravity if not on ground
        if not self.on_ground:
            self.vy = apply_gravity(self.vy, dt)
        
        # Update coyote timer
        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
        else:
            self.coyote_timer -= dt
        
        # Update jump buffer
        self.jump_buffer_timer -= dt
    
    def can_jump(self):
        """Check if entity can jump (on ground or in coyote time)"""
        return self.on_ground or self.coyote_timer > 0
    
    def buffer_jump(self):
        """Buffer a jump input"""
        self.jump_buffer_timer = JUMP_BUFFER_TIME
    
    def try_jump(self):
        """Attempt to jump, returns True if successful"""
        if self.can_jump():
            self.vy = JUMP_VELOCITY
            self.on_ground = False
            self.coyote_timer = 0
            return True
        return False
    
    def check_buffered_jump(self):
        """Check if there's a buffered jump and execute it"""
        if self.jump_buffer_timer > 0 and self.on_ground:
            self.jump_buffer_timer = 0
            return self.try_jump()
        return False