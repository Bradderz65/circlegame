import random
import math
import pygame

from game_config import RED, WHITE, GREEN
import game_config  # Access global GAME_INSTANCE for difficulty
from circle import Difficulty

class Obstacle:
    """Spinning wind-turbine style obstacle that damages the player cursor on contact."""

    def __init__(self, x: float, y: float, scale: float, screen_w: int, screen_h: int):
        self.x = x
        self.y = y
        self.screen_w = screen_w
        self.screen_h = screen_h

        # Movement with random speed variation (0.8x to 1.5x base speed)
        angle = random.uniform(0, 2 * math.pi)
        speed_base = 1.5 * random.uniform(0.8, 1.5)

        # Difficulty-based speed multiplier
        difficulty_speed_mult = {
            Difficulty.EASY: 1.0,
            Difficulty.MEDIUM: 1.15,
            Difficulty.HARD: 1.3,
            Difficulty.NIGHTMARE: 1.5,
        }
        try:
            current_difficulty = game_config.GAME_INSTANCE.difficulty
            speed_base *= difficulty_speed_mult.get(current_difficulty, 1.0)
        except AttributeError:
            # GAME_INSTANCE may not be initialised (e.g., during unit tests)
            pass

        self.vx = math.cos(angle) * speed_base * scale
        self.vy = math.sin(angle) * speed_base * scale

        # Visuals with size variation (80% to 140%)
        size_variation = random.uniform(0.8, 1.4)  # 80% to 140% size
        self.scale = scale * size_variation
        self.blade_len = 40 * self.scale
        self.blade_width = max(3, int(6 * self.scale))
        self.rotation = random.uniform(0, 2 * math.pi)
        self.spin_speed = 0.15  # radians per frame

        # Bounding radius for simple collision check
        self.radius = self.blade_len

    # ---------------------------------------------------------------------
    # Update & Draw
    # ---------------------------------------------------------------------
    # No more expiration - obstacles last until the round ends

    def update(self):
        """Move and rotate the obstacle. Bounce off screen edges."""
        self.x += self.vx
        self.y += self.vy
        self.rotation += self.spin_speed

        # Bounce
        if self.x - self.radius < 0 or self.x + self.radius > self.screen_w:
            self.vx *= -1
        if self.y - self.radius < 0 or self.y + self.radius > self.screen_h:
            self.vy *= -1

    def draw(self, surface: pygame.Surface):
        """Render 3 red blades with white outline."""
        # Pre-compute blade end points
        for i in range(3):  # 3-bladed turbine
            angle = self.rotation + i * (2 * math.pi / 3)
            ex = self.x + math.cos(angle) * self.blade_len
            ey = self.y + math.sin(angle) * self.blade_len
            
            # Draw white outline
            pygame.draw.line(
                surface, 
                WHITE, 
                (self.x, self.y), 
                (ex, ey), 
                self.blade_width + 2
            )
            # Draw red blade
            pygame.draw.line(
                surface, 
                RED, 
                (self.x, self.y), 
                (ex, ey), 
                self.blade_width
            )
        
        # Draw center circle
        pygame.draw.circle(
            surface, 
            RED, 
            (int(self.x), int(self.y)), 
            int(self.blade_width * 1.1)
        )


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
        
        # Check if cursor is within the pipe's x-range
        if not (self.x - 5 <= mx <= self.x + self.width + 5):
            return False
            
        # Check if cursor is outside the gap
        return not (self.gap_y - self.gap_height/2 <= my <= self.gap_y + self.gap_height/2)
        
    def draw(self, surface: pygame.Surface):
        """Draw the pipe with a gap."""
        # Draw top pipe
        pygame.draw.rect(
            surface, 
            GREEN,
            (self.x, 0, self.width, self.gap_y - self.gap_height/2)
        )
        
        # Draw bottom pipe
        pygame.draw.rect(
            surface,
            GREEN,
            (self.x, self.gap_y + self.gap_height/2, self.width, self.screen_h)
        )
        
        # Draw pipe borders for better visibility
        border_color = (0, 100, 0)  # Dark green border
        # Top pipe borders
        pygame.draw.rect(
            surface,
            border_color,
            (self.x, 0, self.width, self.gap_y - self.gap_height/2),
            2  # Border width
        )
        # Bottom pipe borders
        pygame.draw.rect(
            surface,
            border_color,
            (self.x, self.gap_y + self.gap_height/2, self.width, self.screen_h),
            2  # Border width
        )


    # ------------------------------------------------------------------
    # Collision helpers
    # ------------------------------------------------------------------
    def is_cursor_hit(self, mouse_pos) -> bool:
        mx, my = mouse_pos
        dx = mx - self.x
        # Simple circular bound check; good enough given fast movement
        return dx * dx + dy * dy <= (self.radius ** 2)
