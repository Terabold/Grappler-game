
import pygame
import os

def create_tileset():
    os.makedirs("assets/tilesets", exist_ok=True)
    
    # 3x3 grid of 32x32 tiles = 96x96
    surface = pygame.Surface((96, 96))
    surface.fill((0, 0, 0, 0)) # Transparent
    
    # Colors
    ice_color = (100, 200, 255)
    border_color = (200, 240, 255)
    inner_color = (50, 150, 200)
    
    # Draw 9-slice
    # 0,0: Top-Left
    # 1,0: Top
    # 2,0: Top-Right
    # ...
    
    for y in range(3):
        for x in range(3):
            rect = pygame.Rect(x*32, y*32, 32, 32)
            
            # Fill main background
            pygame.draw.rect(surface, ice_color, rect)
            
            # Draw borders based on position to simulate connections
            # Top row has top border
            if y == 0:
                pygame.draw.rect(surface, border_color, (x*32, y*32, 32, 4))
            # Bottom row has bottom border
            if y == 2:
                pygame.draw.rect(surface, border_color, (x*32, y*32+28, 32, 4))
            # Left col has left border
            if x == 0:
                pygame.draw.rect(surface, border_color, (x*32, y*32, 4, 32))
            # Right col has right border
            if x == 2:
                pygame.draw.rect(surface, border_color, (x*32+28, y*32, 4, 32))
            
            # Inner detail (blob)
            center_rect = pygame.Rect(x*32 + 8, y*32 + 8, 16, 16)
            pygame.draw.rect(surface, inner_color, center_rect)

    pygame.image.save(surface, "assets/tilesets/ice.png")
    print("Created assets/tilesets/ice.png")

if __name__ == "__main__":
    pygame.init()
    create_tileset()
    pygame.quit()
