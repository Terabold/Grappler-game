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

TILE_SIZE = 32
DEFAULT_ROOM_WIDTH = 20   # tiles
DEFAULT_ROOM_HEIGHT = 12  # tiles

# Tile types
TILE_EMPTY = 0
TILE_SOLID = 1
TILE_SPIKE = 2
TILE_GRAPPLE = 3
TILE_EXIT = 4
TILE_PLATFORM = 5

TILE_NAMES = {
    TILE_EMPTY: "Empty",
    TILE_SOLID: "Solid",
    TILE_SPIKE: "Spike",
    TILE_GRAPPLE: "Grapple",
    TILE_EXIT: "Exit",
    TILE_PLATFORM: "Platform",
}

TILE_COLORS = {
    TILE_EMPTY: (30, 30, 40),
    TILE_SOLID: (60, 60, 70),
    TILE_SPIKE: (200, 50, 50),
    TILE_GRAPPLE: (50, 150, 200),
    TILE_EXIT: (50, 200, 80),
    TILE_PLATFORM: (120, 90, 50),
}

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
COLOR_SPAWN = (255, 220, 50)

# ============================================================================
# ROOM DATA
# ============================================================================

class RoomData:
    """Stores room tile data and metadata."""
    
    def __init__(self, width=DEFAULT_ROOM_WIDTH, height=DEFAULT_ROOM_HEIGHT):
        self.width = width
        self.height = height
        self.tiles = [[TILE_EMPTY] * width for _ in range(height)]
        # Entry points: list of (x, y, from_room)
        self.entry_points = []
        # Index of entry point that serves as start/respawn point (None if none set)
        self.start_entry_index = None
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
        
        # Keep entry points in bounds
        new_entry_points = []
        for i, (x, y, from_room) in enumerate(self.entry_points):
            new_x = min(x, new_width - 1)
            new_y = min(y, new_height - 1)
            new_entry_points.append((new_x, new_y, from_room))
        
        self.entry_points = new_entry_points
        
        # Update start entry index if it's still valid
        if self.start_entry_index is not None and self.start_entry_index >= len(self.entry_points):
            self.start_entry_index = None
            
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
            self.spawn_x = x
            self.spawn_y = y
            self.modified = True
    
    def get_tile(self, x, y):
        """Get tile at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return TILE_EMPTY
    
    def add_entry_point(self, x, y, from_room="start"):
        """Add an entry point."""
        self.entry_points.append((x, y, from_room))
        self.modified = True
    
    def remove_entry_point(self, index):
        """Remove an entry point."""
        if 0 <= index < len(self.entry_points):
            self.entry_points.pop(index)
            self.modified = True
    
    def set_entry_point_room(self, index, from_room):
        """Set the from_room for an entry point."""
        if 0 <= index < len(self.entry_points):
            x, y, _ = self.entry_points[index]
            self.entry_points[index] = (x, y, from_room)
            self.modified = True
    
    def set_entry_point_start(self, index, is_start):
        """Set whether an entry point is the start point."""
        if is_start:
            # Only one start point allowed - clear any existing
            self.start_entry_index = index
        elif self.start_entry_index == index:
            self.start_entry_index = None
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
        """Clear all tiles."""
        self.tiles = [[TILE_EMPTY] * self.width for _ in range(self.height)]
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
                            "name": "entry",
                            "type": "entry",
                            "x": x * TILE_SIZE + TILE_SIZE // 2,
                            "y": y * TILE_SIZE + TILE_SIZE // 2,
                            "properties": {
                                "from_room": from_room,
                                "is_start": i == self.start_entry_index
                            }
                        } for i, (x, y, from_room) in enumerate(self.entry_points)
                    ]
                }
            ]
        }
    
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
                    if obj.get("type") == "entry" or obj.get("name") == "entry":
                        x = int(obj.get("x", 64) // TILE_SIZE)
                        y = int(obj.get("y", 64) // TILE_SIZE)
                        from_room = obj.get("properties", {}).get("from_room") or obj.get("from_room", "start")
                        is_start = obj.get("properties", {}).get("is_start", False)
                        
                        self.entry_points.append((x, y, from_room))
                        
                        # Set start entry index
                        if is_start:
                            self.start_entry_index = len(self.entry_points) - 1
        
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
        self.tool = "paint"  # paint, fill, line, rect, spawn, entry
        self.painting = False
        self.erasing = False
        
        # Line/rect tool state
        self.line_start = None
        
        # UI
        self.panel_width = 200
        self.setup_ui()
        
        # Entry point editor
        self.entry_editor = None  # Will be EntryPointEditor instance
        self.selected_entry_point = None  # Index of selected entry point
        
        # Double-click detection for entry points
        self._last_entry_click = 0
        self._last_entry_index = None
        
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
        # Tile buttons in a 3x2 grid for compactness
        self.tile_buttons = []
        start_x = 15
        start_y = 50
        size = 32
        spacing = 50  # Enough for label below
        cols = 3
        
        for tile_type in range(6):
            col = tile_type % cols
            row = tile_type // cols
            x = start_x + col * spacing
            y = start_y + row * (size + 25)  # Extra space for label
            btn = TileButton(x, y, size, tile_type)
            if tile_type == self.current_tile:
                btn.active = True
            self.tile_buttons.append(btn)
        
        # Tool buttons in a row/compact vertical list
        self.tool_buttons = []
        tools = [("Paint", "paint"), ("Fill", "fill"), ("Line", "line"), 
                 ("Rect", "rect"), ("Entry", "entry")]
        
        y = 170
        for i, (name, tool) in enumerate(tools):
            btn = Button(15, y + i * 32, 80, 26, name, toggle=True)
            btn.tool = tool
            if tool == self.tool:
                btn.active = True
            self.tool_buttons.append(btn)
        
        # Size inputs
        y_size = 350
        self.width_input = InputBox(15, y_size, 50, 22, str(self.room.width), "W")
        self.height_input = InputBox(80, y_size, 50, 22, str(self.room.height), "H")
        self.resize_btn = Button(140, y_size, 40, 22, "Set", self.apply_resize)
        
        # Action buttons - compact 2-column layout
        y = 400
        btn_w = 85
        btn_h = 26
        gap = 5
        
        self.action_buttons = [
            Button(15, y, btn_w, btn_h, "New", self.new_room),
            Button(15 + btn_w + gap, y, btn_w, btn_h, "Open", self.open_room),
            Button(15, y + btn_h + gap, btn_w, btn_h, "Save", self.save_room),
            Button(15 + btn_w + gap, y + btn_h + gap, btn_w, btn_h, "Save As", self.save_room_as),
            Button(15, y + (btn_h + gap) * 2, btn_w, btn_h, "Borders", self.room.fill_borders),
            Button(15 + btn_w + gap, y + (btn_h + gap) * 2, btn_w, btn_h, "Clear", self.clear_room),
        ]
        
        # Back button at bottom
        self.action_buttons.append(Button(15, self.screen.get_height() - 80, self.panel_width - 30, 35, "Back to Menu", self.exit_editor))
        
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
            'entry_points': self.room.entry_points[:],
            'start_entry_index': self.room.start_entry_index
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
            'spawn_x': self.room.spawn_x,
            'spawn_y': self.room.spawn_y,
            'entry_points': self.room.entry_points[:]
        }
        self.redo_stack.append(current)
        
        # Restore previous
        state = self.undo_stack.pop()
        self.room.tiles = state['tiles']
        self.room.entry_points = state['entry_points']
        self.room.start_entry_index = state.get('start_entry_index', None)
        self.room.modified = True
        self.show_message("Undo")
    
    def redo(self):
        """Redo last undone action."""
        if not self.redo_stack:
            return
        
        # Save current for undo
        current = {
            'tiles': [row[:] for row in self.room.tiles],
            'spawn_x': self.room.spawn_x,
            'spawn_y': self.room.spawn_y,
        }
        self.undo_stack.append(current)
        
        # Restore
        state = self.redo_stack.pop()
        self.room.tiles = state['tiles']
        self.room.entry_points = state['entry_points']
        self.room.start_entry_index = state.get('start_entry_index', None)
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
        canvas_width = self.screen.get_width() - self.panel_width
        canvas_height = self.screen.get_height()
        
        room_pixel_width = self.room.width * TILE_SIZE * self.zoom
        room_pixel_height = self.room.height * TILE_SIZE * self.zoom
        
        self.camera_x = (canvas_width - room_pixel_width) / 2
        self.camera_y = (canvas_height - room_pixel_height) / 2
    
    def screen_to_tile(self, screen_x, screen_y):
        """Convert screen position to tile coordinates."""
        # Adjust for panel
        world_x = (screen_x - self.panel_width - self.camera_x) / self.zoom
        world_y = (screen_y - self.camera_y) / self.zoom
        
        tile_x = int(world_x // TILE_SIZE)
        tile_y = int(world_y // TILE_SIZE)
        
        return tile_x, tile_y
    
    def tile_to_screen(self, tile_x, tile_y):
        """Convert tile coordinates to screen position."""
        screen_x = tile_x * TILE_SIZE * self.zoom + self.camera_x + self.panel_width
        screen_y = tile_y * TILE_SIZE * self.zoom + self.camera_y
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
                        self.center_view()
                        self.show_message(f"Loaded: {os.path.basename(result)}")
                continue
            
            # Entry editor
            if self.entry_editor and self.entry_editor.active:
                self.entry_editor.handle_event(event)
                continue
            
            # Input boxes
            self.width_input.handle_event(event)
            self.height_input.handle_event(event)
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicked = True
                
                # Right click to remove
                if event.button == 3 and event.pos[0] > self.panel_width:
                    tile_x, tile_y = self.screen_to_tile(*event.pos)
                    
                    # Check if clicking on an entry point
                    removed_entry = False
                    for i, (ex, ey, from_room) in enumerate(self.room.entry_points):
                        if ex == tile_x and ey == tile_y:
                            self.save_undo()
                            self.room.remove_entry_point(i)
                            if self.selected_entry_point == i:
                                self.selected_entry_point = None
                            elif self.selected_entry_point and self.selected_entry_point > i:
                                self.selected_entry_point -= 1
                            self.show_message("Entry point removed")
                            removed_entry = True
                            break
                    
                    # If not an entry point, clear the tile
                    if not removed_entry and 0 <= tile_x < self.room.width and 0 <= tile_y < self.room.height:
                        if self.room.tiles[tile_y][tile_x] != TILE_EMPTY:
                            self.save_undo()
                            self.room.set_tile(tile_x, tile_y, TILE_EMPTY)
                            self.show_message("Tile cleared")
                
                # Left click for tools (in canvas area)
                elif event.button == 1 and event.pos[0] > self.panel_width:
                    tile_x, tile_y = self.screen_to_tile(*event.pos)
                    
                    if self.tool == "entry":
                        # Check if clicking on existing entry point
                        clicked_existing = False
                        for i, (ex, ey, from_room) in enumerate(self.room.entry_points):
                            if ex == tile_x and ey == tile_y:
                                self.selected_entry_point = i
                                clicked_existing = True
                                
                                # Check for double click
                                current_time = pygame.time.get_ticks()
                                if hasattr(self, '_last_entry_click') and hasattr(self, '_last_entry_index'):
                                    if (current_time - self._last_entry_click < 400 and 
                                        self._last_entry_index == i):
                                        # Double click - edit entry point
                                        is_start = (i == self.room.start_entry_index)
                                        self.entry_editor = EntryPointEditor(
                                            event.pos[0], event.pos[1], i, from_room, self.edit_entry_point, self.rooms_dir, is_start
                                        )
                                        break
                                
                                self._last_entry_click = current_time
                                self._last_entry_index = i
                                break
                        
                        if not clicked_existing:
                            self.save_undo()
                            # For now, default to "start" - user can edit later
                            self.room.add_entry_point(tile_x, tile_y, "start")
                            self.selected_entry_point = len(self.room.entry_points) - 1
                    elif self.tool == "fill":
                        target = self.room.get_tile(tile_x, tile_y)
                        self.save_undo()
                        self.flood_fill(tile_x, tile_y, target, self.current_tile)
                    elif self.tool in ("line", "rect"):
                        self.line_start = (tile_x, tile_y)
                    else:
                        self.painting = True
                        self.save_undo()
                        self.room.set_tile(tile_x, tile_y, self.current_tile)
                
                # Right click to remove
                elif event.button == 3 and event.pos[0] > self.panel_width:
                    tile_x, tile_y = self.screen_to_tile(*event.pos)
                    
                    # Check if clicking on an entry point
                    removed_entry = False
                    for i, (ex, ey, from_room) in enumerate(self.room.entry_points):
                        if ex == tile_x and ey == tile_y:
                            self.save_undo()
                            self.room.remove_entry_point(i)
                            if self.selected_entry_point == i:
                                self.selected_entry_point = None
                            elif self.selected_entry_point and self.selected_entry_point > i:
                                self.selected_entry_point -= 1
                            self.show_message("Entry point removed")
                            removed_entry = True
                            break
                    
                    # If not an entry point, clear the tile
                    if not removed_entry and 0 <= tile_x < self.room.width and 0 <= tile_y < self.room.height:
                        if self.room.tiles[tile_y][tile_x] != TILE_EMPTY:
                            self.save_undo()
                            self.room.set_tile(tile_x, tile_y, TILE_EMPTY)
                            self.show_message("Tile cleared")
                
                # Scroll to zoom
                elif event.button == 4:  # Scroll up
                    old_zoom = self.zoom
                    self.zoom = min(self.max_zoom, self.zoom * 1.2)
                    # Zoom toward mouse
                    if event.pos[0] > self.panel_width:
                        factor = self.zoom / old_zoom
                        mx = event.pos[0] - self.panel_width
                        my = event.pos[1]
                        self.camera_x = mx - (mx - self.camera_x) * factor
                        self.camera_y = my - (my - self.camera_y) * factor
                
                elif event.button == 5:  # Scroll down
                    old_zoom = self.zoom
                    self.zoom = max(self.min_zoom, self.zoom / 1.2)
                    if event.pos[0] > self.panel_width:
                        factor = self.zoom / old_zoom
                        mx = event.pos[0] - self.panel_width
                        my = event.pos[1]
                        self.camera_x = mx - (mx - self.camera_x) * factor
                        self.camera_y = my - (my - self.camera_y) * factor
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3):
                    self.dragging_camera = False
                
                elif event.button == 1:
                    self.painting = False
                    
                    # Complete line/rect
                    if self.line_start and event.pos[0] > self.panel_width:
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
                
                elif self.painting and event.pos[0] > self.panel_width:
                    tile_x, tile_y = self.screen_to_tile(*event.pos)
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
                                  pygame.K_3, pygame.K_4, pygame.K_5):
                    tile = event.key - pygame.K_0
                    if tile < len(self.tile_buttons):
                        self.current_tile = tile
                        for btn in self.tile_buttons:
                            btn.active = btn.tile_type == tile
                
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
                    if self.selected_entry_point is not None:
                        self.save_undo()
                        self.room.remove_entry_point(self.selected_entry_point)
                        self.selected_entry_point = None
                        self.show_message("Entry point deleted")
                
                # Escape key - cancel tool or exit
                elif event.key == pygame.K_ESCAPE:
                    if self.line_start:
                        self.line_start = None
                    elif self.selected_entry_point is not None:
                        self.selected_entry_point = None
                    elif self.file_dialog.active:
                        self.file_dialog.close()
                    elif self.entry_editor and self.entry_editor.active:
                        self.entry_editor.close()
                    else:
                        self.exit_editor()
            
            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        
        # UI button updates
        if not self.file_dialog.active:
            # Tile buttons
            for btn in self.tile_buttons:
                if btn.update(mouse_pos, mouse_clicked):
                    self.current_tile = btn.tile_type
                    for other in self.tile_buttons:
                        other.active = other.tile_type == self.current_tile
            
            # Tool buttons
            for btn in self.tool_buttons:
                if btn.update(mouse_pos, mouse_clicked):
                    self.set_tool(btn.tool)
            
            # Action buttons
            for btn in self.action_buttons:
                btn.update(mouse_pos, mouse_clicked)
            
            self.resize_btn.update(mouse_pos, mouse_clicked)
    def set_tool(self, tool):

        """Set current tool."""
        self.tool = tool
        for btn in self.tool_buttons:
            btn.active = btn.tool == tool
        self.line_start = None
    
    def update(self, dt):
        """Update editor state."""
        mouse_pos = pygame.mouse.get_pos()
        
        self.width_input.update(dt)
        self.height_input.update(dt)
        self.file_dialog.update(dt)
        
        if self.entry_editor:
            self.entry_editor.update(dt, mouse_pos)
            if not self.entry_editor.active:
                self.entry_editor = None
        
        if self.message_timer > 0:
            self.message_timer -= dt
    
    def draw(self):
        """Draw everything."""
        self.screen.fill(COLOR_BG)
        
        # Draw canvas area
        self.draw_canvas()
        
        # Draw panel
        self.draw_panel()
        
        # Draw file dialog
        self.file_dialog.draw(self.screen, self.font)
        
        # Draw entry editor
        if self.entry_editor:
            self.entry_editor.draw(self.screen, self.font)
        
        # Draw message
        if self.message_timer > 0:
            msg_surf = self.font_large.render(self.message, True, COLOR_TEXT)
            msg_rect = msg_surf.get_rect(centerx=self.screen.get_width() // 2 + self.panel_width // 2, 
                                        bottom=self.screen.get_height() - 20)
            pygame.draw.rect(self.screen, COLOR_PANEL, msg_rect.inflate(20, 10))
            self.screen.blit(msg_surf, msg_rect)
        
        pygame.display.flip()
    
    def draw_canvas(self):
        """Draw the room canvas."""
        # Canvas background
        canvas_rect = pygame.Rect(self.panel_width, 0, 
                                  self.screen.get_width() - self.panel_width,
                                  self.screen.get_height())
        pygame.draw.rect(self.screen, (25, 25, 30), canvas_rect)
        
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
                
                # Clip to canvas
                if rect.right < self.panel_width or rect.left > self.screen.get_width():
                    continue
                
                color = TILE_COLORS[tile]
                pygame.draw.rect(self.screen, color, rect)
                
                # Platform indicator
                if tile == TILE_PLATFORM and self.zoom >= 0.5:
                    top_rect = pygame.Rect(rect.x, rect.y, rect.width, max(2, 4 * self.zoom))
                    pygame.draw.rect(self.screen, (150, 120, 70), top_rect)
        
        # Draw grid
        if self.zoom >= 0.5:
            for x in range(start_x, end_x + 1):
                screen_x = x * tile_size_zoomed + self.camera_x + self.panel_width
                color = COLOR_GRID_MAJOR if x % 5 == 0 else COLOR_GRID
                pygame.draw.line(self.screen, color,
                               (screen_x, max(0, self.camera_y)),
                               (screen_x, min(self.screen.get_height(), 
                                            self.room.height * tile_size_zoomed + self.camera_y)))
            
            for y in range(start_y, end_y + 1):
                screen_y = y * tile_size_zoomed + self.camera_y
                color = COLOR_GRID_MAJOR if y % 5 == 0 else COLOR_GRID
                pygame.draw.line(self.screen, color,
                               (max(self.panel_width, self.camera_x + self.panel_width), screen_y),
                               (min(self.screen.get_width(),
                                   self.room.width * tile_size_zoomed + self.camera_x + self.panel_width), screen_y))
        
        # Draw entry points
        for i, (x, y, from_room) in enumerate(self.room.entry_points):
            screen_x, screen_y = self.tile_to_screen(x, y)
            entry_rect = pygame.Rect(screen_x + tile_size_zoomed * 0.1,
                                   screen_y + tile_size_zoomed * 0.1,
                                   tile_size_zoomed * 0.8, tile_size_zoomed * 0.8)
            
            # Highlight selected entry point
            if i == self.selected_entry_point:
                pygame.draw.rect(self.screen, (255, 255, 100), entry_rect)
                pygame.draw.rect(self.screen, (255, 220, 50), entry_rect, 3)
            else:
                pygame.draw.rect(self.screen, (100, 200, 255), entry_rect)
                pygame.draw.rect(self.screen, (150, 220, 255), entry_rect, 2)
            
            # Label with room name if zoom allows
            if self.zoom >= 0.8:
                label = from_room[:6]  # Truncate long names
                label_surf = self.font.render(label, True, (255, 255, 255))
                label_rect = label_surf.get_rect(centerx=screen_x + tile_size_zoomed/2,
                                                top=screen_y + tile_size_zoomed + 2)
                # Background for readability
                bg_rect = label_rect.inflate(4, 2)
                pygame.draw.rect(self.screen, (0, 0, 0, 128), bg_rect)
                self.screen.blit(label_surf, label_rect)
        
        # Draw line/rect preview
        if self.line_start:
            mouse_pos = pygame.mouse.get_pos()
            if mouse_pos[0] > self.panel_width:
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
            self.camera_x + self.panel_width,
            self.camera_y,
            self.room.width * tile_size_zoomed,
            self.room.height * tile_size_zoomed
        )
        pygame.draw.rect(self.screen, COLOR_ACCENT, bounds, 2)
        
        # Cursor tile highlight
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] > self.panel_width:
            tile_x, tile_y = self.screen_to_tile(*mouse_pos)
            if 0 <= tile_x < self.room.width and 0 <= tile_y < self.room.height:
                screen_x, screen_y = self.tile_to_screen(tile_x, tile_y)
                cursor_rect = pygame.Rect(screen_x, screen_y, tile_size_zoomed, tile_size_zoomed)
                pygame.draw.rect(self.screen, (255, 255, 255), cursor_rect, 2)
    
    def draw_panel(self):
        """Draw the side panel."""
        panel_rect = pygame.Rect(0, 0, self.panel_width, self.screen.get_height())
        pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect)
        pygame.draw.line(self.screen, COLOR_GRID_MAJOR, 
                        (self.panel_width, 0), (self.panel_width, self.screen.get_height()))
        
        # Title
        title = "Room Editor"
        title_surf = self.font_large.render(title, True, COLOR_TEXT)
        self.screen.blit(title_surf, (15, 15))
        
        # Tile section label
        section_surf = self.font.render("TILES (0-5)", True, COLOR_TEXT_DIM)
        self.screen.blit(section_surf, (15, 35))
        
        for btn in self.tile_buttons:
            btn.draw(self.screen, self.font)
        
        # Tool section label
        section_surf = self.font.render("TOOLS", True, COLOR_TEXT_DIM)
        self.screen.blit(section_surf, (15, 155))
        
        for btn in self.tool_buttons:
            btn.draw(self.screen, self.font)
        
        # Size section label
        section_surf = self.font.render("ROOM SIZE", True, COLOR_TEXT_DIM)
        self.screen.blit(section_surf, (15, 300))
        
        self.width_input.draw(self.screen, self.font)
        self.height_input.draw(self.screen, self.font)
        self.resize_btn.draw(self.screen, self.font)
        
        # File section label
        section_surf = self.font.render("FILE", True, COLOR_TEXT_DIM)
        self.screen.blit(section_surf, (15, 355))
        
        for btn in self.action_buttons:
            btn.draw(self.screen, self.font)
        
        # Info at bottom
        info_y = self.screen.get_height() - 120
        
        # Filename
        filename = os.path.basename(self.room.filename) if self.room.filename else "Untitled"
        if self.room.modified:
            filename += "*"
        file_surf = self.font.render(filename, True, COLOR_TEXT)
        self.screen.blit(file_surf, (15, info_y))
        
        # Zoom
        zoom_surf = self.font.render(f"Zoom: {self.zoom:.1f}x", True, COLOR_TEXT_DIM)
        self.screen.blit(zoom_surf, (15, info_y + 18))
        
        # Current tile/tool
        tool_surf = self.font.render(f"Tool: {self.tool.capitalize()}", True, COLOR_TEXT_DIM)
        self.screen.blit(tool_surf, (15, info_y + 36))
        
        # Mouse pos if on canvas
        mouse_pos = pygame.mouse.get_pos()
        if mouse_pos[0] > self.panel_width:
            tile_x, tile_y = self.screen_to_tile(*mouse_pos)
            pos_surf = self.font.render(f"Tile: {tile_x}, {tile_y}", True, COLOR_TEXT_DIM)
            self.screen.blit(pos_surf, (15, info_y + 54))
    
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