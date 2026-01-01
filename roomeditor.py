#!/usr/bin/env python3
"""
Room Editor - Create and edit rooms for your game
Controls shown in the editor
"""

import pygame
import json
import os
import sys

# ============================================================================
# CONSTANTS
# ============================================================================

TILE_SIZE = 16
DEFAULT_ROOM_WIDTH = 40   # tiles
DEFAULT_ROOM_HEIGHT = 24  # tiles

# Tile types
TILE_EMPTY = 0
TILE_SOLID = 1
TILE_SPIKE = 2
TILE_GRAPPLE = 3
TILE_EXIT = 4
TILE_PLATFORM = 5
TILE_ICE = 6

# Object types
OBJ_PLATFORM = "platform"

TILE_NAMES = {
    TILE_EMPTY: "Empty",
    TILE_SOLID: "Solid",
    TILE_SPIKE: "Spike",
    TILE_GRAPPLE: "Grapple",
    TILE_EXIT: "Exit",
    TILE_PLATFORM: "Platform",
    TILE_ICE: "Ice",
}

TILE_COLORS = {
    TILE_EMPTY: (30, 30, 40),
    TILE_SOLID: (60, 60, 70),
    TILE_SPIKE: (200, 50, 50),
    TILE_GRAPPLE: (50, 150, 200),
    TILE_EXIT: (50, 200, 80),
    TILE_PLATFORM: (120, 90, 50),
    TILE_ICE: (100, 200, 255),
}

SUBGRID_SIZE = 16

# UI Colors
COLOR_BG = (20, 20, 25)
COLOR_GRID = (40, 40, 50)
COLOR_GRID_MAJOR = (60, 60, 70)
COLOR_TEXT = (220, 220, 220)
COLOR_TEXT_DIM = (120, 120, 120)
COLOR_PANEL = (35, 35, 45)
COLOR_BUTTON = (50, 50, 65)
COLOR_BUTTON_HOVER = (70, 70, 90)
COLOR_BUTTON_ACTIVE = (100, 80, 80)
COLOR_ACCENT = (220, 80, 80)
COLOR_BUTTON_HOVER = (70, 70, 90)
COLOR_BUTTON_ACTIVE = (100, 80, 80)
COLOR_ACCENT = (220, 80, 80)
COLOR_SPAWN = (255, 220, 50)

# Layout
TOOLBAR_HEIGHT = 40
SIDEBAR_WIDTH = 240


# ============================================================================
# ROOM DATA
# ============================================================================

