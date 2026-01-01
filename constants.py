# Game constants - all sizes relative to base resolution

# Base game resolution (internal rendering)
GAME_WIDTH = 640
GAME_HEIGHT = 384

# Scaling helper - convert design size to actual size
def scale(value):
    """Scale a value based on game height (use for sizes that should scale)"""
    return int(value * GAME_HEIGHT / 384)

def scale_x(value):
    """Scale based on width"""
    return int(value * GAME_WIDTH / 640)

# Font sizes (designed for 384 height)
FONT_TITLE = scale(36)
FONT_SUBTITLE = scale(14)
FONT_BUTTON = scale(16)
FONT_SMALL = scale(12)
FONT_TINY = scale(10)

# UI Element sizes
BUTTON_WIDTH = scale_x(120)
BUTTON_HEIGHT = scale(26)
BUTTON_SPACING = scale(36)

TAB_WIDTH = scale_x(75)
TAB_HEIGHT = scale(20)
TAB_SPACING = scale_x(8)

SLIDER_HEIGHT = scale(18)
SELECTOR_HEIGHT = scale(20)
TOGGLE_HEIGHT = scale(20)
KEYBIND_HEIGHT = scale(20)

CONTENT_WIDTH = scale_x(200)
CONTENT_SPACING = scale(34)

# Padding/margins
PADDING_SMALL = scale(4)
PADDING_MEDIUM = scale(8)
PADDING_LARGE = scale(16)

# No fixed game resolution - use screen size directly

# Colors
COLOR_BG = (20, 20, 30)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (100, 100, 100)
COLOR_DARK_GRAY = (40, 40, 40)
COLOR_LIGHT_GRAY = (150, 150, 150)
COLOR_ACCENT = (220, 60, 60)

# Tile settings
TILE_SIZE = 16


# Player settings
PLAYER_WIDTH = 28
PLAYER_HEIGHT = 28
PLAYER_SPEED = 300

# Camera settings
CAMERA_LERP_SPEED = 8
TRANSITION_SPEED = 3
