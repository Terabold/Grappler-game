import pygame

class Camera:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Fixed view size - how much of the world the camera sees
        self.view_width = 640
        self.view_height = 384
        
        # Scale to fill screen completely (may stretch slightly)
        self.scale_x = screen_width / self.view_width
        self.scale_y = screen_height / self.view_height
        
        # Camera position in world
        self.x = 0
        self.y = 0
        
        # Smooth follow
        self.lerp_speed = 8
        
        # Room bounds
        self.bounds = None
        
        # Transition state
        self.transitioning = False
        self.transition_progress = 0
        self.transition_speed = 5
        self.transition_start = (0, 0)
        self.transition_target = (0, 0)
        self.on_transition_complete = None
    
    def set_bounds(self, rect):
        self.bounds = rect
    
    def follow(self, target_x, target_y, dt):
        if self.transitioning:
            self._update_transition(dt)
            return
        
        target_cam_x = target_x - self.view_width / 2
        target_cam_y = target_y - self.view_height / 2
        
        self.x += (target_cam_x - self.x) * self.lerp_speed * dt
        self.y += (target_cam_y - self.y) * self.lerp_speed * dt
        
        self._clamp_to_bounds()
    
    def _clamp_to_bounds(self):
        if self.bounds is None:
            return
        
        if self.bounds.width <= self.view_width:
            self.x = self.bounds.x + (self.bounds.width - self.view_width) / 2
        else:
            self.x = max(self.bounds.x, min(self.x, self.bounds.right - self.view_width))
        
        if self.bounds.height <= self.view_height:
            self.y = self.bounds.y + (self.bounds.height - self.view_height) / 2
        else:
            self.y = max(self.bounds.y, min(self.y, self.bounds.bottom - self.view_height))
    
    def start_transition(self, new_bounds, direction, callback=None):
        self.transitioning = True
        self.transition_progress = 0
        self.transition_start = (self.x, self.y)
        self.on_transition_complete = callback
        
        if direction == "right":
            target_x = new_bounds.x
            target_y = self.y
        elif direction == "left":
            target_x = new_bounds.right - self.view_width
            target_y = self.y
        elif direction == "down":
            target_x = self.x
            target_y = new_bounds.y
        elif direction == "up":
            target_x = self.x
            target_y = new_bounds.bottom - self.view_height
        else:
            target_x, target_y = self.x, self.y
        
        if new_bounds.width <= self.view_width:
            target_x = new_bounds.x + (new_bounds.width - self.view_width) / 2
        else:
            target_x = max(new_bounds.x, min(target_x, new_bounds.right - self.view_width))
        
        if new_bounds.height <= self.view_height:
            target_y = new_bounds.y + (new_bounds.height - self.view_height) / 2
        else:
            target_y = max(new_bounds.y, min(target_y, new_bounds.bottom - self.view_height))
        
        self.transition_target = (target_x, target_y)
        self.bounds = new_bounds
    
    def _update_transition(self, dt):
        self.transition_progress += dt * self.transition_speed
        
        if self.transition_progress >= 1:
            self.transition_progress = 1
            self.transitioning = False
            self.x, self.y = self.transition_target
            self._clamp_to_bounds()
            
            if self.on_transition_complete:
                self.on_transition_complete()
                self.on_transition_complete = None
            return
        
        t = 1 - (1 - self.transition_progress) ** 3
        
        self.x = self.transition_start[0] + (self.transition_target[0] - self.transition_start[0]) * t
        self.y = self.transition_start[1] + (self.transition_target[1] - self.transition_start[1]) * t
    
    def world_to_screen(self, world_pos):
        screen_x = (world_pos[0] - self.x) * self.scale_x
        screen_y = (world_pos[1] - self.y) * self.scale_y
        return (screen_x, screen_y)
    
    def apply(self, world_pos):
        return self.world_to_screen(world_pos)
    
    def apply_rect(self, rect):
        x, y = self.world_to_screen((rect.x, rect.y))
        w = rect.width * self.scale_x
        h = rect.height * self.scale_y
        return pygame.Rect(x, y, w, h)
    
    def screen_to_world(self, screen_pos):
        world_x = screen_pos[0] / self.scale_x + self.x
        world_y = screen_pos[1] / self.scale_y + self.y
        return (world_x, world_y)