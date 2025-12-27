import pygame
from .ui_components import Button
from .settings_menu import SettingsMenu
from constants import *

class MainMenu:
    def __init__(self, game):
        self.game = game
        self.selected_index = 0
        self.settings_menu = None
        self.in_settings = False
        self._create_buttons()
    
    def _create_buttons(self):
        w, h = self.game.width, self.game.height
        btn_w, btn_h = 200, 40
        
        self.buttons = [
            Button(w//2 - btn_w//2, h//2, btn_w, btn_h, "Play"),
            Button(w//2 - btn_w//2, h//2 + 50, btn_w, btn_h, "Room Editor"),
            Button(w//2 - btn_w//2, h//2 + 100, btn_w, btn_h, "World Editor"),
            Button(w//2 - btn_w//2, h//2 + 150, btn_w, btn_h, "Settings"),
            Button(w//2 - btn_w//2, h//2 + 200, btn_w, btn_h, "Quit"),
        ]
        self.buttons[self.selected_index].selected = True
    
    def update(self, events, dt):
        if self.in_settings:
            if self.settings_menu.update(events, dt) == "back":
                self.in_settings = False
                self._create_buttons()
            return
        
        mouse_pos = pygame.mouse.get_pos()
        
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.buttons[self.selected_index].selected = False
                    self.selected_index = (self.selected_index - 1) % len(self.buttons)
                    self.buttons[self.selected_index].selected = True
                elif event.key == pygame.K_DOWN:
                    self.buttons[self.selected_index].selected = False
                    self.selected_index = (self.selected_index + 1) % len(self.buttons)
                    self.buttons[self.selected_index].selected = True
        
        for i, btn in enumerate(self.buttons):
            if btn.update(mouse_pos, events):
                if i == 0:
                    self.game.start_game()
                elif i == 1:
                    self.game.start_editor()
                elif i == 2:
                    self.game.start_world_editor()
                elif i == 3:
                    self.in_settings = True
                    self.settings_menu = SettingsMenu(self.game)
                elif i == 4:
                    self.game.running = False
    
    def draw(self, surface):
        surface.fill(COLOR_BG)
        
        if self.in_settings:
            self.settings_menu.draw(surface)
            return
        
        w, h = surface.get_size()
        
        font_big = pygame.font.Font(None, 64)
        font_small = pygame.font.Font(None, 24)
        
        title = font_big.render("GRAPPLE", True, COLOR_WHITE)
        surface.blit(title, (w//2 - title.get_width()//2, h//4))
        
        subtitle = font_small.render("A grappling hook action game", True, COLOR_ACCENT)
        surface.blit(subtitle, (w//2 - subtitle.get_width()//2, h//4 + 50))
        
        for btn in self.buttons:
            btn.draw(surface)