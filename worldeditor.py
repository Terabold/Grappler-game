#!/usr/bin/env python3
"""
World Editor - Connect rooms together to create your game world
Optimized for large numbers of rooms using pre-rendered surfaces
"""

import pygame
import json
import os
import sys

# ============================================================================
# CONSTANTS
# ============================================================================

TILE_SIZE = 32
GRID_SNAP = 32  # Snap to tile grid

# Colors
COLOR_BG = (15, 15, 20)
COLOR_GRID_MINOR = (25, 25, 32)
COLOR_GRID_MAJOR = (35, 35, 45)
COLOR_GRID_ROOM = (50, 50, 65)
COLOR_PANEL = (30, 30, 38)
COLOR_TEXT = (220, 220, 220)
COLOR_TEXT_DIM = (100, 100, 110)
COLOR_BUTTON = (45, 45, 58)
COLOR_BUTTON_HOVER = (60, 60, 78)
COLOR_ACCENT = (220, 70, 70)
COLOR_ACCENT_DIM = (150, 50, 50)
COLOR_START = (70, 180, 70)
COLOR_CONNECTION = (80, 130, 180)
COLOR_SPAWN = (255, 210, 50)

# Tile colors
TILE_COLORS = {
    0: (22, 22, 28),      # Empty - darker
    1: (55, 55, 65),      # Solid
    2: (180, 45, 45),     # Spike
    3: (45, 130, 180),    # Grapple
    4: (45, 180, 70),     # Exit
    5: (100, 75, 45),     # Platform
}

TILE_GRID_COLOR = (35, 35, 42)

# ============================================================================
# ROOM WITH PRE-RENDERED SURFACE
# ============================================================================

class RoomPlacement:
    """A room with pre-rendered surface for fast drawing."""
    
    def __init__(self, room_id, filename, x=0, y=0):
        self.room_id = room_id
        self.filename = filename
        self.x = x
        self.y = y
        
        # Room data
        self.tile_width = 20
        self.tile_height = 12
        self.tiles = []
        self.spawn_x = 2
        self.spawn_y = 10
        
        # Pixel dimensions
        self.width = self.tile_width * TILE_SIZE
        self.height = self.tile_height * TILE_SIZE
        
        # Pre-rendered surface (created after loading)
        self.surface = None
        self.surface_with_grid = None
        
        self._load()
        self._render_surface()
    
    def _load(self):
        """Load room data from JSON."""
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
            
            self.tile_width = data.get('width', 20)
            self.tile_height = data.get('height', 12)
            self.width = self.tile_width * TILE_SIZE
            self.height = self.tile_height * TILE_SIZE
            
            # Initialize tiles
            self.tiles = [[0] * self.tile_width for _ in range(self.tile_height)]
            
            # Parse layers
            for layer in data.get('layers', []):
                layer_type = layer.get('type', '')
                layer_name = layer.get('name', '').lower()
                
                if layer_type == 'tilelayer' and 'collision' in layer_name:
                    tile_data = layer.get('data', [])
                    for y in range(self.tile_height):
                        for x in range(self.tile_width):
                            idx = y * self.tile_width + x
                            if idx < len(tile_data):
                                self.tiles[y][x] = tile_data[idx]
                
                elif layer_type == 'objectgroup':
                    for obj in layer.get('objects', []):
                        obj_name = obj.get('name', '').lower()
                        obj_type = obj.get('type', '').lower()
                        if 'spawn' in obj_name or 'spawn' in obj_type:
                            self.spawn_x = int(obj.get('x', 64)) // TILE_SIZE
                            self.spawn_y = int(obj.get('y', 320)) // TILE_SIZE
            
            print(f"Loaded {self.room_id}: {self.tile_width}x{self.tile_height}, tiles found: {sum(1 for row in self.tiles for t in row if t != 0)}")
            
        except Exception as e:
            print(f"Error loading {self.filename}: {e}")
            self.tiles = [[0] * self.tile_width for _ in range(self.tile_height)]
    
    def _render_surface(self):
        """Pre-render room to surface for fast blitting."""
        # Surface without grid (for zoomed out view)
        self.surface = pygame.Surface((self.width, self.height))
        self.surface.fill(TILE_COLORS[0])
        
        # Surface with grid (for zoomed in view)
        self.surface_with_grid = pygame.Surface((self.width, self.height))
        self.surface_with_grid.fill(TILE_COLORS[0])
        
        # Draw tiles
        for y in range(self.tile_height):
            for x in range(self.tile_width):
                tile = self.tiles[y][x]
                rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                
                color = TILE_COLORS.get(tile, TILE_COLORS[1])
                pygame.draw.rect(self.surface, color, rect)
                pygame.draw.rect(self.surface_with_grid, color, rect)
                
                # Platform top highlight
                if tile == 5:
                    top_rect = pygame.Rect(rect.x, rect.y, TILE_SIZE, 4)
                    pygame.draw.rect(self.surface, (140, 105, 60), top_rect)
                    pygame.draw.rect(self.surface_with_grid, (140, 105, 60), top_rect)
        
        # Draw grid on grid surface
        for x in range(self.tile_width + 1):
            px = x * TILE_SIZE
            pygame.draw.line(self.surface_with_grid, TILE_GRID_COLOR, (px, 0), (px, self.height))
        for y in range(self.tile_height + 1):
            py = y * TILE_SIZE
            pygame.draw.line(self.surface_with_grid, TILE_GRID_COLOR, (0, py), (self.width, py))
        
        # Draw spawn on both
        spawn_rect = pygame.Rect(
            self.spawn_x * TILE_SIZE + 6,
            self.spawn_y * TILE_SIZE + 6,
            TILE_SIZE - 12,
            TILE_SIZE - 12
        )
        pygame.draw.rect(self.surface, COLOR_SPAWN, spawn_rect)
        pygame.draw.rect(self.surface_with_grid, COLOR_SPAWN, spawn_rect)
    
    def reload(self):
        """Reload from file and re-render."""
        self._load()
        self._render_surface()
    
    def get_rect(self):
        """Get world rect."""
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    def to_dict(self):
        """For JSON serialization."""
        return {
            "id": self.room_id,
            "file": os.path.basename(self.filename),
            "x": self.x,
            "y": self.y
        }


