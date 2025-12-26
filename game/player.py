import pygame
import math
from .physics import (
    GrappleHook, apply_gravity, GRAVITY, TERMINAL_VELOCITY,
    JUMP_VELOCITY, COYOTE_TIME, JUMP_BUFFER_TIME
)


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 28
        self.height = 28
        
        # Velocity
        self.vx = 0
        self.vy = 0
        
        # Movement parameters
        self.speed = 280  # Horizontal movement speed
        self.air_control = 0.7  # Reduced control in air
        self.friction = 0.85  # Ground friction when not moving
        self.air_friction = 0.95  # Air friction
        
        # Jump parameters
        self.jump_velocity = JUMP_VELOCITY
        self.on_ground = False
        self.coyote_timer = 0
        self.jump_buffer_timer = 0
        self.jump_held = False  # For variable jump height
        self.jump_cut_multiplier = 0.5  # Velocity multiplier when releasing jump early
        
        # Grapple
        self.grapple = GrappleHook()
        
        # Visual
        self.color = (100, 200, 100)
        self.grapple_color = (100, 150, 200)
        
        # State
        self.frozen = False
        self.facing_right = True
        
        # Transition slide
        self.transition_slide = 20
        self.transition_dir = (0, 0)
        self.transition_slid = 0
    
    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    @property
    def center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    def start_transition(self, direction):
        """Called when room transition starts"""
        self.frozen = True
        self.transition_slid = 0
        self.grapple.release()  # Release grapple on room transition
        
        if direction == "right":
            self.transition_dir = (1, 0)
        elif direction == "left":
            self.transition_dir = (-1, 0)
        elif direction == "down":
            self.transition_dir = (0, 1)
        elif direction == "up":
            self.transition_dir = (0, -1)
        else:
            self.transition_dir = (0, 0)
    
    def end_transition(self):
        """Called when room transition ends"""
        self.frozen = False
        self.transition_dir = (0, 0)
    
    def update(self, dt, room_manager, controls):
        if self.frozen:
            self._update_transition(dt)
            return
        
        keys = pygame.key.get_pressed()
        mouse_buttons = pygame.mouse.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        
        # Update grapple
        self.grapple.update(dt, self, room_manager)
        
        if self.grapple.state == "attached":
            # While grappling, handle rope controls
            self._update_grappling(dt, keys, controls, room_manager)
        else:
            # Normal movement
            self._update_normal(dt, keys, controls, room_manager)
        
        # Handle grapple input (fire/release)
        self._handle_grapple_input(keys, mouse_buttons, mouse_pos, controls, room_manager)
    
    def _update_transition(self, dt):
        """Slide into new room during transition"""
        if self.transition_slid < self.transition_slide:
            slide_speed = 150
            move = slide_speed * dt
            self.x += self.transition_dir[0] * move
            self.y += self.transition_dir[1] * move
            self.transition_slid += move
    
    def _update_normal(self, dt, keys, controls, room_manager):
        """Normal physics-based movement"""
        # Horizontal input
        move_input = 0
        if keys[controls["left"]]:
            move_input = -1
            self.facing_right = False
        if keys[controls["right"]]:
            move_input = 1
            self.facing_right = True
        
        # Apply horizontal movement
        if self.on_ground:
            if move_input != 0:
                self.vx = move_input * self.speed
            else:
                self.vx *= self.friction
        else:
            # Air control (less responsive)
            if move_input != 0:
                target_vx = move_input * self.speed
                self.vx += (target_vx - self.vx) * self.air_control * dt * 10
            else:
                self.vx *= self.air_friction
        
        # Clamp tiny velocities to zero
        if abs(self.vx) < 1:
            self.vx = 0
        
        # Apply gravity
        self.vy = apply_gravity(self.vy, dt)
        
        # Update coyote time
        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
        else:
            self.coyote_timer = max(0, self.coyote_timer - dt)
        
        # Update jump buffer
        self.jump_buffer_timer = max(0, self.jump_buffer_timer - dt)
        
        # Jump input
        if keys[controls["jump"]]:
            if not self.jump_held:
                # Fresh press
                self.jump_held = True
                if self._can_jump():
                    self._do_jump()
                else:
                    # Buffer the jump
                    self.jump_buffer_timer = JUMP_BUFFER_TIME
        else:
            # Jump released - cut velocity for variable height
            if self.jump_held and self.vy < 0:
                self.vy *= self.jump_cut_multiplier
            self.jump_held = False
        
        # Check buffered jump when landing
        if self.on_ground and self.jump_buffer_timer > 0:
            self._do_jump()
            self.jump_buffer_timer = 0
        
        # Move with collision
        self._move_with_collision(dt, room_manager)
    
    def _update_grappling(self, dt, keys, controls, room_manager):
        """Update while attached to grapple"""
        # Rope length control
        if keys[controls["up"]]:
            self.grapple.shorten_rope(200 * dt)
        if keys[controls["down"]]:
            self.grapple.lengthen_rope(200 * dt)
        
        # Swing input - add angular momentum
        if keys[controls["left"]]:
            self.grapple.angular_velocity -= 3 * dt
        if keys[controls["right"]]:
            self.grapple.angular_velocity += 3 * dt
    
    def _handle_grapple_input(self, keys, mouse_buttons, mouse_pos, controls, room_manager):
        """Handle grapple fire/release input"""
        grapple_key = controls.get("grapple", pygame.K_LSHIFT)
        
        # Can use either grapple key or right mouse button
        grapple_pressed = keys[grapple_key] if isinstance(grapple_key, int) else False
        
        if grapple_pressed or mouse_buttons[2]:  # Right click
            if self.grapple.state == "inactive":
                # Fire grapple towards mouse
                # Need to convert screen mouse pos to world pos
                # For now, fire in facing direction at 45 degrees up
                cx, cy = self.center
                if mouse_buttons[2]:
                    # TODO: Convert mouse_pos through camera
                    # For now, estimate based on facing direction
                    target_x = cx + (200 if self.facing_right else -200)
                    target_y = cy - 150
                else:
                    target_x = cx + (200 if self.facing_right else -200)
                    target_y = cy - 150
                
                self.grapple.fire(cx, cy, target_x, target_y)
        else:
            # Released grapple key
            if self.grapple.state == "attached":
                # Get velocity boost from swing
                boost_vx, boost_vy = self.grapple.get_release_velocity()
                self.vx = boost_vx
                self.vy = boost_vy
                self.grapple.release()
    
    def fire_grapple_at(self, target_x, target_y):
        """Fire grapple at specific world position (called from game with camera conversion)"""
        if self.grapple.state == "inactive":
            cx, cy = self.center
            self.grapple.fire(cx, cy, target_x, target_y)
    
    def _can_jump(self):
        """Check if player can jump"""
        return self.on_ground or self.coyote_timer > 0
    
    def _do_jump(self):
        """Execute a jump"""
        self.vy = self.jump_velocity
        self.on_ground = False
        self.coyote_timer = 0
    
    def _move_with_collision(self, dt, room_manager):
        """Move with collision detection and resolution"""
        # Store if we were on ground
        was_on_ground = self.on_ground
        self.on_ground = False
        
        # Move X
        self.x += self.vx * dt
        for col in room_manager.get_collisions(self.rect):
            if self.vx > 0:
                self.x = col.left - self.width
            elif self.vx < 0:
                self.x = col.right
            self.vx = 0
        
        # Room edge collision X - only clamp if no adjacent room
        if room_manager.current_room:
            bounds = room_manager.current_room.bounds
            if self.x < bounds.left:
                if not self._has_adjacent_room(room_manager, "left"):
                    self.x = bounds.left
                    self.vx = 0
            if self.x + self.width > bounds.right:
                if not self._has_adjacent_room(room_manager, "right"):
                    self.x = bounds.right - self.width
                    self.vx = 0
        
        # Move Y
        self.y += self.vy * dt
        for col in room_manager.get_collisions(self.rect):
            if self.vy > 0:
                self.y = col.top - self.height
                self.on_ground = True
                self.vy = 0
            elif self.vy < 0:
                self.y = col.bottom
                self.vy = 0
        
        # Room edge collision Y
        if room_manager.current_room:
            bounds = room_manager.current_room.bounds
            if self.y < bounds.top:
                if not self._has_adjacent_room(room_manager, "up"):
                    self.y = bounds.top
                    self.vy = 0
            if self.y + self.height > bounds.bottom:
                if not self._has_adjacent_room(room_manager, "down"):
                    self.y = bounds.bottom - self.height
                    self.on_ground = True
                    self.vy = 0
    
    def _has_adjacent_room(self, room_manager, direction):
        """Check if there's an adjacent room in the given direction"""
        if not room_manager.current_room or not room_manager.rooms:
            return False
        
        current = room_manager.current_room.bounds
        
        for room in room_manager.rooms.values():
            if room == room_manager.current_room:
                continue
            other = room.bounds
            
            if direction == "right":
                if other.left <= current.right + 10 and other.left >= current.right - 10:
                    if other.top < current.bottom and other.bottom > current.top:
                        return True
            elif direction == "left":
                if other.right >= current.left - 10 and other.right <= current.left + 10:
                    if other.top < current.bottom and other.bottom > current.top:
                        return True
            elif direction == "down":
                if other.top <= current.bottom + 10 and other.top >= current.bottom - 10:
                    if other.left < current.right and other.right > current.left:
                        return True
            elif direction == "up":
                if other.bottom >= current.top - 10 and other.bottom <= current.top + 10:
                    if other.left < current.right and other.right > current.left:
                        return True
        
        return False
    
    def draw(self, surface, camera):
        # Draw grapple first (behind player)
        self.grapple.draw(surface, camera, self)
        
        # Draw player
        screen_rect = camera.apply_rect(self.rect)
        
        # Different color when grappling
        if self.grapple.state == "attached":
            color = self.grapple_color
        else:
            color = self.color
        
        pygame.draw.rect(surface, color, screen_rect)
        
        # Draw facing indicator (small triangle)
        if self.facing_right:
            points = [
                (screen_rect.right - 4, screen_rect.centery - 4),
                (screen_rect.right + 2, screen_rect.centery),
                (screen_rect.right - 4, screen_rect.centery + 4),
            ]
        else:
            points = [
                (screen_rect.left + 4, screen_rect.centery - 4),
                (screen_rect.left - 2, screen_rect.centery),
                (screen_rect.left + 4, screen_rect.centery + 4),
            ]
        pygame.draw.polygon(surface, (255, 255, 255), points)