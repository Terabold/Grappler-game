import pygame
from .physics import (
    GrappleHook, apply_gravity, approach, sign, check_wall, check_ground,
    GRAVITY, TERMINAL_VELOCITY, JUMP_VELOCITY,
    WALL_SLIDE_SPEED, WALL_JUMP_VELOCITY_X, WALL_JUMP_VELOCITY_Y,
    COYOTE_TIME, JUMP_BUFFER_TIME,
    ROLL_SPEED, ROLL_DURATION, ROLL_COOLDOWN, ROLL_IFRAMES,
    SPRINT_MULTIPLIER
)
from .room import TILE_SOLID, TILE_PLATFORM, TILE_SPIKE, TILE_EXIT, TILE_GRAPPLE


class Player:
    """
    Player controller with:
    - Basic movement + sprint
    - Jump with coyote time and buffer
    - Wall slide and wall jump
    - Roll/dash with i-frames
    - Pull-based grappling hook
    - One-way platform support
    """
    
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.width = 24
        self.height = 24
        
        self.vx = 0.0
        self.vy = 0.0
        
        # Movement tuning
        self.speed = 260
        self.accel = 1600
        self.decel = 1400
        self.air_accel = 1200
        self.air_decel = 600
        
        # Ground/jump state
        self.on_ground = False
        self.coyote_timer = 0.0
        self.jump_buffer_timer = 0.0
        self.jump_held = False
        self.jump_released_midair = False
        
        # Platform drop-through (hold down to fall through platforms)
        self.drop_through_platforms = False
        self.last_y = 0.0  # Track last Y for platform collision
        
        # Wall state
        self.wall_dir = 0
        self.wall_jump_locked = False
        self.wall_jump_lock_timer = 0.0
        
        # Sprint state
        self.sprinting = False
        
        # Roll/dash state
        self.rolling = False
        self.roll_timer = 0.0
        self.roll_cooldown = 0.0
        self.roll_dir = 1  # 1 = right, -1 = left
        self.roll_was_pressed = False
        
        # Grapple
        self.grapple = GrappleHook()
        self.grapple_was_pressed = False
        
        # Visual
        self.facing_right = True
        
        # State
        self.frozen = False
        self.transition_dir = (0, 0)
        self.transition_slid = 0.0
        self.transition_slide = 200  # Increased to move player further during transition
        
        # Combat
        self.health = 100
        self.max_health = 100
        self.invincible_timer = 0.0
        
        # Flags for game state
        self.on_exit = False  # True when touching exit tile
        self.exit_direction = None  # Direction of exit being touched
        self.dead = False
    
    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)
    
    @property
    def center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def is_invincible(self):
        """True if player can't be hurt (rolling or i-frames)"""
        return self.invincible_timer > 0 or (self.rolling and self.roll_timer < ROLL_IFRAMES)
    
    # =========================================================================
    # TRANSITIONS
    # =========================================================================
    
    def start_transition(self, direction):
        self.frozen = True
        self.transition_slid = 0.0
        self.grapple.cancel()
        self.vx = 0.0
        self.vy = 0.0
        self.rolling = False
        
        dirs = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}
        self.transition_dir = dirs.get(direction, (0, 0))
    
    def end_transition(self):
        self.frozen = False
        self.transition_dir = (0, 0)
    
    # =========================================================================
    # UPDATE
    # =========================================================================
    
    def update(self, dt, room_manager, controls, camera=None):
        if self.frozen:
            if self.transition_slid < self.transition_slide:
                move = 150 * dt
                self.x += self.transition_dir[0] * move
                self.y += self.transition_dir[1] * move
                self.transition_slid += move
            return
        
        dt = min(dt, 0.033)
        
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        
        if camera:
            world_mouse = camera.screen_to_world(mouse_pos)
        else:
            world_mouse = mouse_pos
        
        # Update timers
        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.wall_jump_lock_timer = max(0.0, self.wall_jump_lock_timer - dt)
        self.roll_cooldown = max(0.0, self.roll_cooldown - dt)
        
        if self.wall_jump_lock_timer <= 0:
            self.wall_jump_locked = False
        
        # Grapple input - RIGHT MOUSE ONLY (no keyboard conflict)
        grapple_pressed = mouse[2]  # Right mouse button only
        
        # Roll input (left ctrl or left mouse)
        roll_pressed = keys[pygame.K_LCTRL] or mouse[0]
        
        # Sprint input - hold Shift OR double-tap direction
        # Using Shift now works since grapple is right-mouse only
        self.sprinting = keys[pygame.K_LSHIFT]
        
        # Handle grapple
        self._handle_grapple(dt, grapple_pressed, world_mouse, keys, controls, room_manager)
        
        # If rolling, continue roll
        if self.rolling:
            self._update_roll(dt, room_manager)
        # If attached to grapple, grapple controls movement
        elif self.grapple.state == "attached":
            self._update_grappling(dt, keys, controls, room_manager)
        else:
            # Check for roll initiation
            if roll_pressed and not self.roll_was_pressed and self.roll_cooldown <= 0:
                self._start_roll(keys, controls)
            else:
                self._update_normal(dt, keys, controls, room_manager)
        
        self.grapple_was_pressed = grapple_pressed
        self.roll_was_pressed = roll_pressed
    
    # =========================================================================
    # ROLL/DASH
    # =========================================================================
    
    def _start_roll(self, keys, controls):
        """Initiate a roll/dash - only on ground."""
        # Can only roll on ground
        if not self.on_ground:
            return
        
        self.rolling = True
        self.roll_timer = 0.0
        self.roll_cooldown = ROLL_COOLDOWN
        
        # Roll in input direction, or facing direction if no input
        if keys[controls["left"]]:
            self.roll_dir = -1
            self.facing_right = False
        elif keys[controls["right"]]:
            self.roll_dir = 1
            self.facing_right = True
        else:
            self.roll_dir = 1 if self.facing_right else -1
        
        # Set roll velocity
        self.vx = self.roll_dir * ROLL_SPEED
        
        # Small upward boost to make it feel snappy
        self.vy = -80
    
    def _update_roll(self, dt, room_manager):
        """Update during roll."""
        self.roll_timer += dt
        
        if self.roll_timer >= ROLL_DURATION:
            # End roll
            self.rolling = False
            # Preserve some momentum
            self.vx *= 0.6
            return
        
        # Maintain roll speed (no deceleration during roll)
        self.vx = self.roll_dir * ROLL_SPEED
        
        # Reduced gravity during roll
        self.vy = apply_gravity(self.vy, dt * 0.4)
        
        # Clear wall state during roll
        self.wall_dir = 0
        
        # Move with collision
        self._move_with_collision(dt, room_manager)
    
    # =========================================================================
    # GRAPPLE
    # =========================================================================
    
    def _handle_grapple(self, dt, grapple_pressed, world_mouse, keys, controls, room_manager):
        """Handle grapple input."""
        # Fire only on fresh press
        if grapple_pressed and not self.grapple_was_pressed:
            if self.grapple.state == "inactive" and not self.rolling:
                cx, cy = self.center
                self.grapple.fire(cx, cy, world_mouse[0], world_mouse[1])
        
        # Release on button release
        if not grapple_pressed and self.grapple_was_pressed:
            if self.grapple.state == "attached":
                boost_vx, boost_vy = self.grapple.release()
                self.vx = boost_vx
                self.vy = boost_vy
            elif self.grapple.state == "firing":
                self.grapple.cancel()
        
        # Update firing grapple
        if self.grapple.state == "firing":
            self.grapple.update(dt, self, room_manager)
    
    def _update_grappling(self, dt, keys, controls, room_manager):
        """Update while grappling."""
        if keys[controls.get("down", pygame.K_s)]:
            self.grapple.set_mode("swing")
        else:
            self.grapple.set_mode("pull")
        
        self.grapple.update(dt, self, room_manager)
        
        if self.grapple.mode == "swing":
            if keys[controls["left"]]:
                self.grapple.add_swing_force(-1, dt)
            if keys[controls["right"]]:
                self.grapple.add_swing_force(1, dt)
            if keys[controls["up"]]:
                self.grapple.shorten_rope(200 * dt)
            if keys[controls["down"]]:
                self.grapple.lengthen_rope(200 * dt)
        
        self.on_ground = False
        self.wall_dir = 0
        self._move_with_collision(dt, room_manager)
    
    # =========================================================================
    # NORMAL MOVEMENT
    # =========================================================================
    
    def _update_normal(self, dt, keys, controls, room_manager):
        """Normal movement update."""
        # Get horizontal input
        move_input = 0
        if keys[controls["left"]]:
            move_input -= 1
        if keys[controls["right"]]:
            move_input += 1
        
        if move_input != 0:
            self.facing_right = move_input > 0
        
        # Drop through platforms when holding down
        self.drop_through_platforms = keys[controls.get("down", pygame.K_s)]
        
        # Apply horizontal movement (with sprint)
        self._apply_horizontal_movement(move_input, dt)
        
        # Check walls (only when airborne and not locked)
        self.wall_dir = 0
        if not self.on_ground and not self.wall_jump_locked:
            if check_wall(self.rect, "left", room_manager):
                self.wall_dir = -1
            elif check_wall(self.rect, "right", room_manager):
                self.wall_dir = 1
        
        # Apply gravity (with wall slide)
        if self.wall_dir != 0 and self.vy > 0:
            self.vy = min(self.vy + GRAVITY * 0.1 * dt, WALL_SLIDE_SPEED)
        else:
            self.vy = apply_gravity(self.vy, dt)
        
        # Update timers
        if self.on_ground:
            self.coyote_timer = COYOTE_TIME
            self.jump_released_midair = False
            self.wall_jump_locked = False
        else:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)
        
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        
        # Handle jump
        self._handle_jump(keys, controls)
        
        # Move with collision
        self._move_with_collision(dt, room_manager)
    
    def _apply_horizontal_movement(self, move_input, dt):
        """Apply horizontal acceleration/deceleration with sprint."""
        # Calculate target speed (with sprint)
        current_speed = self.speed
        if self.sprinting and self.on_ground:
            current_speed *= SPRINT_MULTIPLIER
        
        target_vx = move_input * current_speed
        
        if self.on_ground:
            if move_input != 0:
                self.vx = approach(self.vx, target_vx, self.accel * dt)
            else:
                self.vx = approach(self.vx, 0, self.decel * dt)
        else:
            if move_input != 0:
                self.vx = approach(self.vx, target_vx, self.air_accel * dt)
            else:
                self.vx = approach(self.vx, 0, self.air_decel * dt)
        
        if abs(self.vx) < 0.5:
            self.vx = 0.0
    
    def _handle_jump(self, keys, controls):
        """Handle jump input."""
        jump_pressed = keys[controls["jump"]]
        
        if jump_pressed:
            if not self.jump_held:
                self.jump_held = True
                self.jump_released_midair = False
                
                if self._can_jump():
                    self._do_jump()
                elif self.wall_dir != 0:
                    self._do_wall_jump()
                else:
                    self.jump_buffer_timer = JUMP_BUFFER_TIME
        else:
            if self.jump_held:
                if self.vy < 0 and not self.jump_released_midair:
                    self.vy *= 0.5
                    self.jump_released_midair = True
            self.jump_held = False
        
        # Buffered jump
        if self.jump_buffer_timer > 0:
            if self.on_ground:
                self._do_jump()
                self.jump_buffer_timer = 0.0
            elif self.wall_dir != 0:
                self._do_wall_jump()
                self.jump_buffer_timer = 0.0
    
    def _can_jump(self):
        return self.on_ground or self.coyote_timer > 0
    
    def _do_jump(self):
        self.vy = JUMP_VELOCITY
        self.on_ground = False
        self.coyote_timer = 0.0
    
    def _do_wall_jump(self):
        self.vx = -self.wall_dir * WALL_JUMP_VELOCITY_X
        self.vy = WALL_JUMP_VELOCITY_Y
        self.on_ground = False
        self.coyote_timer = 0.0
        self.facing_right = self.vx > 0
        self.wall_jump_locked = True
        self.wall_jump_lock_timer = 0.2
        self.wall_dir = 0
    
    # =========================================================================
    # COLLISION
    # =========================================================================
    
    def _move_with_collision(self, dt, room_manager):
        """Move with collision resolution and one-way platform support."""
        # Previous bottom for One-Way platform check
        prev_bottom = self.y + self.height
        
        # Sub-stepping for collision accuracy (prevent tunneling)
        # Calculate total move amount
        dx = self.vx * dt
        dy = self.vy * dt
        
        # Determine number of steps (max 8 pixels per step to be safe)
        steps_x = max(1, int(abs(dx) / 10) + 1)
        steps_y = max(1, int(abs(dy) / 10) + 1)
        
        step_dx = dx / steps_x
        step_dy = dy / steps_y
        
        # Move X in steps
        for _ in range(steps_x):
            self.x += step_dx
            rect = self.rect
            collision = False
            
            # Check for wall collision
            for tile in room_manager.get_collisions(rect):
                if tile.tile_type == TILE_SOLID:
                    if step_dx > 0:
                        self.x = tile.rect.left - self.width
                        self.vx = 0.0
                    elif step_dx < 0:
                        self.x = tile.rect.right
                        self.vx = 0.0
                    collision = True
                    break # Stop processing this step if collided
            
            # Check room bounds X if no tile collision happened (or even if it did, to be safe)
            if room_manager.current_room:
                bounds = room_manager.current_room.bounds
                if self.x < bounds.left:
                    if not self._has_adjacent_room(room_manager, "left"):
                        self.x = bounds.left
                        self.vx = 0.0
                elif self.x + self.width > bounds.right:
                    if not self._has_adjacent_room(room_manager, "right"):
                        self.x = bounds.right - self.width
                        self.vx = 0.0
            
            if collision:
                break
        
        # Move Y in steps
        landed = False
        for _ in range(steps_y):
            self.y += step_dy
            rect = self.rect
            collision = False
            
            # Check collisions
            for tile in room_manager.get_collisions(rect):
                if tile.tile_type == TILE_SOLID:
                    if step_dy >= 0:
                        self.y = tile.rect.top - self.height
                        self.vy = 0.0
                        landed = True
                    elif step_dy < 0:
                        self.y = tile.rect.bottom
                        self.vy = 0.0
                    collision = True
                    
                elif tile.tile_type == TILE_PLATFORM:
                    if (step_dy >= 0 and 
                        prev_bottom <= tile.rect.top + 4 and 
                        not self.drop_through_platforms):
                        # Ensure we are actually colliding with the top part
                        if self.y + self.height >= tile.rect.top and self.y + self.height <= tile.rect.top + 10:
                            self.y = tile.rect.top - self.height
                            self.vy = 0.0
                            landed = True
                            collision = True
                
                if collision:
                    break
            
            # Check room bounds Y
            if room_manager.current_room:
                bounds = room_manager.current_room.bounds
                if self.y < bounds.top:
                    if not self._has_adjacent_room(room_manager, "up"):
                        self.y = bounds.top
                        self.vy = 0.0
                elif self.y + self.height > bounds.bottom:
                    if not self._has_adjacent_room(room_manager, "down"):
                        self.y = bounds.bottom - self.height
                        self.vy = 0.0
                        landed = True
            
            if collision:
                break
        
        # Ground check
        if landed:
            self.on_ground = True
        else:
            self.on_ground = self._check_ground_with_platforms(room_manager)
        
        # Check for hazards and special tiles
        self._check_tile_hazards(room_manager)
    
    def _check_ground_with_platforms(self, room_manager):
        """Check if standing on solid ground or platform."""
        # Check a thin rect below the player
        test_rect = pygame.Rect(
            int(self.x) + 2,
            int(self.y) + self.height,
            self.width - 4,
            3
        )
        
        for tile in room_manager.get_collisions(test_rect):
            if tile.tile_type == TILE_SOLID:
                return True
            elif tile.tile_type == TILE_PLATFORM and not self.drop_through_platforms:
                return True
        
        # Check room floor
        if room_manager.current_room:
            bounds = room_manager.current_room.bounds
            if self.y + self.height >= bounds.bottom - 2:
                return True
        
        return False
    
    def _has_adjacent_room(self, room_manager, direction):
        """Check for adjacent room."""
        if not room_manager.current_room or not room_manager.rooms:
            return False
        
        current = room_manager.current_room.bounds
        
        for room in room_manager.rooms.values():
            if room == room_manager.current_room:
                continue
            other = room.bounds
            
            if direction == "right":
                if abs(other.left - current.right) <= 10:
                    if other.top < current.bottom and other.bottom > current.top:
                        return True
            elif direction == "left":
                if abs(other.right - current.left) <= 10:
                    if other.top < current.bottom and other.bottom > current.top:
                        return True
            elif direction == "down":
                if abs(other.top - current.bottom) <= 10:
                    if other.left < current.right and other.right > current.left:
                        return True
            elif direction == "up":
                if abs(other.bottom - current.top) <= 10:
                    if other.left < current.right and other.right > current.left:
                        return True
        
        return False
    
    def _check_tile_hazards(self, room_manager):
        """Check for spike damage and exit tiles."""
        self.on_exit = False
        self.exit_direction = None
        
        for tile in room_manager.get_collisions(self.rect):
            if tile.tile_type == TILE_SPIKE:
                # Spikes deal damage
                if not self.is_invincible:
                    self.take_damage(25, 0, -300)
            elif tile.tile_type == TILE_EXIT:
                # Determine exit direction based on position in room
                room = room_manager.current_room
                if room:
                    # Check if exit is on the right edge
                    if self.x + self.width >= room.bounds.right - 32:
                        self.exit_direction = "right"
                    # Check if exit is on the left edge
                    elif self.x <= room.bounds.left + 32:
                        self.exit_direction = "left"
                    # Check if exit is on the bottom
                    elif self.y + self.height >= room.bounds.bottom - 32:
                        self.exit_direction = "down"
                    # Check if exit is on the top
                    elif self.y <= room.bounds.top + 32:
                        self.exit_direction = "up"
                    
                    if self.exit_direction:
                        self.on_exit = True
    
    # =========================================================================
    # COMBAT
    # =========================================================================
    
    def take_damage(self, amount, knockback_x=0, knockback_y=0):
        """Take damage if not invincible."""
        if self.is_invincible:
            return False
        
        self.health -= amount
        self.invincible_timer = 1.0
        
        # Check for death
        if self.health <= 0:
            self.dead = True
            self.health = 0
        
        # Apply knockback
        self.vx = knockback_x
        self.vy = knockback_y - 200
        
        # Cancel roll and grapple
        self.rolling = False
        self.grapple.cancel()
        
        return True
    
    # =========================================================================
    # DRAW
    # =========================================================================
    
    def draw(self, surface, camera):
        self.grapple.draw(surface, camera, self)
        
        # Determine color based on state
        if self.rolling:
            # Flash during i-frames portion of roll
            if self.roll_timer < ROLL_IFRAMES:
                color = (255, 255, 150)  # Yellow-ish during i-frames
            else:
                color = (200, 200, 100)  # Slightly different during rest of roll
        elif self.grapple.state == "attached":
            color = (120, 180, 255)
        elif self.wall_dir != 0:
            color = (180, 180, 220)
        elif self.sprinting:
            color = (150, 255, 150)  # Brighter green when sprinting
        else:
            color = (100, 220, 120)
        
        # Flash when invincible (from damage, not roll)
        if self.invincible_timer > 0 and not self.rolling:
            if int(self.invincible_timer * 10) % 2 == 0:
                color = (255, 255, 255)
        
        # Draw player
        screen_rect = camera.apply_rect(self.rect)
        
        if self.rolling:
            # Squish effect during roll
            squish = 0.7
            roll_rect = pygame.Rect(
                screen_rect.x,
                screen_rect.y + screen_rect.height * (1 - squish) / 2,
                screen_rect.width * 1.2,
                screen_rect.height * squish
            )
            pygame.draw.rect(surface, color, roll_rect)
        else:
            pygame.draw.rect(surface, color, screen_rect)
        
        # Facing indicator (not during roll)
        if not self.rolling:
            cx, cy = screen_rect.centerx, screen_rect.centery
            if self.facing_right:
                points = [(cx + 7, cy), (cx + 1, cy - 4), (cx + 1, cy + 4)]
            else:
                points = [(cx - 7, cy), (cx - 1, cy - 4), (cx - 1, cy + 4)]
            pygame.draw.polygon(surface, (255, 255, 255), points)
        
        # Wall slide indicator
        if self.wall_dir != 0 and not self.on_ground and not self.rolling:
            for i in range(3):
                py = screen_rect.top + 4 + i * 6
                px = screen_rect.left - 2 if self.wall_dir < 0 else screen_rect.right + 2
                pygame.draw.line(surface, (200, 200, 255), (px, py), (px, py + 3), 2)
        
        # Sprint particles (simple trailing effect)
        if self.sprinting and self.on_ground and abs(self.vx) > 200:
            trail_x = screen_rect.centerx - sign(self.vx) * 15
            trail_y = screen_rect.bottom - 4
            pygame.draw.circle(surface, (150, 255, 150), (int(trail_x), int(trail_y)), 3)