import pygame
from constants import *

class Button:
    def __init__(self, x, y, width, height, text, font_size=24):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = pygame.font.Font(None, font_size)
        self.hovered = False
        self.selected = False
        self.enabled = True
    
    def update(self, mouse_pos, events):
        self.hovered = self.rect.collidepoint(mouse_pos) and self.enabled
        
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.hovered:
                    return True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if self.selected:
                    return True
        return False
    
    def draw(self, surface):
        color = COLOR_DARK_GRAY
        if self.selected or self.hovered:
            color = COLOR_GRAY
        if not self.enabled:
            color = (30, 30, 30)
        
        pygame.draw.rect(surface, color, self.rect)
        border_color = COLOR_ACCENT if (self.selected or self.hovered) else COLOR_LIGHT_GRAY
        pygame.draw.rect(surface, border_color, self.rect, 2)
        
        text_color = COLOR_WHITE if self.enabled else COLOR_GRAY
        text_surf = self.font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class Slider:
    def __init__(self, x, y, width, height, min_val=0, max_val=1, value=0.5, label="", font_size=20):
        self.rect = pygame.Rect(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.label = label
        self.font = pygame.font.Font(None, font_size)
        self.dragging = False
        self.hovered = False
        self.selected = False
    
    def update(self, mouse_pos, events):
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.hovered:
                    self.dragging = True
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
            if event.type == pygame.KEYDOWN and self.selected:
                step = (self.max_val - self.min_val) / 20
                if event.key == pygame.K_LEFT:
                    self.value = max(self.min_val, self.value - step)
                    return True
                elif event.key == pygame.K_RIGHT:
                    self.value = min(self.max_val, self.value + step)
                    return True
        
        if self.dragging:
            relative_x = mouse_pos[0] - self.rect.x
            self.value = self.min_val + (relative_x / self.rect.width) * (self.max_val - self.min_val)
            self.value = max(self.min_val, min(self.max_val, self.value))
            return True
        return False
    
    def draw(self, surface):
        label_surf = self.font.render(self.label, True, COLOR_WHITE)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 22))
        
        pygame.draw.rect(surface, COLOR_DARK_GRAY, self.rect)
        pygame.draw.rect(surface, COLOR_LIGHT_GRAY, self.rect, 1)
        
        fill_width = int((self.value - self.min_val) / (self.max_val - self.min_val) * self.rect.width)
        fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
        pygame.draw.rect(surface, COLOR_ACCENT, fill_rect)
        
        val_text = f"{int(self.value * 100)}%" if self.max_val <= 1 else str(int(self.value))
        val_surf = self.font.render(val_text, True, COLOR_WHITE)
        surface.blit(val_surf, (self.rect.right - val_surf.get_width() - 5, self.rect.centery - val_surf.get_height()//2))


class Selector:
    def __init__(self, x, y, width, height, options, current_index=0, label="", font_size=20):
        self.rect = pygame.Rect(x, y, width, height)
        self.options = options
        self.index = current_index
        self.label = label
        self.font = pygame.font.Font(None, font_size)
        self.hovered = False
        self.selected = False
        self.left_arrow = pygame.Rect(x, y, 30, height)
        self.right_arrow = pygame.Rect(x + width - 30, y, 30, height)
    
    def update(self, mouse_pos, events):
        self.hovered = self.rect.collidepoint(mouse_pos)
        left_hover = self.left_arrow.collidepoint(mouse_pos)
        right_hover = self.right_arrow.collidepoint(mouse_pos)
        
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if left_hover:
                    self.index = (self.index - 1) % len(self.options)
                    return True
                elif right_hover:
                    self.index = (self.index + 1) % len(self.options)
                    return True
            if event.type == pygame.KEYDOWN and self.selected:
                if event.key == pygame.K_LEFT:
                    self.index = (self.index - 1) % len(self.options)
                    return True
                elif event.key == pygame.K_RIGHT:
                    self.index = (self.index + 1) % len(self.options)
                    return True
        return False
    
    def get_value(self):
        return self.options[self.index]
    
    def draw(self, surface):
        label_surf = self.font.render(self.label, True, COLOR_WHITE)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 22))
        
        pygame.draw.rect(surface, COLOR_DARK_GRAY, self.rect)
        pygame.draw.rect(surface, COLOR_LIGHT_GRAY, self.rect, 1)
        
        # Arrows
        pygame.draw.polygon(surface, COLOR_WHITE, [
            (self.left_arrow.centerx + 5, self.left_arrow.centery - 8),
            (self.left_arrow.centerx - 5, self.left_arrow.centery),
            (self.left_arrow.centerx + 5, self.left_arrow.centery + 8)
        ])
        pygame.draw.polygon(surface, COLOR_WHITE, [
            (self.right_arrow.centerx - 5, self.right_arrow.centery - 8),
            (self.right_arrow.centerx + 5, self.right_arrow.centery),
            (self.right_arrow.centerx - 5, self.right_arrow.centery + 8)
        ])
        
        value = self.options[self.index]
        val_text = f"{value[0]}x{value[1]}" if isinstance(value, tuple) else ("Unlimited" if value == 0 else str(value))
        val_surf = self.font.render(val_text, True, COLOR_WHITE)
        surface.blit(val_surf, (self.rect.centerx - val_surf.get_width()//2, self.rect.centery - val_surf.get_height()//2))


class Toggle:
    def __init__(self, x, y, width, height, value=False, label="", font_size=20):
        self.rect = pygame.Rect(x, y, width, height)
        self.value = value
        self.label = label
        self.font = pygame.font.Font(None, font_size)
        self.hovered = False
        self.selected = False
    
    def update(self, mouse_pos, events):
        self.hovered = self.rect.collidepoint(mouse_pos)
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered:
                self.value = not self.value
                return True
            if event.type == pygame.KEYDOWN and self.selected and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.value = not self.value
                return True
        return False
    
    def draw(self, surface):
        label_surf = self.font.render(self.label, True, COLOR_WHITE)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 22))
        
        pygame.draw.rect(surface, COLOR_DARK_GRAY, self.rect)
        pygame.draw.rect(surface, COLOR_LIGHT_GRAY, self.rect, 1)
        
        indicator = pygame.Rect(0, 0, 30, self.rect.height - 6)
        indicator.centery = self.rect.centery
        if self.value:
            indicator.right = self.rect.right - 3
            pygame.draw.rect(surface, COLOR_ACCENT, indicator)
        else:
            indicator.left = self.rect.left + 3
            pygame.draw.rect(surface, COLOR_LIGHT_GRAY, indicator)
        
        text = "ON" if self.value else "OFF"
        text_surf = self.font.render(text, True, COLOR_WHITE)
        surface.blit(text_surf, (self.rect.centerx - text_surf.get_width()//2, self.rect.centery - text_surf.get_height()//2))


class KeyBinder:
    def __init__(self, x, y, width, height, action, current_key, label="", font_size=20):
        self.rect = pygame.Rect(x, y, width, height)
        self.action = action
        self.key = current_key
        self.label = label
        self.font = pygame.font.Font(None, font_size)
        self.waiting_for_input = False
        self.hovered = False
        self.selected = False
    
    def update(self, mouse_pos, events):
        self.hovered = self.rect.collidepoint(mouse_pos)
        for event in events:
            if self.waiting_for_input:
                if event.type == pygame.KEYDOWN:
                    if event.key != pygame.K_ESCAPE:
                        self.key = event.key
                    self.waiting_for_input = False
                    return True
            else:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered:
                    self.waiting_for_input = True
                if event.type == pygame.KEYDOWN and self.selected and event.key == pygame.K_RETURN:
                    self.waiting_for_input = True
        return False
    
    def draw(self, surface):
        label_surf = self.font.render(self.label, True, COLOR_WHITE)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 22))
        
        bg_color = COLOR_ACCENT if self.waiting_for_input else (COLOR_GRAY if self.hovered or self.selected else COLOR_DARK_GRAY)
        pygame.draw.rect(surface, bg_color, self.rect)
        pygame.draw.rect(surface, COLOR_LIGHT_GRAY, self.rect, 1)
        
        text = "Press key..." if self.waiting_for_input else pygame.key.name(self.key).upper()
        text_surf = self.font.render(text, True, COLOR_WHITE)
        surface.blit(text_surf, (self.rect.centerx - text_surf.get_width()//2, self.rect.centery - text_surf.get_height()//2))