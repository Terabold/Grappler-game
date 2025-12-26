import json
import os
import pygame

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

DEFAULT_SETTINGS = {
    "video": {
        "resolution": [1280, 720],
        "fullscreen": False,
        "fps_cap": 60,
        "vsync": True
    },
    "audio": {
        "master": 0.8,
        "sfx": 0.8,
        "music": 0.5
    },
    "controls": {
        "left": pygame.K_a,
        "right": pygame.K_d,
        "up": pygame.K_w,
        "down": pygame.K_s,
        "jump": pygame.K_SPACE,
        "grapple": pygame.K_LSHIFT,
        "pause": pygame.K_ESCAPE
    }
}

BASE_RESOLUTION_OPTIONS = [
    (640, 360),
    (854, 480),
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160)
]

def get_available_resolutions():
    """Filter resolutions to only those that fit the monitor"""
    try:
        if not pygame.display.get_init():
            pygame.display.init()
        
        info = pygame.display.Info()
        max_w, max_h = info.current_w, info.current_h
        
        # Sanity check - if we get weird values, return all options
        if max_w < 800 or max_h < 600:
            return BASE_RESOLUTION_OPTIONS
        
        available = [res for res in BASE_RESOLUTION_OPTIONS if res[0] <= max_w and res[1] <= max_h]
        
        # Always have at least one option
        if not available:
            available = [(1280, 720)]
        
        return available
    except:
        return BASE_RESOLUTION_OPTIONS

# Cache
_cached_resolutions = None

def get_resolution_options():
    global _cached_resolutions
    if _cached_resolutions is None:
        _cached_resolutions = get_available_resolutions()
    return _cached_resolutions

FPS_OPTIONS = [30, 60, 120, 144, 240, 0]  # 0 = unlimited

class SettingsManager:
    def __init__(self):
        self.settings = self.load()
        self._validate_resolution()
    
    def _validate_resolution(self):
        """Ensure saved resolution doesn't exceed monitor size"""
        options = get_resolution_options()
        current = tuple(self.settings["video"]["resolution"])
        
        if current not in options:
            # Pick the highest available resolution
            best = options[-1]
            self.settings["video"]["resolution"] = list(best)
            self.save()
    
    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new settings
                    return self._merge_defaults(loaded)
            except (json.JSONDecodeError, IOError):
                return DEFAULT_SETTINGS.copy()
        return DEFAULT_SETTINGS.copy()
    
    def _merge_defaults(self, loaded):
        """Merge loaded settings with defaults to fill missing keys"""
        result = DEFAULT_SETTINGS.copy()
        for category, values in loaded.items():
            if category in result:
                if isinstance(values, dict):
                    result[category].update(values)
                else:
                    result[category] = values
        return result
    
    def save(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=2)
        except IOError as e:
            print(f"Failed to save settings: {e}")
    
    def get(self, category, key=None):
        if key is None:
            return self.settings.get(category, {})
        return self.settings.get(category, {}).get(key)
    
    def set(self, category, key, value):
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
        self.save()
    
    def get_key_name(self, key_code):
        """Convert pygame key code to readable name"""
        return pygame.key.name(key_code).upper()
    
    def get_resolution_index(self):
        current = tuple(self.settings["video"]["resolution"])
        options = get_resolution_options()
        if current in options:
            return options.index(current)
        return 0
    
    def get_fps_index(self):
        current = self.settings["video"]["fps_cap"]
        if current in FPS_OPTIONS:
            return FPS_OPTIONS.index(current)
        return 1  # Default to 60
