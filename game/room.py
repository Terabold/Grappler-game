import pygame
import json
import os

# Tile types
TILE_EMPTY = 0
TILE_SOLID = 1
TILE_SPIKE = 2
TILE_GRAPPLE = 3
TILE_EXIT = 4
TILE_PLATFORM = 5

TILE_COLORS = {
    TILE_EMPTY: None,
    TILE_SOLID: (60, 60, 70),
    TILE_SPIKE: (200, 50, 50),
    TILE_GRAPPLE: (50, 150, 200),
    TILE_EXIT: (50, 200, 80),
    TILE_PLATFORM: (80, 70, 50),
}


class Tile:
    """A single tile with position and type."""
    __slots__ = ('rect', 'tile_type')
    
    def __init__(self, rect, tile_type):
        self.rect = rect
        self.tile_type = tile_type


class Room:
    """A single room loaded from a JSON file (exported from Tiled TMX)."""
    
    def __init__(self, room_id, filepath, world_x, world_y):
        self.room_id = room_id
        self.filepath = filepath
        
        # Position in world (set by world.json)
        self.world_x = world_x
        self.world_y = world_y
        
        # Room data
        self.width = 20   # tiles
        self.height = 12  # tiles
        self.tile_size = 32
        self.tiles = []
        
        # Pixel bounds in world space
        self.bounds = None
        
        # Spawn point (local to room)
        self.spawn = None
        
        self._load(filepath)
    
    def _load(self, filepath):
        """Load room from JSON file (exported from Tiled)."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.width = data.get('width', 20)
        self.height = data.get('height', 12)
        self.tile_size = data.get('tilewidth', 32)
        
        # Calculate bounds in world space
        pixel_width = self.width * self.tile_size
        pixel_height = self.height * self.tile_size
        self.bounds = pygame.Rect(self.world_x, self.world_y, pixel_width, pixel_height)
        
        # Initialize empty tiles
        self.tiles = [[TILE_EMPTY] * self.width for _ in range(self.height)]
        
        # Parse layers
        for layer in data.get('layers', []):
            layer_type = layer.get('type', '')
            layer_name = layer.get('name', '').lower()
            
            if layer_type == 'tilelayer' and 'collision' in layer_name:
                self._parse_tiles(layer)
            elif layer_type == 'objectgroup':
                self._parse_objects(layer)
    
    def _parse_tiles(self, layer):
        """Parse tile layer data."""
        tile_data = layer.get('data', [])
        
        for y in range(self.height):
            for x in range(self.width):
                idx = y * self.width + x
                if idx < len(tile_data):
                    tile_id = tile_data[idx]
                    # Tiled uses 0 for empty, 1+ for tiles
                    if tile_id == 0:
                        self.tiles[y][x] = TILE_EMPTY
                    elif tile_id == 1:
                        self.tiles[y][x] = TILE_SOLID
                    elif tile_id == 2:
                        self.tiles[y][x] = TILE_SPIKE
                    elif tile_id == 3:
                        self.tiles[y][x] = TILE_GRAPPLE
                    elif tile_id == 4:
                        self.tiles[y][x] = TILE_EXIT
                    elif tile_id == 5:
                        self.tiles[y][x] = TILE_PLATFORM
                    else:
                        self.tiles[y][x] = TILE_SOLID
    
    def _parse_objects(self, layer):
        """Parse object layer for spawn points etc."""
        for obj in layer.get('objects', []):
            obj_type = obj.get('type', '').lower()
            obj_name = obj.get('name', '').lower()
            
            if 'spawn' in obj_type or 'spawn' in obj_name:
                self.spawn = (obj.get('x', 64), obj.get('y', 64))
    
    def get_spawn_world(self):
        """Get spawn point in world coordinates."""
        if self.spawn:
            return (self.world_x + self.spawn[0], self.world_y + self.spawn[1])
        return (self.world_x + 64, self.world_y + 64)
    
    def contains_point(self, x, y):
        """Check if world point is inside this room."""
        return self.bounds.collidepoint(x, y)
    
    def get_collisions(self, rect):
        """Get tile collisions for a rect (in world coords)."""
        results = []
        
        # Convert world rect to local tile coordinates
        local_left = rect.left - self.world_x
        local_top = rect.top - self.world_y
        local_right = rect.right - self.world_x
        local_bottom = rect.bottom - self.world_y
        
        start_x = max(0, int(local_left // self.tile_size) - 1)
        end_x = min(self.width, int(local_right // self.tile_size) + 2)
        start_y = max(0, int(local_top // self.tile_size) - 1)
        end_y = min(self.height, int(local_bottom // self.tile_size) + 2)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile_type = self.tiles[y][x]
                if tile_type in (TILE_SOLID, TILE_PLATFORM):
                    tile_rect = pygame.Rect(
                        self.world_x + x * self.tile_size,
                        self.world_y + y * self.tile_size,
                        self.tile_size,
                        self.tile_size
                    )
                    if rect.colliderect(tile_rect):
                        results.append(Tile(tile_rect, tile_type))
        
        return results
    
    def get_solid_collisions(self, rect):
        """Get only solid tile collisions (no platforms)."""
        results = []
        
        local_left = rect.left - self.world_x
        local_top = rect.top - self.world_y
        local_right = rect.right - self.world_x
        local_bottom = rect.bottom - self.world_y
        
        start_x = max(0, int(local_left // self.tile_size) - 1)
        end_x = min(self.width, int(local_right // self.tile_size) + 2)
        start_y = max(0, int(local_top // self.tile_size) - 1)
        end_y = min(self.height, int(local_bottom // self.tile_size) + 2)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if self.tiles[y][x] == TILE_SOLID:
                    tile_rect = pygame.Rect(
                        self.world_x + x * self.tile_size,
                        self.world_y + y * self.tile_size,
                        self.tile_size,
                        self.tile_size
                    )
                    if rect.colliderect(tile_rect):
                        results.append(tile_rect)
        
        return results
    
    def draw(self, surface, camera):
        """Draw visible tiles."""
        view_rect = pygame.Rect(camera.x, camera.y, camera.view_width, camera.view_height)
        if not view_rect.colliderect(self.bounds):
            return
        
        for y in range(self.height):
            for x in range(self.width):
                tile_type = self.tiles[y][x]
                if tile_type == TILE_EMPTY:
                    continue
                
                world_rect = pygame.Rect(
                    self.world_x + x * self.tile_size,
                    self.world_y + y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                
                screen_rect = camera.apply_rect(world_rect)
                color = TILE_COLORS.get(tile_type, (100, 100, 100))
                
                if color:
                    pygame.draw.rect(surface, color, screen_rect)
                    
                    if tile_type == TILE_PLATFORM:
                        top_line = pygame.Rect(screen_rect.x, screen_rect.y, screen_rect.width, 4)
                        pygame.draw.rect(surface, (120, 100, 70), top_line)


class RoomManager:
    """
    Manages rooms using world.json for layout.
    
    Each room is a separate JSON file (exported from Tiled TMX).
    world.json tells the game where each room is positioned.
    """
    
    def __init__(self, rooms_dir):
        self.rooms_dir = rooms_dir
        self.rooms = {}
        self.current_room = None
        self.camera = None
        self.spawn = (100, 100)
    
    def set_camera(self, camera):
        self.camera = camera
        if self.current_room:
            self.camera.set_bounds(self.current_room.bounds)
    
    def load_world(self, world_file):
        """
        Load world.json which defines room positions.
        
        Format:
        {
            "start": "room_01",
            "rooms": [
                {"id": "room_01", "file": "room_01.json", "x": 0, "y": 0},
                {"id": "room_02", "file": "room_02.json", "x": 640, "y": 0}
            ]
        }
        """
        world_path = os.path.join(self.rooms_dir, world_file)
        
        with open(world_path, 'r') as f:
            data = json.load(f)
        
        start_room_id = data.get('start', 'room_01')
        
        for room_data in data.get('rooms', []):
            room_id = room_data.get('id')
            room_file = room_data.get('file', f"{room_id}.json")
            world_x = room_data.get('x', 0)
            world_y = room_data.get('y', 0)
            
            room_path = os.path.join(self.rooms_dir, room_file)
            if os.path.exists(room_path):
                room = Room(room_id, room_path, world_x, world_y)
                self.rooms[room_id] = room
                
                if room_id == start_room_id and room.spawn:
                    self.spawn = room.get_spawn_world()
        
        if start_room_id in self.rooms:
            self.current_room = self.rooms[start_room_id]
            if self.camera:
                self.camera.set_bounds(self.current_room.bounds)
    
    def load_chapter(self, chapter_file):
        """Load chapter - just calls load_world."""
        self.load_world(chapter_file)
    
    def get_collisions(self, rect):
        """Get collisions from current room only."""
        if self.current_room:
            return self.current_room.get_collisions(rect)
        return []
    
    def get_solid_collisions(self, rect):
        """Get solid collisions from current room only."""
        if self.current_room:
            return self.current_room.get_solid_collisions(rect)
        return []
    
    def check_room_transition(self, player_rect):
        """Check if player should transition to another room."""
        if not self.current_room:
            return None
        
        cx, cy = player_rect.centerx, player_rect.centery
        
        if self.current_room.contains_point(cx, cy):
            return None
        
        for room_id, room in self.rooms.items():
            if room == self.current_room:
                continue
            
            if room.contains_point(cx, cy):
                old_bounds = self.current_room.bounds
                new_bounds = room.bounds
                
                if new_bounds.left >= old_bounds.right - 10:
                    direction = "right"
                elif new_bounds.right <= old_bounds.left + 10:
                    direction = "left"
                elif new_bounds.top >= old_bounds.bottom - 10:
                    direction = "down"
                else:
                    direction = "up"
                
                return (room_id, direction)
        
        return None
    
    def transition_to(self, room_id, direction, callback=None):
        """Transition camera to new room."""
        if room_id not in self.rooms:
            return
        
        new_room = self.rooms[room_id]
        
        def on_complete():
            self.current_room = new_room
            if callback:
                callback()
        
        if self.camera:
            self.camera.start_transition(new_room.bounds, direction, on_complete)
        else:
            self.current_room = new_room
            if callback:
                callback()
    
    def draw(self, surface, camera):
        """Draw all visible rooms."""
        for room in self.rooms.values():
            room.draw(surface, camera)