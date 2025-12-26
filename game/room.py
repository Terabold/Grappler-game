import pygame
import json
import os

TILE_EMPTY = 0
TILE_SOLID = 1
TILE_SPIKE = 2
TILE_GRAPPLE = 3
TILE_EXIT = 4  # Green exit zone

TILE_COLORS = {
    TILE_EMPTY: None,
    TILE_SOLID: (60, 60, 70),
    TILE_SPIKE: (200, 50, 50),
    TILE_GRAPPLE: (50, 150, 200),
    TILE_EXIT: (50, 200, 80),
}


class Room:
    def __init__(self, room_id, rect):
        self.room_id = room_id
        self.bounds = rect
    
    def contains_point(self, x, y):
        return self.bounds.collidepoint(x, y)
    
    def get_bounds(self):
        return self.bounds


class Chapter:
    def __init__(self, filepath):
        self.filepath = filepath
        self.rooms = {}
        self.tiles = []
        self.collision_rects = []
        
        self.width = 0
        self.height = 0
        self.tile_size = 32
        
        self.spawn = (100, 100)
        self.current_room = None
        self.camera = None
        
        self._load(filepath)
    
    def _load(self, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
        
        self.width = data.get("width", 100)
        self.height = data.get("height", 50)
        self.tile_size = data.get("tilewidth", 32)
        
        self.tiles = [[TILE_EMPTY] * self.width for _ in range(self.height)]
        
        for layer in data.get("layers", []):
            layer_name = layer.get("name", "").lower()
            layer_type = layer.get("type", "")
            
            if layer_type == "tilelayer" and "collision" in layer_name:
                self._parse_tile_layer(layer)
            elif layer_type == "objectgroup" and "room" in layer_name:
                self._parse_rooms_layer(layer)
            elif layer_type == "objectgroup":
                self._parse_objects_layer(layer)
        
        self._build_collision_rects()
        
        if self.rooms:
            for room in self.rooms.values():
                if room.contains_point(self.spawn[0], self.spawn[1]):
                    self.current_room = room
                    break
            if not self.current_room:
                self.current_room = list(self.rooms.values())[0]
    
    def _parse_tile_layer(self, layer):
        data = layer.get("data", [])
        
        for y in range(self.height):
            for x in range(self.width):
                idx = y * self.width + x
                tile_id = data[idx] if idx < len(data) else 0
                
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
                else:
                    self.tiles[y][x] = TILE_SOLID
    
    def _parse_rooms_layer(self, layer):
        for obj in layer.get("objects", []):
            room_id = obj.get("name", f"room_{len(self.rooms)}")
            x = obj.get("x", 0)
            y = obj.get("y", 0)
            w = obj.get("width", 640)
            h = obj.get("height", 384)
            
            rect = pygame.Rect(x, y, w, h)
            self.rooms[room_id] = Room(room_id, rect)
    
    def _parse_objects_layer(self, layer):
        for obj in layer.get("objects", []):
            obj_type = obj.get("type", "").lower()
            obj_name = obj.get("name", "").lower()
            
            if "spawn" in obj_type or "spawn" in obj_name:
                self.spawn = (obj.get("x", 100), obj.get("y", 100))
    
    def _build_collision_rects(self):
        self.collision_rects = []
        
        for y in range(self.height):
            for x in range(self.width):
                if self.tiles[y][x] == TILE_SOLID:
                    rect = pygame.Rect(
                        x * self.tile_size,
                        y * self.tile_size,
                        self.tile_size,
                        self.tile_size
                    )
                    self.collision_rects.append(rect)
    
    def set_camera(self, camera):
        self.camera = camera
        if self.current_room:
            self.camera.set_bounds(self.current_room.get_bounds())
    
    def get_collisions(self, rect):
        results = []
        
        start_x = max(0, int(rect.left // self.tile_size) - 1)
        end_x = min(self.width, int(rect.right // self.tile_size) + 2)
        start_y = max(0, int(rect.top // self.tile_size) - 1)
        end_y = min(self.height, int(rect.bottom // self.tile_size) + 2)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if self.tiles[y][x] == TILE_SOLID:
                    tile_rect = pygame.Rect(
                        x * self.tile_size,
                        y * self.tile_size,
                        self.tile_size,
                        self.tile_size
                    )
                    if rect.colliderect(tile_rect):
                        results.append(tile_rect)
        
        return results
    
    def check_room_transition(self, player_rect):
        if not self.current_room:
            return None
        
        cx, cy = player_rect.centerx, player_rect.centery
        
        if self.current_room.contains_point(cx, cy):
            return None
        
        for room_id, room in self.rooms.items():
            if room == self.current_room:
                continue
            if room.contains_point(cx, cy):
                old_bounds = self.current_room.get_bounds()
                new_bounds = room.get_bounds()
                
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
        if room_id not in self.rooms:
            return
        
        new_room = self.rooms[room_id]
        
        def on_complete():
            self.current_room = new_room
            if callback:
                callback()
        
        if self.camera:
            self.camera.start_transition(new_room.get_bounds(), direction, on_complete)
        else:
            self.current_room = new_room
            if callback:
                callback()
    
    def draw(self, surface, camera):
        view_left = camera.x
        view_top = camera.y
        view_right = camera.x + camera.view_width
        view_bottom = camera.y + camera.view_height
        
        start_x = max(0, int(view_left // self.tile_size))
        end_x = min(self.width, int(view_right // self.tile_size) + 1)
        start_y = max(0, int(view_top // self.tile_size))
        end_y = min(self.height, int(view_bottom // self.tile_size) + 1)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.tiles[y][x]
                if tile == TILE_EMPTY:
                    continue
                
                world_rect = pygame.Rect(
                    x * self.tile_size,
                    y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                
                screen_rect = camera.apply_rect(world_rect)
                color = TILE_COLORS.get(tile, (100, 100, 100))
                
                if color:
                    pygame.draw.rect(surface, color, screen_rect)


class RoomManager:
    def __init__(self, rooms_dir):
        self.rooms_dir = rooms_dir
        self.chapter = None
        self.camera = None
    
    @property
    def current_room(self):
        return self.chapter.current_room if self.chapter else None
    
    @property
    def rooms(self):
        return self.chapter.rooms if self.chapter else {}
    
    def set_camera(self, camera):
        self.camera = camera
        if self.chapter:
            self.chapter.set_camera(camera)
    
    def load_world(self, filename):
        filepath = os.path.join(self.rooms_dir, filename)
        
        if "world" in filename:
            chapter_path = os.path.join(self.rooms_dir, "chapter_01.json")
            if os.path.exists(chapter_path):
                filepath = chapter_path
        
        if os.path.exists(filepath):
            self.chapter = Chapter(filepath)
            if self.camera:
                self.chapter.set_camera(self.camera)
    
    def load_chapter(self, filename):
        filepath = os.path.join(self.rooms_dir, filename)
        if os.path.exists(filepath):
            self.chapter = Chapter(filepath)
            if self.camera:
                self.chapter.set_camera(self.camera)
    
    def get_collisions(self, rect):
        if self.chapter:
            return self.chapter.get_collisions(rect)
        return []
    
    def check_room_transition(self, player_rect):
        if self.chapter:
            return self.chapter.check_room_transition(player_rect)
        return None
    
    def transition_to(self, room_id, direction, callback=None):
        if self.chapter:
            self.chapter.transition_to(room_id, direction, callback)
    
    def draw(self, surface, camera):
        if self.chapter:
            self.chapter.draw(surface, camera)