# Physics module - Clean, optimized, bug-free
import math
import pygame

# =============================================================================
# PHYSICS CONSTANTS - Balanced for good feel
# =============================================================================

GRAVITY = 1800
TERMINAL_VELOCITY = 750
JUMP_VELOCITY = -520
WALL_SLIDE_SPEED = 120
WALL_JUMP_VELOCITY_X = 380
WALL_JUMP_VELOCITY_Y = -480

COYOTE_TIME = 0.1
JUMP_BUFFER_TIME = 0.12

# =============================================================================
# ROLL/DASH CONSTANTS
# =============================================================================

ROLL_SPEED = 550
ROLL_DURATION = 0.25
ROLL_COOLDOWN = 0.4
ROLL_IFRAMES = 0.2  # Invincibility during roll

SPRINT_MULTIPLIER = 1.45

# =============================================================================
# GRAPPLE CONSTANTS
# =============================================================================

GRAPPLE_FIRE_SPEED = 2000
GRAPPLE_MAX_RANGE = 450
GRAPPLE_PULL_FORCE = 2800
GRAPPLE_PULL_MAX_SPEED = 900
GRAPPLE_MIN_PULL_DIST = 32
GRAPPLE_RELEASE_BOOST = 1.2
PREFERRED_ROPE_LENGTH = 180


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def apply_gravity(vy, dt):
    """Apply gravity, return new velocity capped at terminal velocity"""
    return min(vy + GRAVITY * dt, TERMINAL_VELOCITY)


def sign(x):
    """Return sign of x: -1, 0, or 1"""
    if x > 0:
        return 1
    elif x < 0:
        return -1
    return 0


def approach(current, target, amount):
    """Move current toward target by amount, don't overshoot"""
    if current < target:
        return min(current + amount, target)
    elif current > target:
        return max(current - amount, target)
    return target


def distance(x1, y1, x2, y2):
    """Distance between two points"""
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)


# =============================================================================
# GRAPPLE HOOK
# =============================================================================

