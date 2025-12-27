import pygame
import os
from settings.settings_manager import SettingsManager
from menus.main_menu import MainMenu
from menus.pause_menu import PauseMenu
from roomeditor import RoomEditor
from worldeditor import WorldEditor
from game.camera import Camera
from game.room import RoomManager
from game.player import Player


class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            print("Warning: No audio device found")
        
        self.settings = SettingsManager()
        self._init_display()
        
        pygame.display.set_caption("Grapple")
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.state = "main_menu"
        self.state = "main_menu"
        self.main_menu = MainMenu(self)
        self.pause_menu = PauseMenu(self)
        self.editor = None
        self.world_editor = None
        
        self.camera = None
        self.room_manager = None
        self.player = None
        
        self.show_debug = True
    
    def _init_display(self):
        video = self.settings.get("video")
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        
        if video["fullscreen"]:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
        else:
            self.screen = pygame.display.set_mode(
                (video["resolution"][0], video["resolution"][1]),
                pygame.HWSURFACE | pygame.DOUBLEBUF
            )
        
        self.width = self.screen.get_width()
        self.height = self.screen.get_height()
        self.fps_cap = video["fps_cap"] if video["fps_cap"] != 0 else 9999
    
    def apply_video_settings(self):
        self._init_display()
        pygame.display.set_caption("Grapple")
        self.main_menu = MainMenu(self)
        self.pause_menu = PauseMenu(self)

    def create_main_menu(self):
        return MainMenu(self)

    def start_editor(self, filename=None):
        self.editor = RoomEditor(self)
        if filename:
            self.editor.room.load(filename)
            self.editor.width_input.set_value(self.editor.room.width)
            self.editor.height_input.set_value(self.editor.room.height)
            self.editor.center_view()
            self.editor.from_world_editor = True # Flag to know where to return
        else:
            self.editor.from_world_editor = False
            
        self.state = "editor"

    def start_world_editor(self):
        self.world_editor = WorldEditor(self)
        self.state = "world_editor"
    
    def start_game(self):
        self.camera = Camera(self.width, self.height)
        
        rooms_dir = os.path.join(os.path.dirname(__file__), "rooms")
        self.room_manager = RoomManager(rooms_dir)
        self.room_manager.set_camera(self.camera)
        self.room_manager.load_world("world.json")
        
        # Get spawn from room manager
        spawn = self.room_manager.spawn
        self.player = Player(spawn[0], spawn[1])
        
        self.state = "playing"
    
    def run(self):
        while self.running:
            dt = self.clock.tick(self.fps_cap) / 1000.0
            
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F3:
                        self.show_debug = not self.show_debug
            
            if self.state in ("main_menu", "settings"):
                self.main_menu.update(events, dt)
                self.main_menu.draw(self.screen)
            elif self.state == "playing":
                self.update_game(events, dt)
                self.draw_game()
            elif self.state == "paused":
                self.pause_menu.update(events, dt)
                self.draw_game() # Draw game behind pause menu
                self.pause_menu.draw(self.screen)
            elif self.state == "editor":
                # Editor has its own loop structure, but we refactored it to use update/draw
                # But roomeditor.py handles its own loop in 'run'. 
                # Since we want to integrate it, we should use its update/draw methods if possible
                # The refactoring I did kept 'run' but added 'update' and 'draw'. 
                # However, 'run' has the loop. 
                # Let's change this: We will just call editor.run() once and let it block?
                # No, that blocks the main loop here. 
                # My refactor of RoomEditor added handle_events, update, draw. 
                # So we can just call those.
                
                # We need to manually pass events to editor because it gets them internally in handle_events
                # But since we already got events here... 
                # RoomEditor.handle_events calls pygame.event.get() which will be empty if we call it again.
                # I should have modified RoomEditor to accept events. 
                # Wait, I didn't modify handle_events to accept events. It calls pygame.event.get().
                # This is a conflict. 
                # I should just let the editor RUN its own loop until it exits.
                
                if self.editor.running:
                    self.editor.run()
                    # When run() returns, it means editor exited
                    # When run() returns, it means editor exited
                    if hasattr(self.editor, 'from_world_editor') and self.editor.from_world_editor:
                        self.editor = None
                        self.start_world_editor()
                    else:
                        self.state = "main_menu"
                        self.editor = None
                        # Re-init display if needed or ensure menu is ready
                        self.main_menu = MainMenu(self)
                else:
                    self.state = "main_menu"
            elif self.state == "world_editor":
                if self.world_editor.running:
                    self.world_editor.run() # Assuming WorldEditor also has a run() method that loops
                    # Wait, WorldEditor has a loop in run(), but if we want it integrated, we should probably
                    # use update/draw like we tried with RoomEditor but failed due to dependencies.
                    # Since RoomEditor works by calling .run() (which has its own loop), let's do the same for WorldEditor.
                    # WorldEditor's run() method should be compatible.
                    
                    if self.world_editor.room_to_edit:
                         # Transition to room editor
                        room_file = self.world_editor.room_to_edit
                        self.world_editor = None # Clean up world editor? Or keep it?
                        # It's better to keep it if we want to preserve state (camera, selection)
                        # But self.world_editor is currently re-created in start_world_editor?
                        # start_world_editor re-creates it. 
                        # To preserve state, we should probably not destroy it, or save state.
                        # For now, let's just pass the file and when returning, we restart world editor.
                        # The user asked for "easly menuvering".
                        
                        self.start_editor(room_file)
                        # Mark that we came from world editor so we can go back
                        self.editor.from_world_editor = True
                    else:
                        self.state = "main_menu"
                        self.world_editor = None
                        self.main_menu = MainMenu(self)
                else:
                    self.state = "main_menu"
            
            pygame.display.flip()
        
        pygame.quit()
    
    def update_game(self, events, dt):
        controls = self.settings.get("controls")
        
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == controls["pause"] or event.key == pygame.K_ESCAPE:
                    self.state = "paused"
                    self.pause_menu = PauseMenu(self) # Reset pause menu state
                    return
                elif event.key == pygame.K_r:
                    if self.room_manager.chapter:
                        spawn = self.room_manager.chapter.spawn
                        self.player = Player(spawn[0], spawn[1])
        
        self.player.update(dt, self.room_manager, controls, self.camera)
        
        transition = self.room_manager.check_room_transition(self.player.rect)
        if transition and not self.camera.transitioning:
            room_id, direction = transition
            self.player.start_transition(direction)
            self.room_manager.transition_to(room_id, direction, self.player.end_transition)
        
        cx, cy = self.player.center
        self.camera.follow(cx, cy, dt)
    
    def draw_game(self):
        self.screen.fill((15, 15, 25))
        self.room_manager.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)
        
        # Aim indicator
        if self.player.grapple.state == "inactive":
            self._draw_aim_indicator()
        
        if self.show_debug:
            self._draw_debug()
        
        self._draw_controls()
    
    def _draw_aim_indicator(self):
        """Draw subtle aim dots."""
        mouse_pos = pygame.mouse.get_pos()
        player_screen = self.camera.apply(self.player.center)
        
        dx = mouse_pos[0] - player_screen[0]
        dy = mouse_pos[1] - player_screen[1]
        dist = (dx * dx + dy * dy) ** 0.5
        
        if dist > 30:
            dx /= dist
            dy /= dist
            for i in range(0, min(int(dist), 120), 20):
                x = player_screen[0] + dx * i
                y = player_screen[1] + dy * i
                pygame.draw.circle(self.screen, (70, 70, 90), (int(x), int(y)), 2)
    
    def _draw_debug(self):
        font = pygame.font.Font(None, 22)
        y = 8
        
        # FPS
        fps = int(self.clock.get_fps())
        color = (100, 255, 100) if fps >= 55 else (255, 200, 100) if fps >= 30 else (255, 100, 100)
        self._text(font, f"FPS: {fps}", 8, y, color)
        y += 16
        
        # State
        states = []
        if self.player.rolling:
            states.append("ROLLING")
        elif self.player.on_ground:
            states.append("GROUND")
        elif self.player.wall_dir != 0:
            states.append(f"WALL {'L' if self.player.wall_dir < 0 else 'R'}")
        else:
            states.append("AIR")
        
        if self.player.sprinting:
            states.append("SPRINT")
        
        if self.player.grapple.state != "inactive":
            states.append(f"GRAPPLE:{self.player.grapple.state}")
        
        self._text(font, " | ".join(states), 8, y, (150, 150, 150))
        y += 16
        
        # Velocity
        speed = int((self.player.vx ** 2 + self.player.vy ** 2) ** 0.5)
        self._text(font, f"Vel: ({int(self.player.vx)}, {int(self.player.vy)}) = {speed}", 8, y, (120, 120, 120))
    
    def _draw_controls(self):
        font = pygame.font.Font(None, 18)
        hints = [
            "WASD: Move | SPACE: Jump | SHIFT: Sprint (ground) / Grapple (aim) | RMB: Grapple",
            "CTRL/LMB: Roll/Dash (i-frames) | Hold S while grappling: Swing mode",
            "R: Reset | F3: Debug | ESC: Menu"
        ]
        y = self.height - 46
        for hint in hints:
            self._text(font, hint, 8, y, (60, 60, 80))
            y += 14
    
    def _text(self, font, text, x, y, color):
        surf = font.render(text, True, color)
        self.screen.blit(surf, (x, y))


if __name__ == "__main__":
    game = Game()
    game.run()