import pygame
from .ui_components import Button, Slider, Selector, Toggle, KeyBinder
from settings.settings_manager import get_resolution_options, FPS_OPTIONS
from constants import *

class SettingsMenu:
    def __init__(self, game):
        self.game = game
        self.settings = game.settings
        self.tabs = ["Video", "Audio", "Controls"]
        self.current_tab = 0
        self.selected_index = 0
        self._create_ui()
    
    def _create_ui(self):
        w, h = self.game.width, self.game.height
        
        # Tabs
        tab_w, tab_h = 100, 30
        total = tab_w * 3 + 20
        start_x = (w - total) // 2
        self.tab_buttons = [
            Button(start_x + i * (tab_w + 10), 60, tab_w, tab_h, self.tabs[i], 20)
            for i in range(3)
        ]
        
        # Content
        cx = w // 2 - 150
        cy = 130
        cw = 300
        sp = 55
        
        video = self.settings.get("video")
        self.video_elements = [
            Selector(cx, cy, cw, 30, get_resolution_options(), self.settings.get_resolution_index(), "Resolution"),
            Selector(cx, cy + sp, cw, 30, FPS_OPTIONS, self.settings.get_fps_index(), "FPS Cap"),
            Toggle(cx, cy + sp*2, cw, 30, video["fullscreen"], "Fullscreen"),
            Toggle(cx, cy + sp*3, cw, 30, video["vsync"], "VSync"),
        ]
        
        audio = self.settings.get("audio")
        self.audio_elements = [
            Slider(cx, cy, cw, 25, 0, 1, audio["master"], "Master Volume"),
            Slider(cx, cy + sp, cw, 25, 0, 1, audio["sfx"], "SFX Volume"),
            Slider(cx, cy + sp*2, cw, 25, 0, 1, audio["music"], "Music Volume"),
        ]
        
        controls = self.settings.get("controls")
        self.control_elements = [
            KeyBinder(cx, cy, cw, 28, "left", controls["left"], "Move Left"),
            KeyBinder(cx, cy + sp, cw, 28, "right", controls["right"], "Move Right"),
            KeyBinder(cx, cy + sp*2, cw, 28, "jump", controls["jump"], "Jump"),
            KeyBinder(cx, cy + sp*3, cw, 28, "grapple", controls["grapple"], "Grapple"),
            KeyBinder(cx, cy + sp*4, cw, 28, "pause", controls["pause"], "Pause"),
        ]
        
        self.back_button = Button(30, h - 50, 80, 35, "Back", 20)
        self.apply_button = Button(w - 110, h - 50, 80, 35, "Apply", 20)
        
        self._update_selection()
    
    def _get_elements(self):
        return [self.video_elements, self.audio_elements, self.control_elements][self.current_tab]
    
    def _update_selection(self):
        for e in self.video_elements + self.audio_elements + self.control_elements:
            e.selected = False
        elements = self._get_elements()
        if elements and 0 <= self.selected_index < len(elements):
            elements[self.selected_index].selected = True
    
    def update(self, events, dt):
        mouse_pos = pygame.mouse.get_pos()
        elements = self._get_elements()
        
        waiting = self.current_tab == 2 and any(e.waiting_for_input for e in self.control_elements)
        
        for event in events:
            if event.type == pygame.KEYDOWN and not waiting:
                if event.key == pygame.K_ESCAPE:
                    return "back"
                elif event.key == pygame.K_UP:
                    self.selected_index = (self.selected_index - 1) % len(elements)
                    self._update_selection()
                elif event.key == pygame.K_DOWN:
                    self.selected_index = (self.selected_index + 1) % len(elements)
                    self._update_selection()
                elif event.key == pygame.K_TAB:
                    self.current_tab = (self.current_tab + 1) % 3
                    self.selected_index = 0
                    self._update_selection()
        
        for i, btn in enumerate(self.tab_buttons):
            if btn.update(mouse_pos, events):
                self.current_tab = i
                self.selected_index = 0
                self._update_selection()
        
        for elem in elements:
            if elem.update(mouse_pos, events):
                if self.current_tab == 1:
                    self.settings.set("audio", "master", self.audio_elements[0].value)
                    self.settings.set("audio", "sfx", self.audio_elements[1].value)
                    self.settings.set("audio", "music", self.audio_elements[2].value)
                elif self.current_tab == 2:
                    for c in self.control_elements:
                        self.settings.set("controls", c.action, c.key)
        
        if self.back_button.update(mouse_pos, events):
            return "back"
        
        if self.apply_button.update(mouse_pos, events) and self.current_tab == 0:
            res = self.video_elements[0].get_value()
            fps = self.video_elements[1].get_value()
            self.settings.set("video", "resolution", list(res))
            self.settings.set("video", "fps_cap", fps)
            self.settings.set("video", "fullscreen", self.video_elements[2].value)
            self.settings.set("video", "vsync", self.video_elements[3].value)
            self.game.apply_video_settings()
            self._create_ui()
        
        return None
    
    def draw(self, surface):
        surface.fill(COLOR_BG)
        w = surface.get_width()
        
        font = pygame.font.Font(None, 32)
        title = font.render("Settings", True, COLOR_WHITE)
        surface.blit(title, (w//2 - title.get_width()//2, 20))
        
        for i, btn in enumerate(self.tab_buttons):
            btn.selected = (i == self.current_tab)
            btn.draw(surface)
        
        for elem in self._get_elements():
            elem.draw(surface)
        
        self.back_button.draw(surface)
        if self.current_tab == 0:
            self.apply_button.draw(surface)