class GrappleHook:
    """
    Pull-based grappling hook.
    States: inactive -> firing -> attached
    """
    
    __slots__ = (
        'state', 'hook_x', 'hook_y', 'anchor_x', 'anchor_y',
        'fire_dir_x', 'fire_dir_y', 'fire_distance',
        'mode', 'rope_length', 'angle', 'angular_velocity',
        '_pull_vx', '_pull_vy'
    )
    
    def __init__(self):
        self.state = "inactive"
        self.hook_x = 0.0
        self.hook_y = 0.0
        self.anchor_x = 0.0
        self.anchor_y = 0.0
        self.fire_dir_x = 0.0
        self.fire_dir_y = 0.0
        self.fire_distance = 0.0
        self.mode = "pull"
        self.rope_length = 0.0
        self.angle = 0.0
        self.angular_velocity = 0.0
        self._pull_vx = 0.0
        self._pull_vy = 0.0
    
    def fire(self, start_x, start_y, target_x, target_y):
        """Fire grapple toward target. Returns True if fired."""
        if self.state != "inactive":
            return False
        
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist < 20:
            return False
        
        self.state = "firing"
        self.hook_x = start_x
        self.hook_y = start_y
        self.fire_dir_x = dx / dist
        self.fire_dir_y = dy / dist
        self.fire_distance = 0.0
        self.mode = "pull"
        self._pull_vx = 0.0
        self._pull_vy = 0.0
        
        return True
    
    def release(self):
        """Release grapple, return velocity boost."""
        if self.state == "inactive":
            return 0.0, 0.0
        
        boost_vx = self._pull_vx * GRAPPLE_RELEASE_BOOST
        boost_vy = self._pull_vy * GRAPPLE_RELEASE_BOOST
        
        self.state = "inactive"
        self._pull_vx = 0.0
        self._pull_vy = 0.0
        
        return boost_vx, boost_vy
    
    def cancel(self):
        """Cancel grapple without boost."""
        self.state = "inactive"
        self._pull_vx = 0.0
        self._pull_vy = 0.0
    
    def set_mode(self, mode):
        """Set mode: 'pull' or 'swing'"""
        if mode in ("pull", "swing"):
            self.mode = mode
    
    def update(self, dt, player, room_manager):
        """Update grapple state."""
        if self.state == "firing":
            self._update_firing(dt, player, room_manager)
        elif self.state == "attached":
            if self.mode == "pull":
                self._update_pull(dt, player, room_manager)
            else:
                self._update_swing(dt, player, room_manager)
    
    def _update_firing(self, dt, player, room_manager):
        """Update hook while traveling with raycast collision to prevent tunneling."""
        total_move = GRAPPLE_FIRE_SPEED * dt
        
        # Step size (smaller than a tile to catch edges)
        step_size = 4.0
        
        distance_left = total_move
        current_x = self.hook_x
        current_y = self.hook_y
        
        while distance_left > 0:
            step = min(distance_left, step_size)
            
            # Advance potential position
            current_x += self.fire_dir_x * step
            current_y += self.fire_dir_y * step
            self.fire_distance += step
            
            # Check for hit at this step
            hook_rect = pygame.Rect(int(current_x) - 3, int(current_y) - 3, 6, 6)
            collisions = room_manager.get_collisions(hook_rect)
            
            valid_hit = False
            for tile in collisions:
                # tile_type: 1=solid, 3=grapple, 5=platform
                if tile.tile_type in (1, 3, 5):
                    valid_hit = True
                    break
            
            if valid_hit:
                # We hit something!
                self.state = "attached"
                self.hook_x = current_x
                self.hook_y = current_y
                self.anchor_x = self.hook_x
                self.anchor_y = self.hook_y
                
                px, py = player.center
                self.rope_length = distance(px, py, self.anchor_x, self.anchor_y)
                
                dx = px - self.anchor_x
                dy = py - self.anchor_y
                self.angle = math.atan2(dx, dy)
                
                # Convert velocity to angular
                if self.rope_length > 10:
                    tangent_x = math.cos(self.angle)
                    tangent_y = -math.sin(self.angle)
                    tangent_vel = player.vx * tangent_x + player.vy * tangent_y
                    self.angular_velocity = tangent_vel / self.rope_length
                else:
                    self.angular_velocity = 0.0
                
                self._pull_vx = player.vx
                self._pull_vy = player.vy
                return # Stop processing steps
                
            # If no hit, confirm this step and continue
            self.hook_x = current_x
            self.hook_y = current_y
            distance_left -= step
            
            # Max range check
            if self.fire_distance > GRAPPLE_MAX_RANGE:
                self.state = "inactive"
                return
    
    def _update_pull(self, dt, player, room_manager):
        """Pull player toward anchor."""
        px, py = player.center
        
        dx = self.anchor_x - px
        dy = self.anchor_y - py
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist < GRAPPLE_MIN_PULL_DIST:
            # Reached target
            boost_vx, boost_vy = self.release()
            player.vx = boost_vx
            player.vy = boost_vy
            return
        
        # Direction to anchor
        dir_x = dx / dist
        dir_y = dy / dist
        
        # Pull force (stronger when far)
        strength = GRAPPLE_PULL_FORCE
        if dist > PREFERRED_ROPE_LENGTH:
            strength *= 1.4
        
        # Apply force
        player.vx += dir_x * strength * dt
        player.vy += dir_y * strength * dt
        
        # Cap speed
        speed = math.sqrt(player.vx * player.vx + player.vy * player.vy)
        if speed > GRAPPLE_PULL_MAX_SPEED:
            scale = GRAPPLE_PULL_MAX_SPEED / speed
            player.vx *= scale
            player.vy *= scale
        
        self._pull_vx = player.vx
        self._pull_vy = player.vy
    
    def _update_swing(self, dt, player, room_manager):
        """Swing mode - pendulum physics."""
        gravity_accel = -GRAVITY / max(self.rope_length, 50) * math.sin(self.angle)
        
        self.angular_velocity += gravity_accel * dt
        self.angular_velocity *= 0.997
        self.angle += self.angular_velocity * dt
        
        new_x = self.anchor_x + math.sin(self.angle) * self.rope_length - player.width / 2
        new_y = self.anchor_y + math.cos(self.angle) * self.rope_length - player.height / 2
        
        test_rect = pygame.Rect(int(new_x), int(new_y), player.width, player.height)
        if not room_manager.get_collisions(test_rect):
            player.x = new_x
            player.y = new_y
        else:
            self.angular_velocity *= -0.4
        
        player.vx = self.angular_velocity * self.rope_length * math.cos(self.angle)
        player.vy = -self.angular_velocity * self.rope_length * math.sin(self.angle)
        
        self._pull_vx = player.vx
        self._pull_vy = player.vy
    
    def add_swing_force(self, direction, dt):
        """Add swing momentum."""
        if self.state == "attached" and self.mode == "swing":
            self.angular_velocity += direction * 4.0 * dt
    
    def shorten_rope(self, amount):
        """Climb up."""
        if self.state == "attached" and self.mode == "swing":
            self.rope_length = max(40, self.rope_length - amount)
    
    def lengthen_rope(self, amount):
        """Drop down."""
        if self.state == "attached" and self.mode == "swing":
            self.rope_length = min(GRAPPLE_MAX_RANGE, self.rope_length + amount)
    
    def draw(self, surface, camera, player):
        """Draw grapple."""
        if self.state == "inactive":
            return
        
        px, py = player.center
        start = camera.apply((px, py))
        
        if self.state == "firing":
            end = camera.apply((self.hook_x, self.hook_y))
            pygame.draw.line(surface, (180, 140, 80), start, end, 2)
            pygame.draw.circle(surface, (220, 200, 150), (int(end[0]), int(end[1])), 4)
        
        elif self.state == "attached":
            end = camera.apply((self.anchor_x, self.anchor_y))
            thickness = 3 if self.mode == "pull" else 2
            pygame.draw.line(surface, (180, 140, 80), start, end, thickness)
            pygame.draw.circle(surface, (255, 220, 100), (int(end[0]), int(end[1])), 5)


# =============================================================================
# COLLISION HELPERS
# =============================================================================

def check_wall(player_rect, direction, room_manager):
    """
    Check for wall collision (solid tiles only).
    Returns True if wall found.
    """
    margin = 3
    inset = 6
    
    if direction == "left":
        test_rect = pygame.Rect(
            player_rect.left - margin,
            player_rect.top + inset,
            margin,
            player_rect.height - inset * 2
        )
    else:
        test_rect = pygame.Rect(
            player_rect.right,
            player_rect.top + inset,
            margin,
            player_rect.height - inset * 2
        )
    
    # Only check solid collisions (not platforms)
    return len(room_manager.get_solid_collisions(test_rect)) > 0


def check_ground(player_rect, room_manager):
    """Check for ground below player - used to verify on_ground status."""
    # Check a thin rect just below the player's feet
    test_rect = pygame.Rect(
        player_rect.left + 2,
        player_rect.bottom,
        player_rect.width - 4,
        2
    )
    
    # Check tile collisions (get_solid_collisions only returns solid, not platforms)
    if room_manager.get_solid_collisions(test_rect):
        return True
    
    # Also check room floor
    if room_manager.current_room:
        bounds = room_manager.current_room.bounds
        if player_rect.bottom >= bounds.bottom - 2:
            return True
    
    return False