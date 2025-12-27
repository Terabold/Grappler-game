import pygame
from .ui_components import Button
from .settings_menu import SettingsMenu
from constants import *

class PauseMenu:
    def __init__(self, game):
        self.game = game
        self.settings_menu = None
        self.in_settings = False
        self._create_buttons()
    
    def _create_buttons(self):
        w, h = self.game.width, self.game.height
        btn_w, btn_h = 200, 40
        
        self.buttons = [
            Button(w//2 - btn_w//2, h//2 - 60, btn_w, btn_h, "Resume"),
            Button(w//2 - btn_w//2, h//2, btn_w, btn_h, "Settings"),
            Button(w//2 - btn_w//2, h//2 + 60, btn_w, btn_h, "Main Menu"),
        ]
    
    def update(self, events, dt):
        if self.in_settings:
            if self.settings_menu.update(events, dt) == "back":
                self.in_settings = False
                self._create_buttons() # Recreate buttons to ensure they have correct references if needed
            return
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, btn in enumerate(self.buttons):
            if btn.update(mouse_pos, events):
                if i == 0: # Resume
                    self.game.state = "playing"
                elif i == 1: # Settings
                    self.in_settings = True
                    self.settings_menu = SettingsMenu(self.game)
                elif i == 2: # Main Menu
                    self.game.state = "main_menu"
                    self.game.main_menu = self.game.create_main_menu() # Recreate main menu to reset state
    
    def draw(self, surface):
        # Draw semi-transparent background
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surface.blit(dim, (0, 0))
        
        if self.in_settings:
            self.settings_menu.draw(surface)
            return
        
        # Draw "PAUSED" text
        font = pygame.font.Font(None, 64)
        text = font.render("PAUSED", True, COLOR_WHITE)
        surface.blit(text, (surface.get_width()//2 - text.get_width()//2, 100))
        
        for btn in self.buttons:
            btn.draw(surface)
