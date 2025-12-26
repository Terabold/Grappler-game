import pygame
import os
from settings.settings_manager import SettingsManager
from menus.main_menu import MainMenu
from game.camera import Camera
from game.room import RoomManager
from game.player import Player

class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            print("Warning: No audio device found, audio disabled")
        
        self.settings = SettingsManager()
        self._init_display()
        
        pygame.display.set_caption("Grapple")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game states
        self.state = "main_menu"
        self.main_menu = MainMenu(self)
        
        # Game objects
        self.camera = None
        self.room_manager = None
        self.player = None
    
    def _init_display(self):
        video = self.settings.get("video")
        
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        
        if video["fullscreen"]:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(
                (video["resolution"][0], video["resolution"][1])
            )
        
        self.width = self.screen.get_width()
        self.height = self.screen.get_height()
        self.fps_cap = video["fps_cap"] if video["fps_cap"] != 0 else 9999
    
    def apply_video_settings(self):
        self._init_display()
        pygame.display.set_caption("Grapple")
        # Rebuild menus for new resolution
        self.main_menu = MainMenu(self)
    
    def start_game(self):
        # Camera takes screen size, internally uses fixed view size
        self.camera = Camera(self.width, self.height)
        
        rooms_dir = os.path.join(os.path.dirname(__file__), "rooms")
        self.room_manager = RoomManager(rooms_dir)
        self.room_manager.set_camera(self.camera)
        self.room_manager.load_chapter("chapter_01.json")
        
        if self.room_manager.chapter:
            spawn = self.room_manager.chapter.spawn
            self.player = Player(spawn[0], spawn[1])
        else:
            self.player = Player(100, 100)
        
        self.state = "playing"
    
    def run(self):
        while self.running:
            dt = self.clock.tick(self.fps_cap) / 1000.0
            # Cap dt to prevent physics explosion on lag
            dt = min(dt, 0.05)
            
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
            
            if self.state in ("main_menu", "settings"):
                self.main_menu.update(events, dt)
                self.main_menu.draw(self.screen)
            elif self.state == "playing":
                self.update_game(events, dt)
                self.draw_game()
            
            pygame.display.flip()
        
        pygame.quit()
    
    def update_game(self, events, dt):
        controls = self.settings.get("controls")
        
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == controls["pause"]:
                    self.state = "main_menu"
                    return
            
            # Handle mouse click for grapple aiming
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # Right click
                    # Convert screen mouse position to world position
                    mouse_screen = event.pos
                    world_pos = self.camera.screen_to_world(mouse_screen)
                    self.player.fire_grapple_at(world_pos[0], world_pos[1])
        
        self.player.update(dt, self.room_manager, controls)
        
        transition = self.room_manager.check_room_transition(self.player.rect)
        if transition and not self.camera.transitioning:
            room_id, direction = transition
            self.player.start_transition(direction)
            self.room_manager.transition_to(room_id, direction, self.player.end_transition)
        
        cx, cy = self.player.center
        self.camera.follow(cx, cy, dt)
    
    def draw_game(self):
        self.screen.fill((20, 20, 30))
        self.room_manager.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        
        # Draw HUD
        self._draw_hud()
    
    def _draw_hud(self):
        font = pygame.font.Font(None, 24)
        
        # FPS
        fps_text = font.render(f"FPS: {int(self.clock.get_fps())}", True, (150, 150, 150))
        self.screen.blit(fps_text, (10, 10))
        
        # Grapple state
        grapple_state = self.player.grapple.state
        state_colors = {
            "inactive": (100, 100, 100),
            "firing": (200, 200, 100),
            "attached": (100, 200, 100),
        }
        state_text = font.render(f"Grapple: {grapple_state}", True, state_colors.get(grapple_state, (150, 150, 150)))
        self.screen.blit(state_text, (10, 35))
        
        # Controls hint
        hint_font = pygame.font.Font(None, 20)
        hints = [
            "WASD: Move",
            "Space: Jump",
            "Shift/RMB: Grapple",
            "While grappling: W/S = climb, A/D = swing",
        ]
        for i, hint in enumerate(hints):
            hint_text = hint_font.render(hint, True, (100, 100, 100))
            self.screen.blit(hint_text, (10, self.height - 80 + i * 18))


if __name__ == "__main__":
    game = Game()
    game.run()