# ============================================================================
# WORLD DATA
# ============================================================================

class WorldData:
    """Manages all rooms in the world."""
    
    def __init__(self, rooms_dir):
        self.rooms_dir = rooms_dir
        self.rooms = []
        self.start_room = None
        self.filename = None
        self.modified = False
    
    def add_room(self, filename):
        """Add a room from file."""
        base_name = os.path.splitext(os.path.basename(filename))[0]
        room_id = base_name
        
        # Ensure unique ID
        existing = {r.room_id for r in self.rooms}
        counter = 1
        while room_id in existing:
            room_id = f"{base_name}_{counter}"
            counter += 1
        
        # Position next to last room
        x, y = 0, 0
        if self.rooms:
            last = self.rooms[-1]
            x = last.x + last.width
            y = last.y
        
        room = RoomPlacement(room_id, filename, x, y)
        self.rooms.append(room)
        
        if not self.start_room:
            self.start_room = room_id
        
        self.modified = True
        return room
    
    def remove_room(self, room):
        """Remove a room."""
        if room in self.rooms:
            self.rooms.remove(room)
            if self.start_room == room.room_id and self.rooms:
                self.start_room = self.rooms[0].room_id
            elif not self.rooms:
                self.start_room = None
            self.modified = True
    
    def get_connections(self):
        """Find connected room pairs."""
        connections = []
        tolerance = 10
        
        for i, r1 in enumerate(self.rooms):
            rect1 = r1.get_rect()
            for r2 in self.rooms[i+1:]:
                rect2 = r2.get_rect()
                
                # Horizontal adjacency
                h_touch = (abs(rect1.right - rect2.left) <= tolerance or 
                          abs(rect2.right - rect1.left) <= tolerance)
                h_overlap = rect1.top < rect2.bottom and rect1.bottom > rect2.top
                
                # Vertical adjacency
                v_touch = (abs(rect1.bottom - rect2.top) <= tolerance or
                          abs(rect2.bottom - rect1.top) <= tolerance)
                v_overlap = rect1.left < rect2.right and rect1.right > rect2.left
                
                if (h_touch and h_overlap) or (v_touch and v_overlap):
                    connections.append((r1, r2))
        
        return connections
    
    def snap_room(self, room):
        """Snap room to grid."""
        room.x = round(room.x / GRID_SNAP) * GRID_SNAP
        room.y = round(room.y / GRID_SNAP) * GRID_SNAP
    
    def save(self, filepath):
        """Save to JSON."""
        data = {
            "start": self.start_room,
            "rooms": [r.to_dict() for r in self.rooms]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        self.filename = filepath
        self.modified = False
    
    def load(self, filepath):
        """Load from JSON."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.rooms = []
        self.start_room = data.get('start')
        
        for rd in data.get('rooms', []):
            room_file = os.path.join(self.rooms_dir, rd.get('file', ''))
            if os.path.exists(room_file):
                room = RoomPlacement(
                    rd.get('id'),
                    room_file,
                    rd.get('x', 0),
                    rd.get('y', 0)
                )
                self.rooms.append(room)
        
        self.filename = filepath
        self.modified = False


# ============================================================================
# UI COMPONENTS
# ============================================================================

class Button:
    def __init__(self, x, y, w, h, text, callback=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        self.hovered = False
    
    def update(self, mouse_pos, clicked):
        self.hovered = self.rect.collidepoint(mouse_pos)
        if self.hovered and clicked and self.callback:
            self.callback()
            return True
        return False
    
    def draw(self, surface, font):
        color = COLOR_BUTTON_HOVER if self.hovered else COLOR_BUTTON
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, COLOR_ACCENT if self.hovered else (55, 55, 65), self.rect, 1)
        
        text = font.render(self.text, True, COLOR_TEXT)
        surface.blit(text, text.get_rect(center=self.rect.center))


class FileList:
    def __init__(self, x, y, w, h, rooms_dir):
        self.rect = pygame.Rect(x, y, w, h)
        self.rooms_dir = rooms_dir
        self.files = []
        self.scroll = 0
        self.selected = None
        self.item_height = 22
        self.refresh()
    
    def refresh(self):
        self.files = []
        if os.path.exists(self.rooms_dir):
            for f in sorted(os.listdir(self.rooms_dir)):
                if f.endswith('.json') and f != 'world.json':
                    self.files.append(f)
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            if event.button == 4:
                self.scroll = max(0, self.scroll - self.item_height)
            elif event.button == 5:
                max_scroll = max(0, len(self.files) * self.item_height - self.rect.height)
                self.scroll = min(max_scroll, self.scroll + self.item_height)
            elif event.button == 1:
                rel_y = event.pos[1] - self.rect.y + self.scroll
                idx = int(rel_y // self.item_height)
                if 0 <= idx < len(self.files):
                    self.selected = idx
                    return os.path.join(self.rooms_dir, self.files[idx])
        return None
    
    def draw(self, surface, font):
        pygame.draw.rect(surface, (20, 20, 25), self.rect)
        pygame.draw.rect(surface, (50, 50, 60), self.rect, 1)
        
        clip = surface.get_clip()
        surface.set_clip(self.rect)
        
        for i, f in enumerate(self.files):
            y = self.rect.y + i * self.item_height - self.scroll
            if y < self.rect.y - self.item_height or y > self.rect.bottom:
                continue
            
            if i == self.selected:
                pygame.draw.rect(surface, COLOR_BUTTON_HOVER, 
                               (self.rect.x, y, self.rect.width, self.item_height))
            
            text = font.render(f, True, COLOR_TEXT)
            surface.blit(text, (self.rect.x + 5, y + 3))
        
        surface.set_clip(clip)


# ============================================================================
# WORLD EDITOR
# ============================================================================

class WorldEditor:
    def __init__(self, rooms_dir="rooms", game=None):
        if game:
            self.game = game
            self.screen = game.screen
            self.rooms_dir = os.path.join(os.path.dirname(__file__), "rooms")
        else:
            pygame.init()
            self.game = None
            self.screen = pygame.display.set_mode((1400, 800), pygame.RESIZABLE)
            pygame.display.set_caption("World Editor")
            self.rooms_dir = rooms_dir
            
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.font = pygame.font.Font(None, 18)
        self.font_large = pygame.font.Font(None, 26)
        
        os.makedirs(self.rooms_dir, exist_ok=True)
        
        self.world = WorldData(self.rooms_dir)
        
        # Camera
        self.camera_x = 300
        self.camera_y = 100
        self.zoom = 0.5
        self.min_zoom = 0.05
        self.max_zoom = 2.0
        self.dragging_view = False
        self.last_mouse = (0, 0)
        
        # Selection
        self.selected_room = None
        self.dragging_room = False
        self.drag_offset = (0, 0)
        self.room_to_edit = None
        
        # Double-click detection
        self.last_click_time = 0
        self.last_click_room = None
        
        # UI
        self.panel_width = 240  # Increased from 220
        self.show_grid = True
        self.setup_ui()
        
        # Message
        self.message = ""
        self.message_time = 0
        
        # Scaled surface cache for performance
        self.scale_cache = {}
        self.cache_zoom = 0
        
        # Load existing world
        world_path = os.path.join(self.rooms_dir, "world.json")
        if os.path.exists(world_path):
            self.world.load(world_path)
            self.center_view()
    
    def setup_ui(self):
        x = 10
        w = 220  # Widen buttons slightly since panel is wider
        
        # Increase Y position and height for file list to avoid overlap with top labels
        self.file_list = FileList(x, 60, w, 280, self.rooms_dir)
        
        # Start buttons lower down
        y = 360
        btn_h = 28
        spacing = 34
        
        # Split into two columns for top buttons
        half_w = (w - 10) // 2
        
        self.buttons = [
            Button(x, y, half_w, btn_h, "Add Room", self.add_room),
            Button(x + half_w + 10, y, half_w, btn_h, "Refresh", self.refresh_files),
            
            Button(x, y + spacing, half_w, btn_h, "Set Start", self.set_start),
            Button(x + half_w + 10, y + spacing, half_w, btn_h, "Remove", self.remove_room),
            
            Button(x, y + spacing*2 + 10, w, btn_h, "Reload All", self.reload_rooms),
            Button(x, y + spacing*3 + 10, w, btn_h, "Toggle Grid", self.toggle_grid),
            Button(x, y + spacing*4 + 10, w, btn_h, "Save World", self.save_world),
            Button(x, y + spacing*5 + 10, w, btn_h, "Load World", self.load_world),
            
            # Button(x, y + spacing*6 + 10, w, btn_h, "Room Editor", self.open_room_editor), # Remove external call if integrated, or keep separate?
            # Let's keep it but maybe it switches state if integrated? For now, standard behavior.
            
            # Back button at the bottom
            Button(x, self.screen.get_height() - 40, w, 30, "Back to Menu", self.exit_editor)
        ]
        
    def exit_editor(self):
        self.running = False
    
    def clear_cache(self):
        """Clear scaled surface cache."""
        self.scale_cache = {}
        self.cache_zoom = 0
    
    def show_msg(self, text):
        self.message = text
        self.message_time = 2.0
    
    def add_room(self):
        if self.file_list.selected is not None:
            path = os.path.join(self.rooms_dir, self.file_list.files[self.file_list.selected])
            room = self.world.add_room(path)
            self.selected_room = room
            self.clear_cache()
            self.show_msg(f"Added {room.room_id}")
    
    def refresh_files(self):
        self.file_list.refresh()
        self.show_msg("Refreshed file list")
    
    def set_start(self):
        if self.selected_room:
            self.world.start_room = self.selected_room.room_id
            self.world.modified = True
            self.show_msg(f"Start: {self.selected_room.room_id}")
    
    def remove_room(self):
        if self.selected_room:
            self.world.remove_room(self.selected_room)
            self.selected_room = None
            self.clear_cache()
            self.show_msg("Removed room")
    
    def reload_rooms(self):
        for room in self.world.rooms:
            room.reload()
        self.clear_cache()
        self.show_msg("Reloaded all rooms")
    
    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.clear_cache()
        self.show_msg(f"Grid: {'ON' if self.show_grid else 'OFF'}")
    
    def save_world(self):
        path = os.path.join(self.rooms_dir, "world.json")
        self.world.save(path)
        self.show_msg("Saved world.json")
    
    def load_world(self):
        path = os.path.join(self.rooms_dir, "world.json")
        if os.path.exists(path):
            self.world.load(path)
            self.clear_cache()
            self.center_view()
            self.show_msg("Loaded world.json")
    
    def open_room_editor(self):
        import subprocess
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roomeditor.py")
        subprocess.Popen([sys.executable, script, self.rooms_dir])
    
    def open_room_editor_for_room(self, room):
        from roomeditor import RoomEditor
        editor = RoomEditor(rooms_dir=self.rooms_dir, game=self)
        editor.room.load(room.filename)
        editor.width_input.set_value(editor.room.width)
        editor.height_input.set_value(editor.room.height)
        editor.center_view()
        editor.run()
        # After editing, reload the room in world editor
        room.reload()
    
    def center_view(self):
        if not self.world.rooms:
            self.camera_x = self.panel_width + 50
            self.camera_y = 50
            return
        
        min_x = min(r.x for r in self.world.rooms)
        min_y = min(r.y for r in self.world.rooms)
        max_x = max(r.x + r.width for r in self.world.rooms)
        max_y = max(r.y + r.height for r in self.world.rooms)
        
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        
        canvas_w = self.screen.get_width() - self.panel_width
        canvas_h = self.screen.get_height()
        
        self.camera_x = self.panel_width + canvas_w / 2 - cx * self.zoom
        self.camera_y = canvas_h / 2 - cy * self.zoom
    
    def world_to_screen(self, wx, wy):
        return (wx * self.zoom + self.camera_x, wy * self.zoom + self.camera_y)
    
    def screen_to_world(self, sx, sy):
        return ((sx - self.camera_x) / self.zoom, (sy - self.camera_y) / self.zoom)
    
    def get_room_at(self, sx, sy):
        wx, wy = self.screen_to_world(sx, sy)
        for room in reversed(self.world.rooms):
            if room.get_rect().collidepoint(wx, wy):
                return room
        return None
    
    def handle_events(self):
        mouse = pygame.mouse.get_pos()
        clicked = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                if self.game:
                    self.game.running = False
                return
            
            self.file_list.handle_event(event)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                clicked = True
                
                if event.pos[0] > self.panel_width:
                    if event.button == 1:
                        room = self.get_room_at(*event.pos)
                        if room:
                            current_time = pygame.time.get_ticks()
                            if self.last_click_room == room and current_time - self.last_click_time < 400:
                                # Double click - open room editor
                                self.open_room_editor_for_room(room)
                            else:
                                self.selected_room = room
                                self.dragging_room = True
                                wx, wy = self.screen_to_world(*event.pos)
                                self.drag_offset = (wx - room.x, wy - room.y)
                            self.last_click_time = current_time
                            self.last_click_room = room
                        else:
                            self.selected_room = None
                    
                    elif event.button == 3:
                        self.dragging_view = True
                        self.last_mouse = event.pos
                    
                    elif event.button == 4:  # Zoom in
                        mx, my = event.pos
                        old_wx, old_wy = self.screen_to_world(mx, my)
                        self.zoom = min(self.max_zoom, self.zoom * 1.15)
                        new_sx, new_sy = self.world_to_screen(old_wx, old_wy)
                        self.camera_x += mx - new_sx
                        self.camera_y += my - new_sy
                        self.clear_cache()
                    
                    elif event.button == 5:  # Zoom out
                        mx, my = event.pos
                        old_wx, old_wy = self.screen_to_world(mx, my)
                        self.zoom = max(self.min_zoom, self.zoom / 1.15)
                        new_sx, new_sy = self.world_to_screen(old_wx, old_wy)
                        self.camera_x += mx - new_sx
                        self.camera_y += my - new_sy
                        self.clear_cache()
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    # Double click to edit room
                    if hasattr(self, '_last_click_time'):
                        if pygame.time.get_ticks() - self._last_click_time < 400:
                            # Check if clicked a room
                            room = self.get_room_at(*event.pos)
                            if room:
                                self.room_to_edit = room.filename
                                self.running = False # Exit run loop
                                return
                    self._last_click_time = pygame.time.get_ticks()

                    if self.dragging_room and self.selected_room:
                        self.world.snap_room(self.selected_room)
                        self.world.modified = True
                    self.dragging_room = False
                
                elif event.button == 3:
                    self.dragging_view = False
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging_view:
                    dx = event.pos[0] - self.last_mouse[0]
                    dy = event.pos[1] - self.last_mouse[1]
                    self.camera_x += dx
                    self.camera_y += dy
                    self.last_mouse = event.pos
                
                elif self.dragging_room and self.selected_room:
                    wx, wy = self.screen_to_world(*event.pos)
                    self.selected_room.x = wx - self.drag_offset[0]
                    self.selected_room.y = wy - self.drag_offset[1]
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DELETE and self.selected_room:
                    self.remove_room()
                elif event.key == pygame.K_HOME:
                    self.center_view()
                elif event.key == pygame.K_g:
                    self.toggle_grid()
                elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
                    self.save_world()
                elif event.key == pygame.K_r and event.mod & pygame.KMOD_CTRL:
                    self.reload_rooms()
                elif event.key == pygame.K_ESCAPE:
                    self.exit_editor()
            
            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        
        for btn in self.buttons:
            btn.update(mouse, clicked)
    
    def update(self, dt):
        if self.message_time > 0:
            self.message_time -= dt
    
    def draw(self):
        self.screen.fill(COLOR_BG)
        
        # Canvas
        self.draw_canvas()
        
        # Panel
        self.draw_panel()
        
        # Message
        if self.message_time > 0:
            text = self.font_large.render(self.message, True, COLOR_TEXT)
            rect = text.get_rect(
                centerx=self.panel_width + (self.screen.get_width() - self.panel_width) // 2,
                bottom=self.screen.get_height() - 15
            )
            bg = rect.inflate(16, 8)
            pygame.draw.rect(self.screen, COLOR_PANEL, bg)
            pygame.draw.rect(self.screen, COLOR_ACCENT_DIM, bg, 1)
            self.screen.blit(text, rect)
        
        pygame.display.flip()
    
    def draw_canvas(self):
        """Draw the world view with rooms."""
        canvas = pygame.Rect(self.panel_width, 0, 
                            self.screen.get_width() - self.panel_width,
                            self.screen.get_height())
        
        # Background grid (room-sized)
        room_grid = 640 * self.zoom  # One room width
        if room_grid > 30:
            start_x = (self.panel_width - self.camera_x) % room_grid + self.panel_width - room_grid
            start_y = -self.camera_y % room_grid - room_grid
            
            x = start_x
            while x < self.screen.get_width():
                if x >= self.panel_width:
                    pygame.draw.line(self.screen, COLOR_GRID_ROOM, (x, 0), (x, self.screen.get_height()))
                x += room_grid
            
            y = start_y
            while y < self.screen.get_height():
                pygame.draw.line(self.screen, COLOR_GRID_ROOM, (self.panel_width, y), (self.screen.get_width(), y))
                y += room_grid
        
        # Draw connections
        for r1, r2 in self.world.get_connections():
            c1 = self.world_to_screen(r1.x + r1.width/2, r1.y + r1.height/2)
            c2 = self.world_to_screen(r2.x + r2.width/2, r2.y + r2.height/2)
            pygame.draw.line(self.screen, COLOR_CONNECTION, c1, c2, max(1, int(3 * self.zoom)))
        
        # Draw rooms
        for room in self.world.rooms:
            self.draw_room(room)
        
        # Origin marker
        ox, oy = self.world_to_screen(0, 0)
        if self.panel_width - 10 < ox < self.screen.get_width() + 10 and -10 < oy < self.screen.get_height() + 10:
            pygame.draw.circle(self.screen, COLOR_ACCENT, (int(ox), int(oy)), 6)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(ox), int(oy)), 3)
    
    def get_scaled_surface(self, room):
        """Get or create cached scaled surface for room."""
        sw = int(room.width * self.zoom)
        sh = int(room.height * self.zoom)
        
        if sw <= 0 or sh <= 0:
            return None
        
        # Cache key includes room id and grid setting
        cache_key = (room.room_id, self.show_grid and self.zoom >= 0.3)
        
        # Check if cache is valid
        if self.cache_zoom != self.zoom:
            self.scale_cache = {}
            self.cache_zoom = self.zoom
        
        if cache_key not in self.scale_cache:
            use_grid = self.show_grid and self.zoom >= 0.3
            source = room.surface_with_grid if use_grid else room.surface
            self.scale_cache[cache_key] = pygame.transform.scale(source, (sw, sh))
        
        return self.scale_cache[cache_key]
    
    def draw_room(self, room):
        """Draw a room using pre-rendered surface."""
        sx, sy = self.world_to_screen(room.x, room.y)
        sw = int(room.width * self.zoom)
        sh = int(room.height * self.zoom)
        
        screen_rect = pygame.Rect(sx, sy, sw, sh)
        
        # Skip if off screen
        if screen_rect.right < self.panel_width or screen_rect.left > self.screen.get_width():
            return
        if screen_rect.bottom < 0 or screen_rect.top > self.screen.get_height():
            return
        
        # Get cached scaled surface
        scaled = self.get_scaled_surface(room)
        if scaled:
            self.screen.blit(scaled, (sx, sy))
        
        # Border
        is_selected = room == self.selected_room
        is_start = room.room_id == self.world.start_room
        
        if is_selected:
            border_color = COLOR_ACCENT
            border_width = 3
        elif is_start:
            border_color = COLOR_START
            border_width = 2
        else:
            border_color = (70, 70, 85)
            border_width = 1
        
        pygame.draw.rect(self.screen, border_color, screen_rect, border_width)
        
        # Label
        if sw > 50:
            label = self.font.render(room.room_id, True, COLOR_TEXT)
            label_rect = label.get_rect(centerx=screen_rect.centerx, top=screen_rect.top + 4)
            
            # Label background
            bg = label_rect.inflate(8, 4)
            pygame.draw.rect(self.screen, (25, 25, 30), bg)
            self.screen.blit(label, label_rect)
        
        # Start indicator
        if is_start and sw > 30:
            star = self.font_large.render("★", True, COLOR_SPAWN)
            self.screen.blit(star, (screen_rect.x + 4, screen_rect.y + 2))
    
    def draw_panel(self):
        """Draw side panel."""
        panel = pygame.Rect(0, 0, self.panel_width, self.screen.get_height())
        pygame.draw.rect(self.screen, COLOR_PANEL, panel)
        pygame.draw.line(self.screen, (50, 50, 60), 
                        (self.panel_width, 0), (self.panel_width, self.screen.get_height()))
        
        # Title
        title = self.font_large.render("World Editor", True, COLOR_TEXT)
        self.screen.blit(title, (10, 12))
        
        # Files label
        label = self.font.render("Room Files:", True, COLOR_TEXT_DIM)
        self.screen.blit(label, (10, 38))
        
        self.file_list.draw(self.screen, self.font)
        
        for btn in self.buttons:
            btn.draw(self.screen, self.font)
        
        # Info
        y = self.screen.get_height() - 110
        
        info = [
            f"Rooms: {len(self.world.rooms)}",
            f"Start: {self.world.start_room or 'None'}",
            f"Zoom: {self.zoom:.2f}x",
        ]
        
        if self.selected_room:
            info.append(f"Sel: {self.selected_room.room_id}")
            info.append(f"Pos: {int(self.selected_room.x)}, {int(self.selected_room.y)}")
        
        if self.world.modified:
            info.append("(modified)")
        
        for i, text in enumerate(info):
            color = COLOR_ACCENT if text == "(modified)" else COLOR_TEXT_DIM
            surf = self.font.render(text, True, color)
            self.screen.blit(surf, (10, y + i * 16))
        
        # Controls
        hint = self.font.render("Scroll=Zoom RMB=Pan G=Grid", True, (60, 60, 70))
        self.screen.blit(hint, (10, self.screen.get_height() - 18))
    
    def run(self):
        self.center_view()
        
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        
        if not self.game:
            pygame.quit()


if __name__ == "__main__":
    rooms_dir = sys.argv[1] if len(sys.argv) > 1 else "rooms"
    WorldEditor(rooms_dir).run()