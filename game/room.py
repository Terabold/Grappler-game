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
OBJ_PLATFORM = "platform"

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
        
        # Room Objects
        self.objects = []
        
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
        """Parse object layer for spawn point and game objects."""
        for obj in layer.get('objects', []):
            obj_type = obj.get('type', '').lower()
            obj_name = obj.get('name', '').lower()
            
            # Spawn point
            if 'spawn' in obj_type or 'spawn' in obj_name:
                self.spawn = (obj.get('x', 64), obj.get('y', 64))
            
            # Platforms / Planks
            elif obj_type == OBJ_PLATFORM:
                # Create RoomObject
                # Note: Tiled objects are (x, y) = Top Left
                x = obj.get('x', 0)
                y = obj.get('y', 0)
                w = obj.get('width', 32)
                h = obj.get('height', 16)
                
                new_obj = RoomObject(x, y, w, h, obj_type)
                new_obj.world_x = self.world_x + x
                new_obj.world_y = self.world_y + y
                self.objects.append(new_obj)
    
    def get_spawn_world(self):
        """Get spawn point in world coordinates."""
        if self.spawn:
            return (self.world_x + self.spawn[0], self.world_y + self.spawn[1])
        return (self.world_x + 64, self.world_y + 64)
    
    
    def contains_point(self, x, y):
        """Check if world point is inside this room."""
        return self.bounds.collidepoint(x, y)
    
    def get_collisions(self, rect):
        """Get tile collisions for a rect (in world coords). Returns ALL non-empty tiles."""
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
                # Return ALL non-empty tiles (spikes, grapple, exit, solid, platform)
                if tile_type != TILE_EMPTY:
                    tile_rect = pygame.Rect(
                        self.world_x + x * self.tile_size,
                        self.world_y + y * self.tile_size,
                        self.tile_size,
                        self.tile_size
                    )
                    if rect.colliderect(tile_rect):
                        results.append(Tile(tile_rect, tile_type))
        
        return results

    def get_object_collisions(self, rect):
        """Get object collisions for a world-space rect."""
        results = []
        for obj in self.objects:
            # Simple AABB check first
            if rect.colliderect(obj.rect):
                results.append(obj)
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
        """Draw visible tiles (Optimized viewport culling)."""
        # 1. Viewport Culling: Only draw tiles strictly inside the camera view
        # Convert camera top-left to tile coordinates
        start_col = int(max(0, (camera.x - self.world_x) // self.tile_size))
        start_row = int(max(0, (camera.y - self.world_y) // self.tile_size))
        
        # Convert camera bottom-right to tile coordinates
        # We add 1 or 2 extra tiles to be safe against rounding/partial tiles
        end_col = int(min(self.width, (camera.x + camera.view_width - self.world_x) // self.tile_size + 1))
        end_row = int(min(self.height, (camera.y + camera.view_height - self.world_y) // self.tile_size + 1))
        
        for y in range(start_row, end_row):
            for x in range(start_col, end_col):
                tile_type = self.tiles[y][x]
                if tile_type == TILE_EMPTY:
                    continue
                
                # World position of this tile
                world_x = self.world_x + x * self.tile_size
                world_y = self.world_y + y * self.tile_size
                
                # Screen position
                screen_rect = camera.apply_rect(pygame.Rect(world_x, world_y, self.tile_size, self.tile_size))
                
                color = TILE_COLORS.get(tile_type, (100, 100, 100))
                
                if color:
                    pygame.draw.rect(surface, color, screen_rect)
                    
                    if tile_type == TILE_PLATFORM:
                        # Draw platform top detail
                        top_line = pygame.Rect(screen_rect.x, screen_rect.y, screen_rect.width, max(1, int(4 * camera.scale_y)))
                        pygame.draw.rect(surface, (120, 100, 70), top_line)
        
        # Draw Objects
        for obj in self.objects:
            obj.draw(surface, camera)


class RoomObject:
    """A game object (e.g. platform) with visual and collision properties."""
    def __init__(self, x, y, width, height, type_name):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.type = type_name
        self.world_x = 0 # Updates when room loads
        self.world_y = 0
        
        self.image = None
        self.mask = None
        
        # Attempt to load asset
        self._load_asset()
        
    @property
    def rect(self):
        return pygame.Rect(self.world_x, self.world_y, self.width, self.height)
        
    def _load_asset(self):
        """Load specific asset image based on type."""
        # Simple mapping for now
        filename = None
        if self.type == OBJ_PLATFORM:
            # We assume assets folder structure
            # If width is 32, look for plank32.png, else plank.png etc.
            filename = "assets/objects/plank.png" 
            
        if filename and os.path.exists(filename):
            try:
                raw_img = pygame.image.load(filename).convert_alpha()
                # Scale if necessary, or tile? For now, scale to fit object dimensions
                self.image = pygame.transform.scale(raw_img, (int(self.width), int(self.height)))
                self.mask = pygame.mask.from_surface(self.image)
            except Exception as e:
                print(f"Failed to load asset {filename}: {e}")
                self.image = None
    
    def draw(self, surface, camera):
        screen_rect = camera.apply_rect(self.rect)
        
        if self.image:
            # Scale image dynamically with camera zoom
            scaled_img = pygame.transform.scale(self.image, (screen_rect.width, screen_rect.height))
            surface.blit(scaled_img, screen_rect)
        else:
            # Fallback drawing
            if self.type == OBJ_PLATFORM:
                pygame.draw.rect(surface, (150, 120, 70), screen_rect)
                pygame.draw.rect(surface, (100, 80, 40), screen_rect, 2)
            else:
                pygame.draw.rect(surface, (255, 0, 255), screen_rect, 1)


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
        self.respawn_data = None  # {room_id, x, y, facing_right}
    
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
                
                if room_id == start_room_id:
                    if room.spawn:
                        self.spawn = room.get_spawn_world()
                    else:
                        self.spawn = (room.world_x + 64, room.world_y + 64)
                    
                    # Set initial respawn data
                    self.respawn_data = {
                        'room_id': room_id,
                        'x': self.spawn[0],
                        'y': self.spawn[1],
                        'facing_right': True
                    }
        
        if start_room_id in self.rooms:
            self.current_room = self.rooms[start_room_id]
            if self.camera:
                self.camera.set_bounds(self.current_room.bounds)
        
        # Debug: Print room positions
        print("\n=== ROOM LAYOUT ===")
        for room_id, room in self.rooms.items():
            print(f"{room_id}: bounds={room.bounds}, spawn={room.spawn}")
    
    def load_chapter(self, chapter_file):
        """Load chapter - just calls load_world."""
        self.load_world(chapter_file)
    
    def get_collisions(self, rect):
        """Get collisions from current room and adjacent rooms (for cross-room grappling)."""
        collisions = []
        
        # Current room
        if self.current_room:
            collisions.extend(self.current_room.get_collisions(rect))
        
        # Adjacent rooms (for grappling across room boundaries)
        for room in self.rooms.values():
            if room != self.current_room and room.bounds.inflate(64, 64).colliderect(rect):
                collisions.extend(room.get_collisions(rect))
        
        return collisions
    
    def get_solid_collisions(self, rect):
        """Get solid collisions and platform object collisions."""
        collisions = []
        if self.current_room:
             # Solid tiles
             collisions.extend(self.current_room.get_solid_collisions(rect))
             
             # Platform objects (treated as solids for now, or handled separately in physics)
             # NOTE: Physics engine should call get_object_collisions separately for pixel perfect
        return collisions
    
    def get_object_collisions(self, rect):
        """Get object collisions from current and adjacent rooms."""
        collisions = []
        if self.current_room:
            collisions.extend(self.current_room.get_object_collisions(rect))
        
        # Check adjacent rooms
        for room in self.rooms.values():
            if room != self.current_room and room.bounds.inflate(64, 64).colliderect(rect):
                collisions.extend(room.get_object_collisions(rect))
        
        return collisions
    
    def check_room_transition(self, player_rect):
        """Check if player should transition to another room."""
        if not self.current_room:
            return None
        
        # Check if we have effectively left the current room or entered another
        # Use a slightly expanded rect to catch edge touches
        check_rect = player_rect.inflate(4, 4)
        
        for room_id, room in self.rooms.items():
            if room == self.current_room:
                continue
            
            # Use intersection check with expanded rect
            if room.bounds.colliderect(check_rect):
                # print(f"DETECTED overlap with {room_id}! Player at ({player_rect.x}, {player_rect.y})")
                clip = room.bounds.clip(check_rect)
                
                # If we overlap at all (even 1 pixel), trigger transition
                if clip.width > 0 and clip.height > 0:
                    old_bounds = self.current_room.bounds
                    new_bounds = room.bounds
                    
                    # Determine direction based on relative position
                    if new_bounds.top >= old_bounds.bottom - 16: # Room is below
                        direction = "down"
                    elif new_bounds.bottom <= old_bounds.top + 16: # Room is above
                        direction = "up"
                    elif new_bounds.left >= old_bounds.right - 16: # Room is right
                        direction = "right"
                    elif new_bounds.right <= old_bounds.left + 16: # Room is left
                        direction = "left"
                    else:
                        # Fallback geometry check
                        dx = new_bounds.centerx - old_bounds.centerx
                        dy = new_bounds.centery - old_bounds.centery
                        if abs(dx) > abs(dy):
                            direction = "right" if dx > 0 else "left"
                        else:
                            direction = "down" if dy > 0 else "up"
                    
                    print(f"  Direction: {direction}")        
                    return (room_id, direction)
        
        return None
    
    def transition_to(self, room_id, direction, player, callback=None):
        """Transition to new room - always teleport to spawn, keep momentum."""
        if room_id not in self.rooms:
            print(f"ERROR: Room {room_id} not found!")
            return
        
        new_room = self.rooms[room_id]
        print(f"TRANSITION: {self.current_room.room_id if self.current_room else '?'} -> {new_room.room_id} (direction: {direction})")
        
        # Determine forward progress (Lexicographical check: room_02 > room_01)
        # Capture this BEFORE on_complete updates self.current_room
        is_forward = False
        if self.current_room:
            is_forward = new_room.room_id > self.current_room.room_id

        def on_complete():
            self.current_room = new_room
            
            # Dampen vertical momentum for smoother entry (except Upward)
            if direction != "up":
                player.vy *= 0.2
                if abs(player.vy) < 100: player.vy = 0 # Snap small values
            
            # Hybrid Transition Logic
            # Forward (Level Up): Auto-Move to Spawn (Celeste-like)
            # Backward (Previous): Natural Movement
            
            if is_forward and new_room.spawn:
                 spawn_pos = new_room.get_spawn_world()
                 print(f"DEBUG: Forward transition to {new_room.room_id} -> Auto-Moving to spawn {spawn_pos}")
                 # Place player at natural entry point first
                 if direction == "right": player.x = new_room.bounds.left + 4
                 elif direction == "left": player.x = new_room.bounds.right - player.width - 4
                 elif direction == "down": player.y = new_room.bounds.top + 4
                 elif direction == "up": player.y = new_room.bounds.bottom - player.height - 4
                 
                 # Initiate Auto-Move to Spawn
                 if direction == "up":
                     # Bezier Arc for smooth precise landing (Visual "Nice Animation")
                     print(f"DEBUG: Up transition -> Arc to {spawn_pos}")
                     player.move_to_arc(spawn_pos, duration=0.45, lift=80) 
                 else:
                     # Horizontal/Down: Physics-based "Natural" move
                     player.move_to(spawn_pos[0])
            else:
                 # Natural transition - place player just inside new room
                 if direction == "right":
                     player.x = new_room.bounds.left + 4
                 elif direction == "left":
                     player.x = new_room.bounds.right - player.width - 4
                 elif direction == "down":
                     player.y = new_room.bounds.top + 4
                 elif direction == "up":
                     player.y = new_room.bounds.bottom - player.height - 4
            
            # Update checkpoint (so death respawns at the proper spawn point)
            if new_room.spawn:
                spawn_pos = new_room.get_spawn_world()
                self.respawn_data = {
                    'room_id': room_id,
                    'x': spawn_pos[0],
                    'y': spawn_pos[1]
                }

            else:
                self.respawn_data = {
                    'room_id': room_id,
                    'x': player.x,
                    'y': player.y,
                    'facing_right': player.facing_right
                }
            
            if callback:
                callback()
        
        if self.camera:
            self.camera.start_transition(new_room.bounds, direction, on_complete)
        else:
            self.current_room = new_room
            on_complete()
    
    
    def respawn_player(self, player):
        """Respawn player at the last saved checkpoint/entry."""
        if not self.respawn_data or self.respawn_data['room_id'] not in self.rooms:
            # Fallback to level start
            player.x, player.y = self.spawn
            player.dead = False
            # Find which room spawn is in
            for room in self.rooms.values():
                if room.contains_point(player.x, player.y):
                    self.current_room = room
                    if self.camera:
                        self.camera.set_bounds(room.bounds)
                    break
            return

        # Restore from respawn data
        room_id = self.respawn_data['room_id']
        room = self.rooms[room_id]
        
        self.current_room = room
        if self.camera:
            self.camera.set_bounds(room.bounds)
            
        player.x = self.respawn_data['x']
        player.y = self.respawn_data['y']
        player.facing_right = self.respawn_data.get('facing_right', True)
        player.vx = 0
        player.vy = 0
        player.dead = False
    
    def draw(self, surface, camera):
        """Draw all visible rooms."""
        for room in self.rooms.values():
            room.draw(surface, camera)