class RoomData:
    """Stores room tile data and metadata."""
    
    def __init__(self, width=DEFAULT_ROOM_WIDTH, height=DEFAULT_ROOM_HEIGHT):
        self.width = width
        self.height = height
        self.tiles = [[TILE_EMPTY] * width for _ in range(height)]
        self.objects = []  # List of dicts: {type, x, y, w, h}
        # Single spawn point: (x, y) in tile coordinates
        self.spawn = None  # Set to (x, y) when placed
        self.modified = False
        self.filename = None
    
    def resize(self, new_width, new_height):
        """Resize room, preserving existing tiles."""
        new_tiles = [[TILE_EMPTY] * new_width for _ in range(new_height)]
        
        for y in range(min(self.height, new_height)):
            for x in range(min(self.width, new_width)):
                new_tiles[y][x] = self.tiles[y][x]
        
        self.tiles = new_tiles
        self.width = new_width
        self.height = new_height
        
        # Keep spawn in bounds
        if self.spawn:
            x, y = self.spawn
            if x >= new_width or y >= new_height:
                self.spawn = None  # Remove spawn if out of bounds
            
        self.modified = True
    
    def set_tile(self, x, y, tile_type):
        """Set a tile, return True if changed."""
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.tiles[y][x] != tile_type:
                self.tiles[y][x] = tile_type
                self.modified = True
                return True
        return False
    
    def set_spawn(self, x, y):
        """Set spawn point."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.spawn = (x, y)
            self.modified = True
    
    def get_tile(self, x, y):
        """Get tile at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return TILE_EMPTY
    
    def get_spawn(self):
        """Get spawn point."""
        return self.spawn
    
    def clear_spawn(self):
        """Clear spawn point."""
        self.spawn = None
        self.modified = True
    
    def fill_borders(self):
        """Fill room borders with solid tiles."""
        for x in range(self.width):
            self.tiles[0][x] = TILE_SOLID
            self.tiles[self.height - 1][x] = TILE_SOLID
        for y in range(self.height):
            self.tiles[y][0] = TILE_SOLID
            self.tiles[y][self.width - 1] = TILE_SOLID
        self.modified = True
    
    def clear(self):
        """Clear all tiles and objects."""
        self.tiles = [[TILE_EMPTY] * self.width for _ in range(self.height)]
        self.objects = []
        self.modified = True
    
    def to_json(self):
        """Convert to JSON format for game."""
        # Flatten tile data
        data = []
        for row in self.tiles:
            data.extend(row)
        
        return {
            "width": self.width,
            "height": self.height,
            "tilewidth": TILE_SIZE,
            "tileheight": TILE_SIZE,
            "layers": [
                {
                    "name": "collision",
                    "type": "tilelayer",
                    "width": self.width,
                    "height": self.height,
                    "data": data
                },
                {
                    "name": "objects",
                    "type": "objectgroup",
                    "objects": [
                        {
                            "name": "spawn",
                            "type": "spawn",
                            "x": self.spawn[0] * TILE_SIZE,
                            "y": self.spawn[1] * TILE_SIZE
                        }
                    ] if self.spawn else []
                }
            ]
        }
        
        # Add other objects
        obj_layer = data["layers"][1]
        for obj in self.objects:
            obj_layer["objects"].append({
                "name": obj["type"],
                "type": obj["type"],
                "x": obj["x"],
                "y": obj["y"],
                "width": obj["w"],
                "height": obj["h"]
            })
            
        return data
    
    def from_json(self, data):
        """Load from JSON data."""
        self.width = data.get("width", DEFAULT_ROOM_WIDTH)
        self.height = data.get("height", DEFAULT_ROOM_HEIGHT)
        self.tiles = [[TILE_EMPTY] * self.width for _ in range(self.height)]
        
        for layer in data.get("layers", []):
            if layer.get("type") == "tilelayer" and "collision" in layer.get("name", "").lower():
                tile_data = layer.get("data", [])
                for y in range(self.height):
                    for x in range(self.width):
                        idx = y * self.width + x
                        if idx < len(tile_data):
                            self.tiles[y][x] = tile_data[idx]
            
            elif layer.get("type") == "objectgroup":
                for obj in layer.get("objects", []):
                    obj_type = obj.get("type", "").lower()
                    obj_name = obj.get("name", "").lower()
                    
                    # Load spawn point
                    if "spawn" in obj_type or "spawn" in obj_name:
                        x = int(obj.get("x", 64) // TILE_SIZE)
                        y = int(obj.get("y", 64) // TILE_SIZE)
                        self.spawn = (x, y)
                    elif obj_type == OBJ_PLATFORM:
                         self.objects.append({
                            "type": OBJ_PLATFORM,
                            "x": obj.get("x", 0),
                            "y": obj.get("y", 0),
                            "w": obj.get("width", 32),
                            "h": obj.get("height", 16)
                         })
        
        self.modified = False
    
    def save(self, filepath):
        """Save room to file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_json(), f, indent=2)
        self.filename = filepath
        self.modified = False
    
    def load(self, filepath):
        """Load room from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.from_json(data)
        self.filename = filepath
        self.modified = False


# ============================================================================
# AUTO-TILING
# ============================================================================

class AutoTiler:
    """Handles auto-tiling logic and assets."""
    
    def __init__(self):
        self.tilesets = {}
        self.load_assets()
        
    def load_assets(self):
        """Load tileset images."""
        try:
            # Load Ice tileset (3x3 grid)
            if os.path.exists("assets/tilesets/ice.png"):
                img = pygame.image.load("assets/tilesets/ice.png").convert_alpha()
                self.tilesets[TILE_ICE] = self.split_tileset(img, 32)
        except Exception as e:
            print(f"Error loading assets: {e}")

    def split_tileset(self, img, size):
        """Split 3x3 tileset into list of surfaces."""
        tiles = []
        for y in range(3):
            for x in range(3):
                rect = pygame.Rect(x*size, y*size, size, size)
                tiles.append(img.subsurface(rect))
        return tiles

    def get_tile_index(self, neighbors):
        """
        Get index (0-8) based on neighbors (T, B, L, R).
        neighbors: list of bools [Top, Bottom, Left, Right]
        """
        t, b, l, r = neighbors
        
        # Map neighbors to 3x3 grid index
        # Row 0 (Top): No top neighbor
        # Row 1 (Mid): Top and Bottom neighbors (or just Top) ? 
        # Actually logic is:
        # Top-Left (0): No Top, No Left
        # Top-Mid (1): No Top, Yes Left, Yes Right (or just Yes L/R?)
        
        # Simplified 3x3 Logic:
        # Y position determined by Top/Bottom
        # 0 (Top): No Top neighbor
        # 1 (Mid): Top and Bottom neighbors
        # 2 (Bot): No Bottom neighbor
        # Note: If no top AND no bottom -> Single vertical block? 
        # For 3x3, we usually assume connected blobs.
        
        col = 1
        if not l: col = 0
        elif not r: col = 2
        
        row = 1
        if not t: row = 0
        elif not b: row = 2
        
        return row * 3 + col

    def draw_tile(self, surface, tile_type, rect, neighbors):
        """Draw auto-tiled rect."""
        if tile_type in self.tilesets:
            idx = self.get_tile_index(neighbors)
            surface.blit(self.tilesets[tile_type][idx], rect)
        else:
            # Fallback
            pygame.draw.rect(surface, TILE_COLORS.get(tile_type, (255,0,255)), rect)

# ============================================================================
# UI COMPONENTS
# ============================================================================

class Button:
    """Simple clickable button."""
    
    def __init__(self, x, y, width, height, text, callback=None, toggle=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.toggle = toggle
        self.active = False
        self.hovered = False
        self.enabled = True
    
    def update(self, mouse_pos, mouse_clicked):
        """Update button state, return True if clicked."""
        self.hovered = self.rect.collidepoint(mouse_pos) and self.enabled
        
        if self.hovered and mouse_clicked and self.enabled:
            if self.toggle:
                self.active = not self.active
            if self.callback:
                self.callback()
            return True
        return False
    
    def draw(self, surface, font):
        """Draw button."""
        if not self.enabled:
            color = (30, 30, 35)
        elif self.active:
            color = COLOR_BUTTON_ACTIVE
        elif self.hovered:
            color = COLOR_BUTTON_HOVER
        else:
            color = COLOR_BUTTON
        
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, COLOR_GRID_MAJOR, self.rect, 1)
        
        text_color = COLOR_TEXT if self.enabled else COLOR_TEXT_DIM
        text_surf = font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)


class TileButton(Button):
    """Button for selecting tile type."""
    
    def __init__(self, x, y, size, tile_type):
        super().__init__(x, y, size, size, "", toggle=True)
        self.tile_type = tile_type
        self.size = size
    
    def draw(self, surface, font):
        """Draw tile button with color."""
        # Background
        if self.active:
            pygame.draw.rect(surface, COLOR_ACCENT, self.rect.inflate(4, 4))
        
        # Tile color
        pygame.draw.rect(surface, TILE_COLORS[self.tile_type], self.rect)
        
        # Border
        border_color = COLOR_TEXT if self.hovered else COLOR_GRID_MAJOR
        pygame.draw.rect(surface, border_color, self.rect, 2)
        
        # Label below
        label = TILE_NAMES[self.tile_type][:3].upper()
        text_surf = font.render(label, True, COLOR_TEXT_DIM)
        text_rect = text_surf.get_rect(centerx=self.rect.centerx, top=self.rect.bottom + 2)
        surface.blit(text_surf, text_rect)


class InputBox:
    """Text input box for numbers."""
    
    def __init__(self, x, y, width, height, initial_value="", label=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = str(initial_value)
        self.label = label
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0
    
    def handle_event(self, event):
        """Handle input events."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isdigit():
                self.text += event.unicode
        
        return False
    
    def get_value(self):
        """Get integer value."""
        try:
            return int(self.text) if self.text else 0
        except ValueError:
            return 0
    
    def set_value(self, value):
        """Set value."""
        self.text = str(value)
    
    def update(self, dt):
        """Update cursor blink."""
        self.cursor_timer += dt
        if self.cursor_timer > 0.5:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
    
    def draw(self, surface, font):
        """Draw input box."""
        # Label
        if self.label:
            label_surf = font.render(self.label, True, COLOR_TEXT_DIM)
            surface.blit(label_surf, (self.rect.x, self.rect.y - 18))
        
        # Box
        color = COLOR_BUTTON_HOVER if self.active else COLOR_BUTTON
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, COLOR_ACCENT if self.active else COLOR_GRID_MAJOR, self.rect, 1)
        
        # Text
        text_surf = font.render(self.text, True, COLOR_TEXT)
        surface.blit(text_surf, (self.rect.x + 5, self.rect.centery - text_surf.get_height() // 2))
        
        # Cursor
        if self.active and self.cursor_visible:
            cursor_x = self.rect.x + 5 + text_surf.get_width()
            pygame.draw.line(surface, COLOR_TEXT, 
                           (cursor_x, self.rect.y + 4), 
                           (cursor_x, self.rect.bottom - 4), 2)


class FileDialog:
    """Simple file browser dialog."""
    
    def __init__(self, x, y, width, height, directory, extension=".json", save_mode=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.directory = directory
        self.extension = extension
        self.save_mode = save_mode
        self.files = []
        self.scroll = 0
        self.selected = None
        self.filename_input = InputBox(x + 10, y + height - 70, width - 20, 28, "", "Filename:")
        self.active = False
        self.result = None
        self.refresh_files()
    
    def refresh_files(self):
        """Refresh file list."""
        self.files = []
        if os.path.exists(self.directory):
            for f in sorted(os.listdir(self.directory)):
                if f.endswith(self.extension):
                    self.files.append(f)
    
    def open(self, save_mode=False):
        """Open dialog."""
        self.save_mode = save_mode
        self.active = True
        self.result = None
        self.selected = None
        self.refresh_files()
        if save_mode:
            self.filename_input.text = "room_01.json"
    
    def close(self):
        """Close dialog."""
        self.active = False
    
    def handle_event(self, event):
        """Handle events, return filepath if confirmed."""
        if not self.active:
            return None
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.rect.collidepoint(event.pos):
                self.close()
                return None
            
            # Check file list clicks
            list_rect = pygame.Rect(self.rect.x + 10, self.rect.y + 40, 
                                   self.rect.width - 20, self.rect.height - 130)
            if list_rect.collidepoint(event.pos):
                rel_y = event.pos[1] - list_rect.y + self.scroll
                idx = rel_y // 24
                if 0 <= idx < len(self.files):
                    self.selected = idx
                    if not self.save_mode:
                        self.filename_input.text = self.files[idx]
            
            # Check scroll
            if event.button == 4:  # Scroll up
                self.scroll = max(0, self.scroll - 24)
            elif event.button == 5:  # Scroll down
                max_scroll = max(0, len(self.files) * 24 - (self.rect.height - 130))
                self.scroll = min(max_scroll, self.scroll + 24)
        
        # Filename input
        if self.save_mode:
            self.filename_input.handle_event(event)
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return None
            elif event.key == pygame.K_RETURN:
                return self._confirm()
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Double click to confirm
            if hasattr(self, '_last_click_time'):
                if pygame.time.get_ticks() - self._last_click_time < 400:
                    return self._confirm()
            self._last_click_time = pygame.time.get_ticks()
        
        return None
    
    def _confirm(self):
        """Confirm selection."""
        if self.save_mode:
            filename = self.filename_input.text
            if not filename.endswith(self.extension):
                filename += self.extension
        else:
            if self.selected is not None:
                filename = self.files[self.selected]
            else:
                return None
        
        self.result = os.path.join(self.directory, filename)
        self.close()
        return self.result
    
    def update(self, dt):
        """Update dialog."""
        if self.save_mode:
            self.filename_input.update(dt)
    
    def draw(self, surface, font):
        """Draw dialog."""
        if not self.active:
            return
        
        # Dim background
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surface.blit(dim, (0, 0))
        
        # Dialog box
        pygame.draw.rect(surface, COLOR_PANEL, self.rect)
        pygame.draw.rect(surface, COLOR_ACCENT, self.rect, 2)
        
        # Title
        title = "Save Room" if self.save_mode else "Open Room"
        title_surf = font.render(title, True, COLOR_TEXT)
        surface.blit(title_surf, (self.rect.x + 10, self.rect.y + 10))
        
        # File list
        list_rect = pygame.Rect(self.rect.x + 10, self.rect.y + 40,
                               self.rect.width - 20, self.rect.height - 130)
        pygame.draw.rect(surface, COLOR_BG, list_rect)
        
        # Clip to list area
        clip = surface.get_clip()
        surface.set_clip(list_rect)
        
        for i, filename in enumerate(self.files):
            y = list_rect.y + i * 24 - self.scroll
            if y < list_rect.y - 24 or y > list_rect.bottom:
                continue
            
            if i == self.selected:
                pygame.draw.rect(surface, COLOR_BUTTON_HOVER,
                               (list_rect.x, y, list_rect.width, 24))
            
            text_surf = font.render(filename, True, COLOR_TEXT)
            surface.blit(text_surf, (list_rect.x + 5, y + 4))
        
        surface.set_clip(clip)
        pygame.draw.rect(surface, COLOR_GRID_MAJOR, list_rect, 1)
        
        # Filename input (save mode)
        if self.save_mode:
            self.filename_input.draw(surface, font)
        
        # Buttons
        btn_y = self.rect.bottom - 35
        confirm_text = "Save" if self.save_mode else "Open"
        
        # Draw buttons (simplified)
        cancel_rect = pygame.Rect(self.rect.x + 10, btn_y, 80, 28)
        confirm_rect = pygame.Rect(self.rect.right - 90, btn_y, 80, 28)
        
        pygame.draw.rect(surface, COLOR_BUTTON, cancel_rect)
        pygame.draw.rect(surface, COLOR_BUTTON, confirm_rect)
        pygame.draw.rect(surface, COLOR_GRID_MAJOR, cancel_rect, 1)
        pygame.draw.rect(surface, COLOR_ACCENT, confirm_rect, 1)
        
        cancel_surf = font.render("Cancel", True, COLOR_TEXT)
        confirm_surf = font.render(confirm_text, True, COLOR_TEXT)
        surface.blit(cancel_surf, cancel_surf.get_rect(center=cancel_rect.center))
        surface.blit(confirm_surf, confirm_surf.get_rect(center=confirm_rect.center))


class EntryPointEditor:
    """Dialog for editing entry point properties with room dropdown."""
    
    def __init__(self, x, y, entry_index, from_room, callback, rooms_dir, is_start=False):
        # Get available rooms first
        self.available_rooms = ["start"]  # Always include start
        if os.path.exists(rooms_dir):
            for f in sorted(os.listdir(rooms_dir)):
                if f.endswith('.json') and f != 'world.json':
                    room_name = f.replace('.json', '')
                    if room_name not in self.available_rooms:
                        self.available_rooms.append(room_name)
        
        # Calculate dialog height based on number of rooms (max 8 visible options)
        max_visible_options = min(8, len(self.available_rooms))
        dialog_height = 100 + max_visible_options * 24 + 50  # title + options + checkbox + buttons
        
        # Position dialog with click position inside it
        x = x - 125  # Center on x
        y = y - dialog_height // 2  # Center on y
        
        # Fit dialog to screen
        screen = pygame.display.get_surface()
        if screen:
            screen_width, screen_height = screen.get_size()
            if x + 250 > screen_width:
                x = screen_width - 250
            if y + dialog_height > screen_height:
                y = screen_height - dialog_height
            if x < 0:
                x = 0
            if y < 0:
                y = 0
        
        self.rect = pygame.Rect(x, y, 250, dialog_height)
        self.entry_index = entry_index
        self.callback = callback
        self.active = True
        
        # Dropdown for room selection
        self.selected_room_index = 0
        for i, room in enumerate(self.available_rooms):
            if room == from_room:
                self.selected_room_index = i
                break
        
        self.dropdown_rect = pygame.Rect(x + 10, y + 40, 230, 24)
        self.dropdown_expanded = False
        
        # Scrolling for dropdown
        self.scroll_offset = 0
        self.max_visible_options = max_visible_options
        self.option_height = 24
        
        # Checkbox for start point
        self.is_start_checkbox = pygame.Rect(x + 10, y + 40 + 24 + self.max_visible_options * self.option_height + 10, 20, 20)
        self.is_start = is_start
        
        # Buttons - position them below the checkbox area
        button_y = y + 40 + 24 + self.max_visible_options * self.option_height + 40
        self.ok_btn = Button(x + 10, button_y, 80, 24, "OK", self.confirm)
        self.cancel_btn = Button(x + 160, button_y, 80, 24, "Cancel", self.close)
        
        # Track mouse state
        self.last_mouse_pos = (0, 0)
        self.mouse_clicked = False
    
    def confirm(self):
        """Confirm changes."""
        from_room = self.available_rooms[self.selected_room_index]
        self.callback(self.entry_index, from_room, self.is_start)
        self.close()
    
    def close(self):
        """Close dialog."""
        self.active = False
    
    def handle_event(self, event):
        """Handle input events."""
        if not self.active:
            return
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            self.mouse_clicked = True
            
            # Check if clicked outside dialog
            if not self.rect.collidepoint(mouse_pos):
                self.close()
                return
            
            # Handle dropdown
            if self.dropdown_rect.collidepoint(mouse_pos):
                self.dropdown_expanded = not self.dropdown_expanded
            elif self.is_start_checkbox.collidepoint(mouse_pos):
                self.is_start = not self.is_start
            elif self.dropdown_expanded:
                # Check if clicking on options
                options_start_y = self.rect.y + 40 + 24
                for i in range(self.max_visible_options):
                    option_index = self.scroll_offset + i
                    if option_index >= len(self.available_rooms):
                        break
                    
                    option_rect = pygame.Rect(
                        self.rect.x + 10, 
                        options_start_y + i * self.option_height, 
                        230, 
                        self.option_height
                    )
                    
                    if option_rect.collidepoint(mouse_pos):
                        self.selected_room_index = option_index
                        self.dropdown_expanded = False
                        break
                
                # Check scroll buttons (if needed)
                if len(self.available_rooms) > self.max_visible_options:
                    # Up arrow
                    up_arrow_rect = pygame.Rect(self.rect.right - 20, options_start_y, 10, 15)
                    if up_arrow_rect.collidepoint(mouse_pos) and self.scroll_offset > 0:
                        self.scroll_offset -= 1
                    
                    # Down arrow  
                    down_arrow_rect = pygame.Rect(self.rect.right - 20, options_start_y + self.max_visible_options * self.option_height - 15, 10, 15)
                    if down_arrow_rect.collidepoint(mouse_pos) and self.scroll_offset < len(self.available_rooms) - self.max_visible_options:
                        self.scroll_offset += 1
            
            # Handle checkbox
            elif self.is_start_checkbox.collidepoint(mouse_pos):
                self.is_start = not self.is_start
        
        elif event.type == pygame.MOUSEWHEEL and self.dropdown_expanded:
            if event.y > 0 and self.scroll_offset > 0:
                self.scroll_offset -= 1
            elif event.y < 0 and self.scroll_offset < len(self.available_rooms) - self.max_visible_options:
                self.scroll_offset += 1
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.confirm()
            elif event.key == pygame.K_ESCAPE:
                self.close()
    
    def update(self, dt, mouse_pos):
        """Update dialog state."""
        self.last_mouse_pos = mouse_pos
        
        # Update buttons
        self.ok_btn.update(mouse_pos, self.mouse_clicked)
        self.cancel_btn.update(mouse_pos, self.mouse_clicked)
        
        # Reset click state
        self.mouse_clicked = False
    
    def draw(self, surface, font):
        """Draw dialog."""
        if not self.active:
            return
        
        # Dim background
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surface.blit(dim, (0, 0))
        
        # Dialog box
        pygame.draw.rect(surface, COLOR_PANEL, self.rect)
        pygame.draw.rect(surface, COLOR_ACCENT, self.rect, 2)
        
        # Title
        title_surf = font.render("Edit Entry Point", True, COLOR_TEXT)
        surface.blit(title_surf, (self.rect.x + 10, self.rect.y + 10))
        
        # Label
        label_surf = font.render("From Room:", True, COLOR_TEXT_DIM)
        surface.blit(label_surf, (self.rect.x + 10, self.rect.y + 25))
        
        # Checkbox for start point
        checkbox_label_surf = font.render("Make this the start point", True, COLOR_TEXT_DIM)
        surface.blit(checkbox_label_surf, (self.rect.x + 35, self.rect.y + 40 + 24 + self.max_visible_options * self.option_height + 12))
        
        # Checkbox
        pygame.draw.rect(surface, COLOR_BUTTON, self.is_start_checkbox)
        pygame.draw.rect(surface, COLOR_GRID_MAJOR, self.is_start_checkbox, 1)
        if self.is_start:
            # Draw checkmark
            pygame.draw.line(surface, COLOR_TEXT, 
                           (self.is_start_checkbox.left + 3, self.is_start_checkbox.centery),
                           (self.is_start_checkbox.centerx - 1, self.is_start_checkbox.bottom - 3), 2)
            pygame.draw.line(surface, COLOR_TEXT,
                           (self.is_start_checkbox.centerx - 1, self.is_start_checkbox.bottom - 3),
                           (self.is_start_checkbox.right - 3, self.is_start_checkbox.top + 3), 2)
        
        # Dropdown button
        dropdown_color = COLOR_BUTTON_HOVER if self.dropdown_rect.collidepoint(self.last_mouse_pos) else COLOR_BUTTON
        pygame.draw.rect(surface, dropdown_color, self.dropdown_rect)
        pygame.draw.rect(surface, COLOR_ACCENT if self.dropdown_expanded else COLOR_GRID_MAJOR, self.dropdown_rect, 1)
        
        # Selected room text
        selected_room = self.available_rooms[self.selected_room_index]
        text_surf = font.render(selected_room, True, COLOR_TEXT)
        surface.blit(text_surf, (self.dropdown_rect.x + 5, self.dropdown_rect.y + 4))
        
        # Dropdown arrow
        arrow_points = [
            (self.dropdown_rect.right - 15, self.dropdown_rect.centery - 3),
            (self.dropdown_rect.right - 10, self.dropdown_rect.centery + 3),
            (self.dropdown_rect.right - 5, self.dropdown_rect.centery - 3)
        ]
        pygame.draw.polygon(surface, COLOR_TEXT, arrow_points)
        
        # Dropdown options (when expanded)
        if self.dropdown_expanded:
            options_area_height = self.max_visible_options * self.option_height
            expanded_rect = pygame.Rect(
                self.rect.x + 10, 
                self.rect.y + 40 + 24, 
                230, 
                options_area_height
            )
            pygame.draw.rect(surface, COLOR_BG, expanded_rect)
            pygame.draw.rect(surface, COLOR_ACCENT, expanded_rect, 1)
            
            # Draw visible options
            for i in range(self.max_visible_options):
                option_index = self.scroll_offset + i
                if option_index >= len(self.available_rooms):
                    break
                
                room = self.available_rooms[option_index]
                option_rect = pygame.Rect(
                    self.rect.x + 10, 
                    self.rect.y + 40 + 24 + i * self.option_height, 
                    230, 
                    self.option_height
                )
                
                option_color = COLOR_BUTTON_HOVER if option_rect.collidepoint(self.last_mouse_pos) else COLOR_BG
                pygame.draw.rect(surface, option_color, option_rect)
                
                text_surf = font.render(room, True, COLOR_TEXT)
                surface.blit(text_surf, (option_rect.x + 5, option_rect.y + 4))
            
            # Draw scroll indicators if needed
            if len(self.available_rooms) > self.max_visible_options:
                # Up arrow
                up_color = COLOR_TEXT if self.scroll_offset > 0 else COLOR_TEXT_DIM
                up_points = [
                    (self.rect.right - 15, self.rect.y + 40 + 24 + 7),
                    (self.rect.right - 10, self.rect.y + 40 + 24 + 2),
                    (self.rect.right - 5, self.rect.y + 40 + 24 + 7)
                ]
                pygame.draw.polygon(surface, up_color, up_points)
                
                # Down arrow
                down_color = COLOR_TEXT if self.scroll_offset < len(self.available_rooms) - self.max_visible_options else COLOR_TEXT_DIM
                down_points = [
                    (self.rect.right - 15, self.rect.y + 40 + 24 + options_area_height - 7),
                    (self.rect.right - 10, self.rect.y + 40 + 24 + options_area_height - 2),
                    (self.rect.right - 5, self.rect.y + 40 + 24 + options_area_height - 7)
                ]
                pygame.draw.polygon(surface, down_color, down_points)
        
        # Buttons
        self.ok_btn.draw(surface, font)
        self.cancel_btn.draw(surface, font)


# ============================================================================
# ROOM EDITOR
# ============================================================================

class RoomEditor:
    """Main room editor application."""
    
    def __init__(self, rooms_dir="rooms", game=None):
        # Handle case where first argument is actually rooms_dir (when called from main)
        if isinstance(game, str):
            rooms_dir = game
            game = None
        
        if game:
            self.game = game
            self.screen = game.screen
            self.rooms_dir = rooms_dir
        else:
            pygame.init()
            self.game = None
            self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
            pygame.display.set_caption("Room Editor")
            self.rooms_dir = rooms_dir
            
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Fonts
        self.font = pygame.font.Font(None, 20)
        self.font_large = pygame.font.Font(None, 28)
        
        # Room data
        os.makedirs(self.rooms_dir, exist_ok=True)
        self.room = RoomData()
        self.room.fill_borders()
        
        self.autotiler = AutoTiler()
        
        # View
        self.zoom = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self.camera_x = 0
        self.camera_y = 0
        self.dragging_camera = False
        self.last_mouse_pos = (0, 0)
        
        # Tools
        self.current_tile = TILE_SOLID
        self.tool = "paint"  # paint, fill, line, rect, spawn, entry, platform
        self.painting = False
        self.erasing = False
        
        # Line/rect tool state
        self.line_start = None
        
        # Line/rect tool state
        self.line_start = None
        
        # UI
        self.sidebar_width = SIDEBAR_WIDTH
        self.toolbar_height = TOOLBAR_HEIGHT
        self.sidebar_scroll = 0
        self.sidebar_content_height = 0
        self.setup_ui()
        
        # File dialog
        self.file_dialog = FileDialog(200, 100, 400, 400, rooms_dir)
        
        # Undo/redo
        self.undo_stack = []
        self.redo_stack = []
        self.max_undo = 50
        
        # Message
        self.message = ""
        self.message_timer = 0
    
    def setup_ui(self):
        """Setup UI elements."""
        
        # --- Toolbar Elements (Top) ---
        toolbar_y = 7
        
        # File Operations
        x = 5
        btn_w = 60
        btn_h = 26
        gap = 5
        
        self.action_buttons = [
            Button(x, toolbar_y, btn_w, btn_h, "New", self.new_room),
            Button(x + btn_w + gap, toolbar_y, btn_w, btn_h, "Open", self.open_room),
            Button(x + (btn_w + gap)*2, toolbar_y, btn_w, btn_h, "Save", self.save_room),
            Button(x + (btn_w + gap)*3, toolbar_y, btn_w+10, btn_h, "Save As", self.save_room_as),
        ]
        
        x += (btn_w + gap) * 4 + 10
        
        # Room Size
        self.width_input = InputBox(x, toolbar_y+2, 40, 22, str(self.room.width), "W:")
        self.height_input = InputBox(x + 55, toolbar_y+2, 40, 22, str(self.room.height), "H:")
        self.resize_btn = Button(x + 110, toolbar_y, 40, 26, "Set", self.apply_resize)
        
        x += 160 + 10
        
        # Editing Tools (Horizontal)
        tools = [("Paint", "paint"), ("Fill", "fill"), ("Line", "line"), 
                 ("Rect", "rect"), ("Spawn", "spawn"), ("Plat", "platform")]
                 
        self.tool_buttons = []
        for name, tool in tools:
            w = 50
            if name in ("Paint", "Fill", "Line", "Rect"): w = 45
            btn = Button(x, toolbar_y, w, btn_h, name, toggle=True)
            btn.tool = tool
            if tool == self.tool:
                btn.active = True
            self.tool_buttons.append(btn)
            x += w + 2
            
        # Extra Actions
        x += 10
        self.action_buttons.append(Button(x, toolbar_y, 60, btn_h, "Borders", self.room.fill_borders))
        self.action_buttons.append(Button(x + 65, toolbar_y, 60, btn_h, "Clear", self.clear_room))
        
        # Back Button (Far Right)
        self.exit_btn = Button(1150, toolbar_y, 100, btn_h, "Exit", self.exit_editor)


        # --- Sidebar Elements (Left) ---
        # Tile buttons in a grid
        self.tile_buttons = []
        start_x = 15
        start_y = 10 # Relative to scroll content start
        size = 48
        spacing_x = 70
        spacing_y = 70
        cols = 3
        
        tile_types = [TILE_EMPTY, TILE_SOLID, TILE_SPIKE, TILE_GRAPPLE, TILE_EXIT, TILE_PLATFORM, TILE_ICE]
        
        for i, tile_type in enumerate(tile_types):
            col = i % cols
            row = i // cols
            btn_x = start_x + col * spacing_x
            btn_y = start_y + row * spacing_y
            
            btn = TileButton(btn_x, btn_y, size, tile_type)
            if tile_type == self.current_tile:
                btn.active = True
            self.tile_buttons.append(btn)
            
        self.sidebar_content_height = start_y + (len(tile_types) // cols + 1) * spacing_y + 50
        
    def exit_editor(self):
        """Exit the editor."""
        self.running = False
    
    def show_message(self, text, duration=2.0):
        """Show a temporary message."""
        self.message = text
        self.message_timer = duration
    
    def save_undo(self):
        """Save current state for undo."""
        state = {
            'tiles': [row[:] for row in self.room.tiles],
            'objects': [obj.copy() for obj in self.room.objects],
            'spawn': self.room.spawn
        }
        self.undo_stack.append(state)
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
    
    def undo(self):
        """Undo last action."""
        if not self.undo_stack:
            return
        
        # Save current for redo
        current = {
            'tiles': [row[:] for row in self.room.tiles],
            'spawn': self.room.spawn
        }
        self.redo_stack.append(current)
        
        # Restore previous
        state = self.undo_stack.pop()
        self.room.tiles = state['tiles']
        self.room.objects = state.get('objects', [])
        self.room.spawn = state['spawn']
        self.room.modified = True
        self.show_message("Undo")
    
    def redo(self):
        """Redo last undone action."""
        if not self.redo_stack:
            return
        
        # Save current for undo
        current = {
            'tiles': [row[:] for row in self.room.tiles],
            'spawn': self.room.spawn
        }
        self.undo_stack.append(current)
        
        # Restore
        state = self.redo_stack.pop()
        self.room.tiles = state['tiles']
        self.room.objects = state.get('objects', [])
        self.room.spawn = state['spawn']
        self.room.modified = True
        self.show_message("Redo")
    
    def new_room(self):
        """Create new room."""
        self.room = RoomData()
        self.room.fill_borders()
        self.width_input.set_value(self.room.width)
        self.height_input.set_value(self.room.height)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.center_view()
        self.show_message("New room created")
    
    def open_room(self):
        """Open file dialog to load room."""
        self.file_dialog.open(save_mode=False)
    
    def save_room(self):
        """Save current room."""
        if self.room.filename:
            self.room.save(self.room.filename)
            self.show_message(f"Saved: {os.path.basename(self.room.filename)}")
        else:
            self.save_room_as()
    
    def save_room_as(self):
        """Open file dialog to save room."""
        self.file_dialog.open(save_mode=True)
    
    def clear_room(self):
        """Clear all tiles."""
        self.save_undo()
        self.room.clear()
        self.show_message("Room cleared")
    
    def apply_resize(self):
        """Apply new room size."""
        new_width = self.width_input.get_value()
        new_height = self.height_input.get_value()
        
        if new_width < 5 or new_height < 5:
            self.show_message("Minimum size is 5x5")
            return
        if new_width > 100 or new_height > 100:
            self.show_message("Maximum size is 100x100")
            return
        
        if new_width != self.room.width or new_height != self.room.height:
            self.save_undo()
            self.room.resize(new_width, new_height)
            self.show_message(f"Resized to {new_width}x{new_height}")
    
    def edit_entry_point(self, index, from_room, is_start=False):
        """Edit an entry point's from_room and start status."""
        self.save_undo()
        self.room.set_entry_point_room(index, from_room)
        self.room.set_entry_point_start(index, is_start)
        self.show_message(f"Entry point updated")
    
    def center_view(self):
        """Center view on room."""
        canvas_width = self.screen.get_width() - self.sidebar_width
        canvas_height = self.screen.get_height() - self.toolbar_height
        
        room_pixel_width = self.room.width * TILE_SIZE * self.zoom
        room_pixel_height = self.room.height * TILE_SIZE * self.zoom
        
        self.camera_x = (canvas_width - room_pixel_width) / 2
        self.camera_y = (canvas_height - room_pixel_height) / 2
    
    def screen_to_tile(self, screen_x, screen_y):
        """Convert screen position to tile coordinates."""
        # Adjust for sidebar and toolbar
        world_x = (screen_x - self.sidebar_width - self.camera_x) / self.zoom
        world_y = (screen_y - self.toolbar_height - self.camera_y) / self.zoom
        
        tile_x = int(world_x // TILE_SIZE)
        tile_y = int(world_y // TILE_SIZE)
        
        return tile_x, tile_y
    
    def tile_to_screen(self, tile_x, tile_y):
        """Convert tile coordinates to screen position."""
        screen_x = tile_x * TILE_SIZE * self.zoom + self.camera_x + self.sidebar_width
        screen_y = tile_y * TILE_SIZE * self.zoom + self.camera_y + self.toolbar_height
        return screen_x, screen_y
    
    def flood_fill(self, start_x, start_y, target_tile, replacement_tile):
        """Flood fill algorithm."""
        if target_tile == replacement_tile:
            return
        
        stack = [(start_x, start_y)]
        visited = set()
        
        while stack:
            x, y = stack.pop()
            
            if (x, y) in visited:
                continue
            if not (0 <= x < self.room.width and 0 <= y < self.room.height):
                continue
            if self.room.tiles[y][x] != target_tile:
                continue
            
            visited.add((x, y))
            self.room.tiles[y][x] = replacement_tile
            
            stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
        
        self.room.modified = True
    
    def draw_line(self, x0, y0, x1, y1, tile_type):
        """Draw line of tiles using Bresenham's algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while True:
            self.room.set_tile(x0, y0, tile_type)
            
            if x0 == x1 and y0 == y1:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
    
    def draw_rect(self, x0, y0, x1, y1, tile_type, filled=False):
        """Draw rectangle of tiles."""
        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)
        
        if filled:
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    self.room.set_tile(x, y, tile_type)
        else:
            for x in range(min_x, max_x + 1):
                self.room.set_tile(x, min_y, tile_type)
                self.room.set_tile(x, max_y, tile_type)
            for y in range(min_y, max_y + 1):
                self.room.set_tile(min_x, y, tile_type)
                self.room.set_tile(max_x, y, tile_type)
    
    def handle_events(self):
        """Handle input events."""
        mouse_pos = pygame.mouse.get_pos()
        mouse_clicked = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                if self.game:
                    self.game.running = False
                return
            
            # File dialog
            if self.file_dialog.active:
                result = self.file_dialog.handle_event(event)
                if result:
                    if self.file_dialog.save_mode:
                        self.room.save(result)
                        self.show_message(f"Saved: {os.path.basename(result)}")
                    else:
                        self.room.load(result)
                        self.width_input.set_value(self.room.width)
                        self.height_input.set_value(self.room.height)
                        self.show_message(f"Loaded: {os.path.basename(result)}")
                continue
            
            # Entry editor
            # if self.entry_editor and self.entry_editor.active:
            #     self.entry_editor.handle_event(event)
            #     continue
            
            # Input boxes
            self.width_input.handle_event(event)
            self.height_input.handle_event(event)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicked = True
                
                # Check regions
                in_sidebar = event.pos[0] < self.sidebar_width and event.pos[1] > self.toolbar_height
                in_toolbar = event.pos[1] < self.toolbar_height
                in_canvas = event.pos[0] > self.sidebar_width and event.pos[1] > self.toolbar_height
                
                # Canvas Interactions
                if in_canvas:
                    # Right click to remove
                    if event.button == 3:
                        tile_x, tile_y = self.screen_to_tile(*event.pos)
                        
                        # 1. Check for Objects to remove (Planks, etc.)
                        removed_object = False
                        world_x = (event.pos[0] - self.sidebar_width - self.camera_x) / self.zoom
                        world_y = (event.pos[1] - self.toolbar_height - self.camera_y) / self.zoom
                        mouse_rect = pygame.Rect(world_x, world_y, 1, 1)
                        
                        for i, obj in enumerate(self.room.objects):
                            obj_rect = pygame.Rect(obj["x"], obj["y"], obj["w"], obj["h"])
                            if obj_rect.colliderect(mouse_rect):
                                self.save_undo()
                                self.room.objects.pop(i)
                                self.show_message("Object removed")
                                removed_object = True
                                break
                        
                        if removed_object:
                            # Skip tile removal if we hit an object
                            pass
                        else:
                            # 2. Check if clicking on spawn point
                            removed_spawn = False
                            if self.room.spawn:
                                sx, sy = self.room.spawn
                                if sx == tile_x and sy == tile_y:
                                    self.save_undo()
                                    self.room.clear_spawn()
                                    self.show_message("Spawn point removed")
                                    removed_spawn = True
                            
                            
                            # 3. Clear Tiles based on Current Tool Size
                            if not removed_spawn and 0 <= tile_x < self.room.width and 0 <= tile_y < self.room.height:
                                # Determine eraser size based on CURRENTLY SELECTED tile
                                # "Make the remove size changable but also set automatically to the tile size of currently selected"
                                # "right click and empry should be just 32x32"
                                
                                eraser_w = 1
                                eraser_h = 1
                                
                                # If current tool is Solid, Ice, or we are just generic (Paint tool default usually), use 32x32
                                # Assuming if current_tile is 0 (Empty), we implies 32x32
                                if self.current_tile in (TILE_SOLID, TILE_ICE, TILE_EMPTY):
                                    eraser_w = 2
                                    eraser_h = 2
                                elif self.tool == "platform":
                                    eraser_w = 4
                                    eraser_h = 2
                                
                                self.save_undo()
                                
                                # Calculate base alignment
                                if eraser_w > 1:
                                    base_x = (tile_x // 2) * 2 # Align to 32px grid
                                    base_y = (tile_y // 2) * 2
                                else:
                                    base_x = tile_x
                                    base_y = tile_y
                                    
                                    base_x = tile_x
                                    base_y = tile_y
                                    
                                # 1. Remove overlapping objects in this area
                                pixel_area_rect = pygame.Rect(base_x * 16, base_y * 16, eraser_w * 16, eraser_h * 16)
                                self._remove_objects_in_rect(pixel_area_rect)

                                # 2. Remove tiles in area (Always do both)
                                for dy in range(eraser_h):
                                    for dx in range(eraser_w):
                                        tx = base_x + dx
                                        ty = base_y + dy
                                        if 0 <= tx < self.room.width and 0 <= ty < self.room.height:
                                            self.room.set_tile(tx, ty, TILE_EMPTY)
                                            
                                self.show_message("Area cleared")
                    
                    # Left click for tools
                    elif event.button == 1:
                        tile_x, tile_y = self.screen_to_tile(*event.pos)
                        
                        if self.tool == "spawn":
                            # Set spawn point
                            if 0 <= tile_x < self.room.width and 0 <= tile_y < self.room.height:
                                self.save_undo()
                                self.room.set_spawn(tile_x, tile_y)
                                self.show_message("Spawn point set")
                        elif self.tool == "fill":
                            target = self.room.get_tile(tile_x, tile_y)
                            self.save_undo()
                            self.flood_fill(tile_x, tile_y, target, self.current_tile)
                        elif self.tool in ("line", "rect"):
                            self.line_start = (tile_x, tile_y)
                        elif self.tool == "platform":
                            # Add subgrid platform
                            # Snap to 8x8 grid
                            world_x = (event.pos[0] - self.sidebar_width - self.camera_x) / self.zoom
                            world_y = (event.pos[1] - self.toolbar_height - self.camera_y) / self.zoom
                            
                            # Snap to specific requirements:
                            # X: Same as 32x32 blocks -> 32px snapping
                            # Y: 2 spaces for each 32x32 -> 16px snapping
                            # Snap to specific requirements:
                            # X: Same as 32x32 blocks -> 32px snapping
                            # Y: 2 spaces for each 32x32 -> 16px snapping
                            # Snap to specific requirements:
                            # X: Same as 32x32 blocks (32px pixels)
                            # Y: 2 spaces for each 32x32 block (16px pixels)
                            # TILE_SIZE is 16. 
                            
                            grid_x = int(world_x // 32) * 32
                            grid_y = int(world_y // 16) * 16
                            
                            # Check if platform already exists at this location
                            exists = False
                            for obj in self.room.objects:
                                if (obj["type"] == OBJ_PLATFORM and 
                                    abs(obj["x"] - grid_x) < 2 and abs(obj["y"] - grid_y) < 2):
                                    exists = True
                                    break
                            
                            if not exists:
                                self.save_undo()
                                
                                # Clear Tiles Underneath (Mutual Exclusion)
                                # Plank is 32wide (2 tiles) x 16high (1 tile)
                                tile_start_x = grid_x // 16
                                tile_start_y = grid_y // 16
                                for dy in range(1):
                                    for dx in range(2):
                                        tx = tile_start_x + dx
                                        ty = tile_start_y + dy
                                        if 0 <= tx < self.room.width and 0 <= ty < self.room.height:
                                            self.room.set_tile(tx, ty, TILE_EMPTY)

                                # Add Object
                                self.room.objects.append({
                                    "type": OBJ_PLATFORM,
                                    "x": grid_x,
                                    "y": grid_y,
                                    "w": 32, # 2 Tiles wide
                                    "h": 16  # 1 Tile high
                                })
                                self.show_message("Platform placed")
    
                        else:
                            self.painting = True
                            self.save_undo()
                            
                            # Generic Paint Tool
                            if self.current_tile in (TILE_SOLID, TILE_ICE):
                                # Snap to even grid (32px) and place 2x2
                                base_x = (tile_x // 2) * 2
                                base_y = (tile_y // 2) * 2
                                
                                # Auto-remove any objects in this space
                                # 32x32 area. We are in 16x16 tile coords.
                                # base_x is aligned to 2.
                                pixel_area_rect = pygame.Rect(base_x * TILE_SIZE, base_y * TILE_SIZE, 32, 32)
                                self._remove_objects_in_rect(pixel_area_rect)

                                for dy in range(2):
                                    for dx in range(2):
                                        self.room.set_tile(base_x + dx, base_y + dy, self.current_tile)
                            else:
                                # Single tile paint (e.g. Spikes)
                                # Should we remove objects here too? Maybe not enforced, but good for consistency
                                # If placing a spike (16x16), check if it overlaps a plank?
                                # User complained about "plank should be removed if drawn over with something else"
                                
                                # Let's be safe: If painting ANYTHING, remove objects in that cell.
                                pixel_area_rect = pygame.Rect(tile_x * TILE_SIZE, tile_y * TILE_SIZE, 16, 16)
                                self._remove_objects_in_rect(pixel_area_rect)
                                
                                self.room.set_tile(tile_x, tile_y, self.current_tile)
                    
                    # Scroll to zoom
                    elif event.button == 4:  # Scroll up
                        old_zoom = self.zoom
                        self.zoom = min(self.max_zoom, self.zoom * 1.2)
                        # Zoom toward mouse
                        factor = self.zoom / old_zoom
                        mx = event.pos[0] - self.sidebar_width
                        my = event.pos[1] - self.toolbar_height
                        self.camera_x = mx - (mx - self.camera_x) * factor
                        self.camera_y = my - (my - self.camera_y) * factor
                    
                    elif event.button == 5:  # Scroll down
                        old_zoom = self.zoom
                        self.zoom = max(self.min_zoom, self.zoom / 1.2)
                        factor = self.zoom / old_zoom
                        mx = event.pos[0] - self.sidebar_width
                        my = event.pos[1] - self.toolbar_height
                        self.camera_x = mx - (mx - self.camera_x) * factor
                        self.camera_y = my - (my - self.camera_y) * factor

            elif event.type == pygame.MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()
                if mouse_pos[0] < self.sidebar_width and mouse_pos[1] > self.toolbar_height:
                    # Sidebar scroll
                    scroll_speed = 30
                    self.sidebar_scroll -= event.y * scroll_speed
                    
                    # Clamp scroll
                    max_scroll = max(0, self.sidebar_content_height - (self.screen.get_height() - self.toolbar_height - 30))
                    self.sidebar_scroll = max(0, min(self.sidebar_scroll, max_scroll))
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3):
                    self.dragging_camera = False
                
                elif event.button == 1:
                    self.painting = False
                    
                    # Complete line/rect
                    if self.line_start and event.pos[0] > self.sidebar_width and event.pos[1] > self.toolbar_height:
                        tile_x, tile_y = self.screen_to_tile(*event.pos)
                        self.save_undo()
                        
                        if self.tool == "line":
                            self.draw_line(*self.line_start, tile_x, tile_y, self.current_tile)
                        elif self.tool == "rect":
                            keys = pygame.key.get_pressed()
                            filled = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
                            self.draw_rect(*self.line_start, tile_x, tile_y, self.current_tile, filled)
                        
                        self.line_start = None
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging_camera:
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.camera_x += dx
                    self.camera_y += dy
                    self.last_mouse_pos = event.pos
                
                elif self.painting and event.pos[0] > self.sidebar_width and event.pos[1] > self.toolbar_height:
                    tile_x, tile_y = self.screen_to_tile(*event.pos)
                    
                    if self.current_tile in (TILE_SOLID, TILE_ICE):
                        # Snap to even grid (32px)
                        base_x = (tile_x // 2) * 2
                        base_y = (tile_y // 2) * 2
                        
                        # Auto-remove objects in this 32x32 area
                        pixel_area_rect = pygame.Rect(base_x * TILE_SIZE, base_y * TILE_SIZE, 32, 32)
                        self._remove_objects_in_rect(pixel_area_rect)
                        
                        # Set 2x2 block
                        for dy in range(2):
                            for dx in range(2):
                                self.room.set_tile(base_x + dx, base_y + dy, self.current_tile)
                    else:
                        # Single tile paint
                        pixel_area_rect = pygame.Rect(tile_x * TILE_SIZE, tile_y * TILE_SIZE, 16, 16)
                        self._remove_objects_in_rect(pixel_area_rect)
                        self.room.set_tile(tile_x, tile_y, self.current_tile)
            
            elif event.type == pygame.KEYDOWN:
                # Keyboard shortcuts
                if event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL):
                    if event.mod & pygame.KMOD_SHIFT:
                        self.redo()
                    else:
                        self.undo()
                elif event.key == pygame.K_y and (event.mod & pygame.KMOD_CTRL):
                    self.redo()
                elif event.key == pygame.K_s and (event.mod & pygame.KMOD_CTRL):
                    if event.mod & pygame.KMOD_SHIFT:
                        self.save_room_as()
                    else:
                        self.save_room()
                elif event.key == pygame.K_o and (event.mod & pygame.KMOD_CTRL):
                    self.open_room()
                elif event.key == pygame.K_n and (event.mod & pygame.KMOD_CTRL):
                    self.new_room()
                elif event.key == pygame.K_HOME:
                    self.center_view()
                
                # Number keys for tiles
                elif event.key in (pygame.K_0, pygame.K_1, pygame.K_2, 
                                  pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6):
                    tile = event.key - pygame.K_0
                    if tile == 6: tile = TILE_ICE # 6 -> Ice
                    
                    # Map to button index if needed
                    self.current_tile = tile
                
                # Tool shortcuts
                elif event.key == pygame.K_b:
                    self.set_tool("paint")
                elif event.key == pygame.K_g:
                    self.set_tool("fill")
                elif event.key == pygame.K_l:
                    self.set_tool("line")
                elif event.key == pygame.K_r:
                    self.set_tool("rect")
                elif event.key == pygame.K_e:
                    self.set_tool("entry")
                elif event.key == pygame.K_p:
                    self.set_tool("platform")
                
                # WASD movement
                elif event.key == pygame.K_w:
                    self.camera_y += 50
                elif event.key == pygame.K_s:
                    self.camera_y -= 50
                elif event.key == pygame.K_a:
                    self.camera_x += 50
                elif event.key == pygame.K_d:
                    self.camera_x -= 50
                
                # Delete key for entry points
                elif event.key == pygame.K_DELETE:
                    # if self.selected_entry_point is not None:
                    #     self.save_undo()
                    #     self.room.remove_entry_point(self.selected_entry_point)
                    #     self.selected_entry_point = None
                    #     self.show_message("Entry point deleted")
                    pass
                
                # Escape key - cancel tool or exit
                elif event.key == pygame.K_ESCAPE:
                    if self.line_start:
                        self.line_start = None
                    # elif self.selected_entry_point is not None:
                    #     self.selected_entry_point = None
                    elif self.file_dialog.active:
                        self.file_dialog.close()
                    # elif self.entry_editor and self.entry_editor.active:
                    #     self.entry_editor.close()
                    else:
                        self.exit_editor()
            
            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        
        # UI button updates
        if not self.file_dialog.active:
            # Tile buttons - Adjust for scroll
            header_h = 30
            start_y = self.toolbar_height + header_h - self.sidebar_scroll
            
            # Clip mouse for sidebar buttons
            mouse_in_sidebar_content = (mouse_pos[0] < self.sidebar_width and 
                                      mouse_pos[1] > self.toolbar_height + header_h)

            for btn in self.tile_buttons:
                # Temporarily move rect
                original_y = btn.rect.y
                btn.rect.y += start_y
                
                # Update only if mouse is in visible area
                if mouse_in_sidebar_content:
                    if btn.update(mouse_pos, mouse_clicked):
                        if btn.tile_type == TILE_PLATFORM:
                            # Special case: Platform button activates Platform Tool (Object)
                            self.set_tool("platform")
                            self.show_message("Platform Tool Selected")
                        else:
                            self.current_tile = btn.tile_type
                            # Reset tool to paint if we act like a tile selector
                            if self.tool not in ("paint", "fill", "line", "rect"):
                                self.set_tool("paint")
                            
                # Update active state visualization
                btn.active = (btn.tile_type == self.current_tile) if btn.tile_type != TILE_PLATFORM else (self.tool == "platform")
                
                btn.rect.y = original_y # Restore
            
            # Tool buttons
            for btn in self.tool_buttons:
                if btn.update(mouse_pos, mouse_clicked):
                    self.set_tool(btn.tool)
            
            # Action buttons
            for btn in self.action_buttons:
                btn.update(mouse_pos, mouse_clicked)
            
            self.resize_btn.update(mouse_pos, mouse_clicked)
            self.exit_btn.update(mouse_pos, mouse_clicked)
    def set_tool(self, tool):
        """Set current tool."""
        self.tool = tool
        for btn in self.tool_buttons:
            btn.active = btn.tool == tool
        self.line_start = None
        
    def _remove_objects_in_rect(self, rect):
        """Helper to remove any room objects overlapping the given rect."""
        i = 0
        while i < len(self.room.objects):
            obj = self.room.objects[i]
            obj_rect = pygame.Rect(obj["x"], obj["y"], obj["w"], obj["h"])
            if obj_rect.colliderect(rect):
                self.room.objects.pop(i)
            else:
                i += 1


    
    def update(self, dt):
        """Update editor state."""
        mouse_pos = pygame.mouse.get_pos()
        
        self.width_input.update(dt)
        self.height_input.update(dt)
        self.file_dialog.update(dt)
        
        # if self.entry_editor:
        #     self.entry_editor.update(dt, mouse_pos)
        #     if not self.entry_editor.active:
        #         self.entry_editor = None
        
        if self.message_timer > 0:
            self.message_timer -= dt
    
    def draw(self):
        """Draw everything."""
        self.screen.fill(COLOR_BG)
        
        # Draw canvas area
        self.draw_canvas()
        
        # Draw UI
        self.draw_ui()
        
        # Draw file dialog
        self.file_dialog.draw(self.screen, self.font)
        
        # Draw message
        if self.message_timer > 0:
            msg_surf = self.font_large.render(self.message, True, COLOR_TEXT)
            msg_rect = msg_surf.get_rect(centerx=self.screen.get_width() // 2 + self.sidebar_width // 2, 
                                        bottom=self.screen.get_height() - 20)

            pygame.draw.rect(self.screen, COLOR_PANEL, msg_rect.inflate(20, 10))
            self.screen.blit(msg_surf, msg_rect)
        
        pygame.display.flip()
    
    def draw_canvas(self):
        """Draw the room canvas."""
        # Canvas background
        canvas_rect = pygame.Rect(self.sidebar_width, self.toolbar_height, 
                                  self.screen.get_width() - self.sidebar_width,
                                  self.screen.get_height() - self.toolbar_height)
        pygame.draw.rect(self.screen, (25, 25, 30), canvas_rect)
        
        # Clip
        clip = self.screen.get_clip()
        self.screen.set_clip(canvas_rect)
        
        # Calculate visible tile range
        tile_size_zoomed = TILE_SIZE * self.zoom
        
        start_x = max(0, int(-self.camera_x / tile_size_zoomed))
        start_y = max(0, int(-self.camera_y / tile_size_zoomed))
        end_x = min(self.room.width, int((canvas_rect.width - self.camera_x) / tile_size_zoomed) + 1)
        end_y = min(self.room.height, int((canvas_rect.height - self.camera_y) / tile_size_zoomed) + 1)
        
        # Draw tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.room.tiles[y][x]
                screen_x, screen_y = self.tile_to_screen(x, y)
                
                rect = pygame.Rect(screen_x, screen_y, 
                                  tile_size_zoomed + 1, tile_size_zoomed + 1)
                
                if rect.right < self.sidebar_width or rect.left > self.screen.get_width():
                    continue
                if rect.bottom < self.toolbar_height or rect.top > self.screen.get_height():
                    continue
                
                if self.room.tiles[y][x] == TILE_ICE:
                    color = TILE_COLORS[TILE_ICE]
                    pygame.draw.rect(self.screen, color, rect)
                    continue

                color = TILE_COLORS[tile]
                pygame.draw.rect(self.screen, color, rect)
                
                # Platform and Objects
                # Platform and Objects
                for obj in self.room.objects:
                    ox = obj["x"] * self.zoom + self.camera_x + self.sidebar_width
                    oy = obj["y"] * self.zoom + self.camera_y + self.toolbar_height
                    ow = obj["w"] * self.zoom
                    oh = obj["h"] * self.zoom
                    
                    obj_rect = pygame.Rect(ox, oy, ow, oh)
                    if obj["type"] == OBJ_PLATFORM:
                         pygame.draw.rect(self.screen, (150, 120, 70), obj_rect)
                         pygame.draw.rect(self.screen, (100, 80, 40), obj_rect, 2)
                
                # Platform indicator (Tile)
                if tile == TILE_PLATFORM and self.zoom >= 0.5:
                    top_rect = pygame.Rect(rect.x, rect.y, rect.width, max(2, 4 * self.zoom))
                    pygame.draw.rect(self.screen, (150, 120, 70), top_rect)
        
        # Draw grid
        if self.zoom >= 0.5:
            # Grid lines (16px - Base Tile Size)
            for x in range(start_x, end_x + 1):
                screen_x = x * tile_size_zoomed + self.camera_x + self.sidebar_width
                # Major grid every 2 tiles (32px blocks)
                color = COLOR_GRID_MAJOR if x % 2 == 0 else COLOR_GRID
                pygame.draw.line(self.screen, color,
                               (screen_x, max(self.toolbar_height, self.camera_y + self.toolbar_height)),
                               (screen_x, min(self.screen.get_height(), 
                                            self.room.height * tile_size_zoomed + self.camera_y + self.toolbar_height)))
            
            for y in range(start_y, end_y + 1):
                screen_y = y * tile_size_zoomed + self.camera_y + self.toolbar_height
                # Major grid every 2 tiles (32px blocks)
                color = COLOR_GRID_MAJOR if y % 2 == 0 else COLOR_GRID
                pygame.draw.line(self.screen, color,
                               (max(self.sidebar_width, self.camera_x + self.sidebar_width), screen_y),
                               (min(self.screen.get_width(),
                                   self.room.width * tile_size_zoomed + self.camera_x + self.sidebar_width), screen_y))

        
        # Draw spawn point
        if self.room.spawn:
            x, y = self.room.spawn
            screen_x, screen_y = self.tile_to_screen(x, y)
            spawn_rect = pygame.Rect(screen_x + tile_size_zoomed * 0.2,
                                   screen_y + tile_size_zoomed * 0.2,
                                   tile_size_zoomed * 0.6, tile_size_zoomed * 0.6)
            
            # Draw spawn marker (yellow circle)
            pygame.draw.circle(self.screen, COLOR_SPAWN, spawn_rect.center, int(tile_size_zoomed * 0.4))
            pygame.draw.circle(self.screen, (255, 255, 255), spawn_rect.center, int(tile_size_zoomed * 0.4), 2)
            
            # Label
            if self.zoom >= 0.8:
                label_surf = self.font.render("SPAWN", True, (0, 0, 0))
                label_rect = label_surf.get_rect(center=spawn_rect.center)
                self.screen.blit(label_surf, label_rect)
        
        # Draw line/rect preview
        if self.line_start:
            mouse_pos = pygame.mouse.get_pos()
            if mouse_pos[0] > self.sidebar_width and mouse_pos[1] > self.toolbar_height:
                end_tile = self.screen_to_tile(*mouse_pos)
                start_screen = self.tile_to_screen(*self.line_start)
                end_screen = self.tile_to_screen(*end_tile)
                
                if self.tool == "line":
                    pygame.draw.line(self.screen, COLOR_ACCENT,
                                   (start_screen[0] + tile_size_zoomed/2, 
                                    start_screen[1] + tile_size_zoomed/2),
                                   (end_screen[0] + tile_size_zoomed/2,
                                    end_screen[1] + tile_size_zoomed/2), 2)
                elif self.tool == "rect":
                    x1, y1 = start_screen
                    x2, y2 = end_screen
                    rect = pygame.Rect(min(x1, x2), min(y1, y2),
                                      abs(x2 - x1) + tile_size_zoomed,
                                      abs(y2 - y1) + tile_size_zoomed)
                    pygame.draw.rect(self.screen, COLOR_ACCENT, rect, 2)
        
        # Room bounds outline
        bounds = pygame.Rect(
            self.camera_x + self.sidebar_width,
            self.camera_y + self.toolbar_height,
            self.room.width * tile_size_zoomed,
            self.room.height * tile_size_zoomed
        )
        pygame.draw.rect(self.screen, COLOR_ACCENT, bounds, 2)
        
        # Cursor tile highlight
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] > self.sidebar_width and mouse_pos[1] > self.toolbar_height:
            if self.tool == "platform":
                # Platform cursor (32x16, snaps to 16px grid)
                world_x = (mouse_pos[0] - self.sidebar_width - self.camera_x) / self.zoom
                world_y = (mouse_pos[1] - self.toolbar_height - self.camera_y) / self.zoom
                
                # X: 32px snapping
                grid_x = int(world_x // 32) * 32
                grid_y = int(world_y // 16) * 16
                
                # Platform cursor (32x16)
                screen_x = grid_x * self.zoom + self.camera_x + self.sidebar_width
                screen_y = grid_y * self.zoom + self.camera_y + self.toolbar_height
                
                cursor_rect = pygame.Rect(screen_x, screen_y, 32 * self.zoom, 16 * self.zoom)
                pygame.draw.rect(self.screen, (255, 255, 255), cursor_rect, 2)
            
            else:
                # Normal tile cursor
                tile_x, tile_y = self.screen_to_tile(*mouse_pos)
                
                # Check for Big Block types (Solid, Ice)
                if self.current_tile in (TILE_SOLID, TILE_ICE):
                    # Snap to even grid (32px blocks)
                    snap_x = (tile_x // 2) * 2
                    snap_y = (tile_y // 2) * 2
                    screen_x, screen_y = self.tile_to_screen(snap_x, snap_y)
                    # Cursor is 2x2 tiles (32x32 pixels)
                    cursor_rect = pygame.Rect(screen_x, screen_y, tile_size_zoomed * 2, tile_size_zoomed * 2)
                    pygame.draw.rect(self.screen, (255, 255, 255), cursor_rect, 2)
                else:
                    # Single tile cursor (16x16)
                    if 0 <= tile_x < self.room.width and 0 <= tile_y < self.room.height:
                        screen_x, screen_y = self.tile_to_screen(tile_x, tile_y)
                        cursor_rect = pygame.Rect(screen_x, screen_y, tile_size_zoomed, tile_size_zoomed)
                        pygame.draw.rect(self.screen, (255, 255, 255), cursor_rect, 2)
                
        # Remove clip
        self.screen.set_clip(clip)
    
    def draw_ui(self):
        """Draw the toolbar and sidebar."""
        # --- Toolbar (Top) ---
        toolbar_rect = pygame.Rect(0, 0, self.screen.get_width(), self.toolbar_height)
        pygame.draw.rect(self.screen, COLOR_PANEL, toolbar_rect)
        pygame.draw.line(self.screen, COLOR_GRID_MAJOR, 
                        (0, self.toolbar_height), (self.screen.get_width(), self.toolbar_height))
        
        for btn in self.tool_buttons:
            btn.draw(self.screen, self.font)
        for btn in self.action_buttons:
            btn.draw(self.screen, self.font)
        
        self.width_input.draw(self.screen, self.font)
        self.height_input.draw(self.screen, self.font)
        self.resize_btn.draw(self.screen, self.font)
        self.exit_btn.draw(self.screen, self.font)

        # --- Sidebar (Left) ---
        sidebar_rect = pygame.Rect(0, self.toolbar_height, self.sidebar_width, self.screen.get_height() - self.toolbar_height)
        pygame.draw.rect(self.screen, (30, 30, 40), sidebar_rect)
        pygame.draw.line(self.screen, COLOR_GRID_MAJOR, 
                        (self.sidebar_width, self.toolbar_height), (self.sidebar_width, self.screen.get_height()))
        
        # Sidebar Header
        header_h = 30
        pygame.draw.rect(self.screen, COLOR_PANEL, (0, self.toolbar_height, self.sidebar_width, header_h))
        section_surf = self.font.render("ASSETS", True, COLOR_TEXT_DIM)
        self.screen.blit(section_surf, (15, self.toolbar_height + 8))
        
        # Clip sidebar content
        content_rect = pygame.Rect(0, self.toolbar_height + header_h, self.sidebar_width, self.screen.get_height() - self.toolbar_height - header_h)
        clip = self.screen.get_clip()
        self.screen.set_clip(content_rect)
        
        # Draw tiles with scrolling
        start_y = self.toolbar_height + header_h - self.sidebar_scroll
        
        # Shift buttons for drawing
        for btn in self.tile_buttons:
            original_y = btn.rect.y
            btn.rect.y += start_y
            btn.draw(self.screen, self.font)
            btn.rect.y = original_y # Restore
        
        self.screen.set_clip(clip)
        
        # Info at bottom of sidebar (Fixed)
        info_h = 100
        info_y = self.screen.get_height() - info_h
        pygame.draw.rect(self.screen, COLOR_PANEL, (0, info_y, self.sidebar_width, info_h))
        pygame.draw.line(self.screen, COLOR_GRID_MAJOR, (0, info_y), (self.sidebar_width, info_y))
        
        # Filename
        filename = os.path.basename(self.room.filename) if self.room.filename else "Untitled"
        if self.room.modified:
            filename += "*"
        file_surf = self.font.render(filename, True, COLOR_TEXT)
        self.screen.blit(file_surf, (15, info_y + 10))
        
        # Zoom
        zoom_surf = self.font.render(f"Zoom: {self.zoom:.1f}x", True, COLOR_TEXT_DIM)
        self.screen.blit(zoom_surf, (15, info_y + 28))
        
        # Current tile/tool
        tool_surf = self.font.render(f"Tool: {self.tool.capitalize()}", True, COLOR_TEXT_DIM)
        self.screen.blit(tool_surf, (15, info_y + 46))
        
        # Mouse pos if on canvas
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] > self.sidebar_width and mouse_pos[1] > self.toolbar_height:
            tile_x, tile_y = self.screen_to_tile(*mouse_pos)
            pos_surf = self.font.render(f"Tile: {tile_x}, {tile_y}", True, COLOR_TEXT_DIM)
            self.screen.blit(pos_surf, (15, info_y + 64))
    
    def run(self):
        """Main loop."""
        self.center_view()
        
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            
            self.handle_events()
            self.update(dt)
            self.draw()
        
        # Only quit if running standalone
        if not self.game:
            pygame.quit()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Get rooms directory
    if len(sys.argv) > 1:
        rooms_dir = sys.argv[1]
    else:
        rooms_dir = "rooms"
    
    editor = RoomEditor(rooms_dir)
    editor.run()