import random
import math
import pygame

from game_config import GREEN, DARK_GRAY

# Create a darker green for the pipe border
DARK_GREEN = (0, 128, 0)  # Dark green

class PipeObstacle:
    """Vertical pipe obstacle that moves from left to right with a moving gap."""
    
    def __init__(self, screen_w: int, screen_h: int, scale: float):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.scale = scale
        self.width = 60 * scale
        self.x = -self.width  # Start off-screen left
        self.speed = 2.5 * scale  # Base speed
        self.gap_height = 200 * scale
        self.spawn_time = pygame.time.get_ticks()  # Track when this pipe was created
        self.gap_y = random.uniform(
            self.gap_height/2, 
            screen_h - self.gap_height/2
        )
        self.vertical_speed = random.uniform(0.5, 1.5)  # Vertical movement speed
        self.direction = 1  # 1 for down, -1 for up
        
    def update(self):
        """Move the pipe from left to right and make the gap move up and down."""
        # Move right
        self.x += self.speed
        
        # Move gap up and down
        self.gap_y += self.vertical_speed * self.direction
        
        # Change direction when hitting top or bottom
        if self.gap_y - self.gap_height/2 < 0 or self.gap_y + self.gap_height/2 > self.screen_h:
            self.direction *= -1
            
    def is_off_screen(self):
        """Check if the pipe has moved off the right side of the screen."""
        return self.x > self.screen_w
        
    def is_cursor_hit(self, mouse_pos) -> bool:
        """Check if the cursor is hitting the pipe (not in the gap)."""
        mx, my = mouse_pos
        
        # Check if cursor is within the pipe's x-range (with a small margin)
        if not (self.x - 5 <= mx <= self.x + self.width + 5):
            return False
            
        # Calculate gap boundaries
        gap_top = self.gap_y - self.gap_height/2
        gap_bottom = self.gap_y + self.gap_height/2
        
        # Check if cursor is in the gap
        is_in_gap = gap_top <= my <= gap_bottom
        
        # Return True if cursor is in the pipe but not in the gap
        return not is_in_gap
        
    def draw(self, surface: pygame.Surface):
        """Draw the pipe with a moving gap."""
        # Calculate gap boundaries
        gap_top = max(0, self.gap_y - self.gap_height/2)  # Ensure we don't go above screen
        gap_bottom = min(self.screen_h, self.gap_y + self.gap_height/2)  # Ensure we don't go below screen
        
        # Draw top pipe (from top of screen to top of gap)
        top_pipe_height = gap_top
        if top_pipe_height > 0:
            # Main fill
            pygame.draw.rect(
                surface, 
                GREEN,
                (self.x, 0, self.width, top_pipe_height)
            )
            # Right border
            pygame.draw.line(
                surface,
                DARK_GREEN,
                (self.x + self.width, 0),
                (self.x + self.width, top_pipe_height),
                3
            )
            # Left border
            pygame.draw.line(
                surface,
                DARK_GREEN,
                (self.x, 0),
                (self.x, top_pipe_height),
                3
            )
            # Bottom border (top of gap)
            pygame.draw.line(
                surface,
                DARK_GREEN,
                (self.x, top_pipe_height),
                (self.x + self.width, top_pipe_height),
                3
            )
        
        # Draw bottom pipe (from bottom of gap to bottom of screen)
        bottom_pipe_top = gap_bottom
        bottom_pipe_height = self.screen_h - bottom_pipe_top
        
        if bottom_pipe_height > 0:
            # Main fill
            pygame.draw.rect(
                surface,
                GREEN,
                (self.x, bottom_pipe_top, self.width, bottom_pipe_height)
            )
            # Right border
            pygame.draw.line(
                surface,
                DARK_GREEN,
                (self.x + self.width, bottom_pipe_top),
                (self.x + self.width, self.screen_h),
                3
            )
            # Left border
            pygame.draw.line(
                surface,
                DARK_GREEN,
                (self.x, bottom_pipe_top),
                (self.x, self.screen_h),
                3
            )
            # Top border (bottom of gap)
            pygame.draw.line(
                surface,
                DARK_GREEN,
                (self.x, bottom_pipe_top),
                (self.x + self.width, bottom_pipe_top),
                3
            )
            
        # Draw gap indicator (for debugging)
        # gap_rect = pygame.Rect(
        #     self.x, 
        #     gap_top, 
        #     self.width, 
        #     max(0, gap_bottom - gap_top)  # Ensure positive height
        # )
        # debug_surface = pygame.Surface((gap_rect.width, gap_rect.height), pygame.SRCALPHA)
        # debug_surface.fill((255, 0, 0, 64))  # Semi-transparent red
        # surface.blit(debug_surface, (gap_rect.x, gap_rect.y))
