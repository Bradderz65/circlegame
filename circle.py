import pygame
import random
import math
from enum import Enum
from typing import Tuple

import game_config
from game_config import *

class CircleType(Enum):
    NORMAL = 1
    FAST = 2
    TELEPORTING = 3
    SHRINKING = 4
    SMALL = 5
    GHOST = 6
    TANK = 7
    SUPERTANK = 8
    HEXAGON = 9
    CURSOR_GRABBER = 10
    SNAKE = 11
    SHOOTER = 12

class Difficulty(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3
    NIGHTMARE = 4

class MovementPattern(Enum):
    WANDERING = 1      # Default random wandering
    ZIGZAG = 2         # Zigzag pattern movement
    ORBITAL = 3        # Circular/orbital movement around a center point
    PREDICTIVE = 4     # Tries to predict and avoid mouse movement
    BOUNCY = 5         # Bounces at sharp angles
    SERPENTINE = 6     # Snake-like wave movement
    EVASIVE = 7        # More aggressive mouse avoidance with quick direction changes

class Triangle:
    """Triangle projectile fired by shooter circles"""
    def __init__(self, x: float, y: float, vx: float, vy: float, scale_factor: float = 1.0, shooter=None, size_variation: float = 1.0):
        self.x = x
        self.y = y
        self.vx = vx  # Velocity in x direction
        self.vy = vy  # Velocity in y direction
        self.scale_factor = scale_factor
        self.size = 15 * scale_factor * size_variation  # Triangle size with variation (100-120%)
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 10000  # 10 seconds in milliseconds
        self.fade_duration = 1000  # 1 second fade out duration
        self.color = ORANGE
        self.shooter = shooter  # Reference to the shooter that created this triangle
        self.is_fading = False
        self.fade_start_time = 0
        self.alpha = 255  # Full opacity initially
        
    def update(self, screen_width: int, screen_height: int) -> bool:
        """Update triangle position and handle bouncing. Returns False if should be removed."""
        current_time = pygame.time.get_ticks()
        
        # Handle fading logic
        if not self.is_fading:
            # Check if lifetime expired - start fading instead of immediate removal
            if current_time - self.spawn_time > self.lifetime - self.fade_duration:
                self.is_fading = True
                self.fade_start_time = current_time
        else:
            # Update fade alpha
            fade_progress = (current_time - self.fade_start_time) / self.fade_duration
            if fade_progress >= 1.0:
                return False  # Completely faded out, remove triangle
            self.alpha = int(255 * (1.0 - fade_progress))  # Fade from 255 to 0
        
        # Move triangle (only if not fading or still moving while fading)
        self.x += self.vx
        self.y += self.vy
        
        # Bounce off screen edges
        if self.x <= self.size or self.x >= screen_width - self.size:
            self.vx = -self.vx
            self.x = max(self.size, min(screen_width - self.size, self.x))
            
        if self.y <= self.size or self.y >= screen_height - self.size:
            self.vy = -self.vy
            self.y = max(self.size, min(screen_height - self.size, self.y))
            
        return True  # Keep triangle
    
    def check_cursor_collision(self, cursor_x: int, cursor_y: int) -> bool:
        """Check if triangle collides with cursor position"""
        distance = math.sqrt((self.x - cursor_x) ** 2 + (self.y - cursor_y) ** 2)
        return distance < self.size
    
    def start_fade(self, fade_duration=None):
        """Start fading immediately (e.g., when hit by cursor)"""
        if not self.is_fading:
            self.is_fading = True
            self.fade_start_time = pygame.time.get_ticks()
            if fade_duration is not None:
                self.fade_duration = fade_duration
    
    def draw(self, surface):
        """Draw the triangle with fade effect"""
        # Calculate movement angle to orient triangle
        import math
        angle = math.atan2(self.vy, self.vx)  # Angle of movement
        
        # Calculate triangle points oriented towards movement direction
        # Base triangle points (pointing right by default) - adjusted to be thinner and shorter
        length = self.size * 1.2  # Reduced from 1.5 to make it shorter
        width = self.size * 0.4   # Reduced from 0.6 to make it thinner
        base_points = [
            (length, 0),        # Tip (front)
            (-length * 0.4, -width),  # Bottom left
            (-length * 0.4, width)    # Top left
        ]
        
        # Rotate points based on movement angle
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        points = []
        for px, py in base_points:
            # Rotate point around origin
            rotated_x = px * cos_a - py * sin_a
            rotated_y = px * sin_a + py * cos_a
            # Translate to triangle position
            points.append((self.x + rotated_x, self.y + rotated_y))
        
        if self.alpha < 255:
            # Create a surface with per-pixel alpha for fading
            temp_surface = pygame.Surface((self.size * 3, self.size * 3), pygame.SRCALPHA)
            
            # Adjust rotated points for the temporary surface (center them)
            temp_points = []
            center_offset = self.size * 1.5  # Center of the temp surface
            for px, py in points:
                temp_points.append((px - self.x + center_offset, py - self.y + center_offset))
            
            # Draw with alpha - using a single anti-aliased polygon for cleaner edges
            color_with_alpha = (*self.color, self.alpha)
            
            # Draw filled polygon first
            pygame.draw.polygon(temp_surface, color_with_alpha, temp_points)
            
            # Then draw a slightly smaller filled polygon with the same color to create a border effect
            if self.alpha > 0:  # Only draw border if not fully transparent
                # Calculate a slightly smaller version of the triangle for the border
                center_x = sum(p[0] for p in temp_points) / 3
                center_y = sum(p[1] for p in temp_points) / 3
                border_points = [(
                    center_x + (x - center_x) * 0.9,  # 90% of original size
                    center_y + (y - center_y) * 0.9
                ) for x, y in temp_points]
                
                # Draw the smaller triangle with the same color
                pygame.draw.polygon(temp_surface, color_with_alpha, border_points)
            
            # Blit to main surface
            surface.blit(temp_surface, (self.x - center_offset, self.y - center_offset))
        else:
            # Normal drawing when not fading
            pygame.draw.polygon(surface, self.color, points)
            pygame.draw.polygon(surface, BLACK, points, 2)  # Black outline

class Circle:
    def __init__(self, x: float, y: float, circle_type: CircleType = CircleType.NORMAL,
                 base_speed_multiplier: float = 1.0, round_speed_multiplier: float = 1.0,
                 scale_factor: float = 1.0, target_fps: int = 60, difficulty: Difficulty = Difficulty.MEDIUM,
                 size_variation: float = 1.0, round_num: int = 1, split_generation: int = 0,
                 max_split_generations: int = None):
        self.x = x
        self.y = y
        self.type = circle_type
        self.dying = False
        self.death_timer = 0
        self.death_duration = int(30 * (target_fps / 60))  # Scale death animation with FPS
        self.scale_factor = scale_factor  # For resolution scaling
        self.target_fps = target_fps  # For frame-rate independent timing
        self.difficulty = difficulty  # Store difficulty for scaling properties
        self.size_variation = size_variation  # Size variation multiplier
        self.round_num = round_num  # Current round number for special behaviors
        self.split_generation = split_generation  # Track how many times this circle has been split
        
        # Set maximum split generations for teleporting circles
        if max_split_generations is None and circle_type == CircleType.TELEPORTING:
            # Randomly assign: 60% can split once (max_gen=1), 40% can split twice (max_gen=2)
            self.max_split_generations = 1 if random.random() < 0.6 else 2
        else:
            self.max_split_generations = max_split_generations if max_split_generations is not None else 0

        # Speed multipliers
        self.base_speed_multiplier = base_speed_multiplier  # From difficulty
        self.round_speed_multiplier = round_speed_multiplier  # Increases over time

        # Base properties (at base resolution)
        self.base_radius = 30
        self.base_speed = 2  # Base speed before multipliers
        self.color = RED
        self.max_health = 1
        self.health = self.max_health
        self.points = 10

        # Movement properties
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-1, 1)

        # Scale mouse avoidance with difficulty
        difficulty_avoidance_multiplier = {
            Difficulty.EASY: 0.8,      # Less mouse avoidance
            Difficulty.MEDIUM: 1.0,
            Difficulty.HARD: 1.2,     # More mouse avoidance
            Difficulty.NIGHTMARE: 1.4
        }
        avoidance_mult = difficulty_avoidance_multiplier[self.difficulty]

        self.avoid_distance = (100 * scale_factor) * avoidance_mult  # Scale with resolution and difficulty
        self.avoid_strength = (3 * scale_factor) * avoidance_mult

        # Special properties
        self.teleport_cooldown = 0
        self.ghost_alpha = 255
        self.ghost_fade_direction = int(-2 * (target_fps / 60))  # Scale fade rate with FPS
        self.shrink_rate = (0.15 * scale_factor) * (target_fps / 60)  # Slower shrink rate to reduce eye strain

        # Tank glow properties
        self.is_glowing_tank = False
        self.is_hyper_tank = False
        self.glow_alpha = 0
        self.glow_pulse_timer = 0

        # Movement pattern assignment - randomly select for each circle
        self.movement_pattern = self._assign_movement_pattern()
        self._init_movement_pattern_properties()

        # Set type-specific properties
        self._setup_type_properties()

        # Calculate final speed and radius with all multipliers and scaling
        self.speed = self.base_speed * self.base_speed_multiplier * self.round_speed_multiplier * scale_factor
        self.radius = self.base_radius * scale_factor * self.size_variation

    def _setup_type_properties(self):
        # Difficulty scaling factors
        difficulty_health_multiplier = {
            Difficulty.EASY: 0.8,
            Difficulty.MEDIUM: 1.0,
            Difficulty.HARD: 1.2,
            Difficulty.NIGHTMARE: 1.5
        }

        difficulty_teleport_multiplier = {
            Difficulty.EASY: 0.4,      # Much less frequent teleporting
            Difficulty.MEDIUM: 0.6,    # Less frequent teleporting
            Difficulty.HARD: 0.8,     # Moderate teleporting
            Difficulty.NIGHTMARE: 1.0  # Normal teleporting (still less than before)
        }

        difficulty_points_multiplier = {
            Difficulty.EASY: 1.2,      # More points for easier difficulty
            Difficulty.MEDIUM: 1.0,
            Difficulty.HARD: 0.9,     # Slightly fewer points for harder difficulty
            Difficulty.NIGHTMARE: 0.8
        }

        health_mult = difficulty_health_multiplier[self.difficulty]
        teleport_mult = difficulty_teleport_multiplier[self.difficulty]
        points_mult = difficulty_points_multiplier[self.difficulty]
        
        # After round 20, all circles get bonus health to require multiple clicks
        post_round_20_health_bonus = 0
        if self.round_num > 20:
            # Base bonus health for all circles after round 20
            post_round_20_health_bonus = 2  # +2 health minimum
            # Additional scaling based on how far past round 20 we are
            rounds_past_20 = self.round_num - 20
            if rounds_past_20 >= 10:  # Round 30+
                post_round_20_health_bonus += 1  # +3 total
            if rounds_past_20 >= 20:  # Round 40+
                post_round_20_health_bonus += 1  # +4 total
            if rounds_past_20 >= 30:  # Round 50+
                post_round_20_health_bonus += 1  # +5 total

        if self.type == CircleType.FAST:
            self.base_speed = 2.5  # Reduced from 4
            self.color = BLUE
            self.points = int(15 * points_mult)
            # Apply size variation to fast circles (excluding small circles)
            self.base_radius = self.base_radius * self.size_variation

            # Circular movement pattern properties for mouse avoidance
            self.circle_radius = 40 * self.scale_factor  # Radius of circular movement
            self.circle_angle = random.uniform(0, 2 * math.pi)  # Start at random angle
            self.circle_speed = 0.15  # How fast to move around the circle
            self.circle_direction = random.choice([-1, 1])  # Clockwise or counterclockwise
            self.circle_center_x = self.x
            self.circle_center_y = self.y
            self.last_avoid_time = 0

        elif self.type == CircleType.TELEPORTING:
            self.color = PURPLE
            self.points = int(25 * points_mult)
            # Store teleport frequency multiplier for use in update method
            self.teleport_frequency_mult = teleport_mult
            # Apply size variation to teleporting circles
            self.base_radius = self.base_radius * self.size_variation

            # Set up proximity-based teleporting system
            # Proximity detection range
            self.proximity_teleport_range = {
                Difficulty.EASY: 120 * self.scale_factor,      # Larger range, less aggressive
                Difficulty.MEDIUM: 100 * self.scale_factor,    # Medium range
                Difficulty.HARD: 80 * self.scale_factor,       # Smaller range, more aggressive
                Difficulty.NIGHTMARE: 60 * self.scale_factor   # Very close range, very aggressive
            }.get(self.difficulty, 100 * self.scale_factor)
            
            # Direct teleport intervals when player is close (in seconds)
            proximity_teleport_interval_seconds = {
                Difficulty.EASY: 3.5,      # Every 3.5 seconds when close
                Difficulty.MEDIUM: 2.5,    # Every 2.5 seconds when close
                Difficulty.HARD: 2.0,      # Every 2 seconds when close
                Difficulty.NIGHTMARE: 1.5  # Every 1.5 seconds when close
            }.get(self.difficulty, 2.5)
            
            self.proximity_teleport_interval_frames = int(proximity_teleport_interval_seconds * self.target_fps)
            
            # Start with initial delay of 1-2 seconds
            initial_delay_seconds = random.uniform(1.0, 2.0)
            self.teleport_cooldown = int(initial_delay_seconds * self.target_fps)

        elif self.type == CircleType.SHRINKING:
            self.color = ORANGE
            self.points = int(20 * points_mult)
            # Scale shrinking rate with difficulty - much slower shrinking
            difficulty_shrink_multiplier = {
                Difficulty.EASY: 0.4,      # Very slow shrinking
                Difficulty.MEDIUM: 0.6,    # Slow shrinking
                Difficulty.HARD: 0.8,     # Moderate shrinking
                Difficulty.NIGHTMARE: 1.0  # Normal shrinking
            }
            self.shrink_multiplier = difficulty_shrink_multiplier[self.difficulty]
            # Apply size variation to shrinking circles
            self.base_radius = self.base_radius * self.size_variation

        elif self.type == CircleType.SMALL:
            self.base_radius = 15  # Small circles keep their fixed size
            self.base_speed = 2.0  # Reduced from 3
            self.color = YELLOW
            self.points = int(30 * points_mult)

        elif self.type == CircleType.GHOST:
            self.color = GRAY
            self.points = int(35 * points_mult)
            self.ghost_alpha = 128
            # Scale ghost fade rate with difficulty - much slower fade rates to reduce flickering
            difficulty_fade_multiplier = {
                Difficulty.EASY: 0.3,      # Very slow fade
                Difficulty.MEDIUM: 0.5,    # Slow fade
                Difficulty.HARD: 0.7,     # Moderate fade
                Difficulty.NIGHTMARE: 1.0  # Normal fade (still slower than before)
            }
            self.ghost_fade_multiplier = difficulty_fade_multiplier[self.difficulty]

            # Apply size variation to ghost circles
            self.base_radius = self.base_radius * self.size_variation

            # Initialize proximity-based properties
            self.base_ghost_alpha = 128
            self.base_ghost_radius = self.base_radius
            self.target_ghost_alpha = self.base_ghost_alpha
            self.target_radius_multiplier = 1.0

        elif self.type == CircleType.TANK:
            # Determine tank type based on round and difficulty
            # Hyper tanks: Spawn on any difficulty, round 14+, with 20% chance
            # Glowing tanks: Spawn after round 12, with 30% chance
            # Regular tanks: Default

            can_spawn_hyper = self.round_num >= 14
            can_spawn_glow = self.round_num >= 12

            if can_spawn_hyper and random.random() < 0.2:
                # Hyper tank - smaller, faster, brighter glow
                self.is_hyper_tank = True
                self.is_glowing_tank = True
                base_health = random.randint(5, 12)
                self.max_health = max(1, int(base_health * health_mult))
                self.health = self.max_health
                self.color = (150, 150, 255)  # Brighter blue color for hyper tanks
                self.points = int(150 * points_mult)  # More points for hyper tanks
                self.base_radius = 20 * self.size_variation  # Smaller than regular tanks
                self.base_speed = 2.5  # Faster than regular tanks
            elif can_spawn_glow and random.random() < 0.3:
                # Regular glowing tank
                self.is_glowing_tank = True
                base_health = random.randint(5, 12)
                self.max_health = max(1, int(base_health * health_mult))
                self.health = self.max_health
                self.color = (100, 100, 255)  # Blue-ish color for glowing tanks
                self.points = int(100 * points_mult)  # More points for glowing tanks
                self.base_radius = 25 * self.size_variation  # Apply size variation
                self.base_speed = 1
            else:
                # Regular tank
                base_health = 3
                self.max_health = max(1, int(base_health * health_mult))
                self.health = self.max_health
                self.color = DARK_GRAY
                self.points = int(50 * points_mult)
                self.base_radius = 25 * self.size_variation  # Apply size variation
                self.base_speed = 1

        elif self.type == CircleType.SUPERTANK:
            # Super tank - massive health, larger size, slow movement, intense glow
            self.is_glowing_tank = True
            self.is_hyper_tank = True  # Use hyper tank glow effects
            base_health = random.randint(20, 30)  # Much higher health
            self.max_health = max(1, int(base_health * health_mult))
            self.health = self.max_health
            self.color = (255, 100, 100)  # Red color to distinguish from regular tanks
            self.points = int(300 * points_mult)  # Massive points reward
            self.base_radius = 40 * self.size_variation  # Larger than regular tanks
            self.base_speed = 0.5  # Very slow movement

        elif self.type == CircleType.HEXAGON:
            # Hexagon enemy - becomes hollow when mouse gets close and follows the cursor
            self.color = (255, 100, 255)  # Magenta color for hexagon
            self.points = int(45 * points_mult)  # Good points reward
            self.base_radius = 35 * self.size_variation  # Medium-large size

            # Hexagon health scaling - make them much harder to kill
            base_health = 2  # Start with 2 health instead of 1
            if self.round_num >= 10:
                base_health = 3  # 3 health after round 10
            if self.round_num >= 15:
                base_health = 4  # 4 health in sandbox mode

            # Scale health with difficulty
            difficulty_health_bonus = {
                Difficulty.EASY: 0,        # No extra health
                Difficulty.MEDIUM: 1,      # +1 health
                Difficulty.HARD: 2,        # +2 health
                Difficulty.NIGHTMARE: 3    # +3 health
            }

            final_health = base_health + difficulty_health_bonus[self.difficulty]
            self.max_health = max(2, int(final_health * health_mult))  # Minimum 2 health
            self.health = self.max_health

            # Speed scaling with difficulty - make them faster and harder to catch
            speed_multiplier = {
                Difficulty.EASY: 2.0,      # Slower for easy
                Difficulty.MEDIUM: 2.5,    # Normal speed
                Difficulty.HARD: 3.2,     # Faster for hard
                Difficulty.NIGHTMARE: 4.0  # Much faster for nightmare
            }
            self.base_speed = speed_multiplier[self.difficulty]

            # Hexagon-specific properties with difficulty and round scaling
            self.is_filled = True  # Whether the hexagon is filled or hollow

            # Much faster hollow transitions to make them harder to click
            base_transition_speed = 0.15 * (self.target_fps / 60)  # Increased from 0.08 (almost 2x faster)

            # Scale transition speed with difficulty - harder difficulties = faster transitions
            transition_speed_multiplier = {
                Difficulty.EASY: 0.7,      # Slower transitions (easier)
                Difficulty.MEDIUM: 1.0,    # Normal speed
                Difficulty.HARD: 1.4,     # Faster transitions (harder)
                Difficulty.NIGHTMARE: 1.8  # Much faster transitions (very hard)
            }

            self.hollow_transition_speed = base_transition_speed * transition_speed_multiplier[self.difficulty]
            self.hollow_alpha = 255  # Alpha for filled state
            self.target_alpha = 255  # Target alpha value

            # Growth behavior - higher chance for growing hexagons in sandbox mode
            if self.round_num >= 15:  # Sandbox mode
                self.is_growing_hexagon = random.random() < 0.9  # Increased from 0.8 - more growing hexagons
            else:
                self.is_growing_hexagon = random.random() < 0.7  # Increased from 0.5 - more growing hexagons
            self.base_hexagon_radius = self.base_radius  # Store original radius
            self.growth_multiplier = 1.0  # Current size multiplier
            self.target_growth_multiplier = 1.0  # Target size multiplier

            # Much faster growth transitions for harder gameplay
            base_growth_speed = 0.18 * (self.target_fps / 60)  # Increased from 0.12 (50% faster)

            # Scale growth speed with difficulty
            growth_speed_multiplier = {
                Difficulty.EASY: 0.8,      # Slower growth
                Difficulty.MEDIUM: 1.0,    # Normal speed
                Difficulty.HARD: 1.3,     # Faster growth
                Difficulty.NIGHTMARE: 1.6  # Much faster growth
            }

            self.growth_transition_speed = base_growth_speed * growth_speed_multiplier[self.difficulty]

            # Expanding hexagon behavior - some hexagons will expand and become hollow
            if self.round_num >= 15:  # Sandbox mode
                self.is_expanding_hexagon = random.random() < 0.4  # 40% chance in sandbox
            else:
                self.is_expanding_hexagon = random.random() < 0.2  # 20% chance normally

            if self.is_expanding_hexagon:
                self.expansion_phase = 'expanding'  # 'expanding', 'hollowing', 'complete'
                self.expansion_progress = 0.0  # Progress through expansion (0-1)

                # Determine expansion type: fast or slow
                if random.random() < 0.6:  # 60% chance for fast expansion
                    self.expansion_type = 'fast'
                    self.expansion_speed = 0.008 + random.random() * 0.012  # Speed of expansion (0.008-0.02)
                    self.max_expansion = self.scale_factor * (1.8 + random.random() * 0.7)  # Max size (1.8x to 2.5x)
                    self.hollow_speed = 0.08 + random.random() * 0.07  # Fast hollowing (0.08-0.15)
                else:  # 40% chance for slow expansion
                    self.expansion_type = 'slow'
                    self.expansion_speed = 0.003 + random.random() * 0.005  # Slower expansion (0.003-0.008)
                    self.max_expansion = self.scale_factor * (1.4 + random.random() * 0.5)  # Smaller max size (1.4x to 1.9x)
                    self.hollow_speed = 0.02 + random.random() * 0.03  # Slower hollowing (0.02-0.05)

                # Determine outline style when hollow - some have thin edges, some thick
                self.thin_outline = random.random() < 0.5  # 50% chance for thin outline when hollow

                self.base_scale = self.scale_factor  # Store original scale
                self.hollow_timer = 0.0  # Timer for hollowing effect
                self.reset_cooldown = 0  # Cooldown before can reset to expanding phase
                self.reset_cooldown_duration = random.randint(120, 360)  # 2-6 seconds at 60fps

            # Random behavior patterns - some hexagons have unique behaviors
            # In sandbox mode (round 15), increase chance of normal behavior for better testing
            if self.round_num >= 15:  # Sandbox mode
                self.random_growth_behavior = random.choice(['normal', 'normal', 'random_pulse', 'random_size', 'random_hollow'])
            else:
                self.random_growth_behavior = random.choice(['normal', 'random_pulse', 'random_size', 'random_hollow'])
            self.behavior_timer = 0
            self.behavior_interval = random.randint(60, 180)  # 1-3 seconds at 60fps (faster changes)
            self.random_target_size = 1.0
            self.random_target_alpha = 255

            # Base thresholds that get more aggressive with difficulty and rounds
            base_proximity_threshold = 100 * self.scale_factor  # Reduced from 120 (smaller detection area)
            base_min_distance = 40 * self.scale_factor  # Reduced from 50 (smaller inner zone)

            # Difficulty scaling for proximity ranges - more conservative detection areas
            difficulty_range_multiplier = {
                Difficulty.EASY: 0.8,      # Smaller detection range (easier)
                Difficulty.MEDIUM: 0.9,    # Reduced from 0.8 - slightly smaller range
                Difficulty.HARD: 1.0,     # Normal range
                Difficulty.NIGHTMARE: 1.1  # Reduced from 1.2 - slightly larger range
            }

            # Round scaling - detection range grows more slowly with rounds
            round_range_multiplier = 1.0 + (self.round_num - 8) * 0.01  # Reduced from 0.015 - slower growth
            round_range_multiplier = max(1.0, min(1.1, round_range_multiplier))  # Cap at 10% increase (reduced from 15%)

            # Apply both multipliers
            range_multiplier = difficulty_range_multiplier[self.difficulty] * round_range_multiplier
            self.proximity_threshold = base_proximity_threshold * range_multiplier
            self.min_distance = base_min_distance * range_multiplier

            # Different transition speeds based on difficulty AND round level (much more conservative)
            difficulty_transition_multiplier = {
                Difficulty.EASY: 0.3,      # Very slow transition (much easier to click)
                Difficulty.MEDIUM: 0.6,    # Slow transition
                Difficulty.HARD: 1.0,     # Normal transition speed
                Difficulty.NIGHTMARE: 1.5  # Faster transition
            }

            # Round-based multiplier - gets more aggressive very slowly
            round_multiplier = 1.0 + (self.round_num - 8) * 0.04  # +4% speed per round after round 8 (reduced from 8%)
            round_multiplier = max(1.0, min(1.4, round_multiplier))  # Cap between 1.0x and 1.4x (reduced from 2.0x)

            # Combine both multipliers for very conservative scaling
            total_multiplier = difficulty_transition_multiplier[self.difficulty] * round_multiplier
            self.hollow_transition_speed *= total_multiplier

            # Growth transition speed scaling (for growing hexagons)
            if self.is_growing_hexagon:
                growth_difficulty_multiplier = {
                    Difficulty.EASY: 0.5,      # Slow growth (easier to react)
                    Difficulty.MEDIUM: 0.8,    # Moderate growth
                    Difficulty.HARD: 1.2,     # Faster growth (harder to react)
                    Difficulty.NIGHTMARE: 1.8  # Very fast growth
                }
                growth_total_multiplier = growth_difficulty_multiplier[self.difficulty] * round_multiplier
                self.growth_transition_speed *= growth_total_multiplier

        elif self.type == CircleType.CURSOR_GRABBER:
            # Cursor grabber - disguised as other circle types to hide
            # Pick a random color from other circle types to blend in
            disguise_colors = [
                RED,     # Normal
                BLUE,    # Fast
                PURPLE,  # Teleporting
                ORANGE,  # Shrinking
                YELLOW,  # Small
                GRAY,    # Ghost
                (64, 64, 64),  # Tank
                (255, 100, 255)  # Hexagon
            ]
            self.color = random.choice(disguise_colors)
            self.points = int(75 * points_mult)  # High points reward for difficulty
            self.base_radius = 25 * self.size_variation  # Medium size
            self.base_speed = 1.8  # Moderate speed

            # Cursor grabber specific properties
            self.is_grabbing = False
            self.grab_start_time = 0
            self.grab_duration = random.uniform(5.0, 10.0)  # 5-10 seconds
            self.grab_distance = 15 * self.scale_factor  # Distance to start grabbing
            self.grab_strength = random.uniform(0.8, 1.5)  # Pull strength multiplier
            self.original_cursor_pos = (0, 0)  # Store original cursor position
            self.grab_offset_x = 0  # Offset from cursor center
            self.grab_offset_y = 0

            # Pre-grab wind-up: delay before actually grabbing once in range
            # Gives players a short window to kill it before the grab triggers
            pre_grab_by_difficulty = {
                Difficulty.EASY: 0.7,
                Difficulty.MEDIUM: 0.5,
                Difficulty.HARD: 0.3,
                Difficulty.NIGHTMARE: 0.1,
            }
            self.pre_grab_delay = pre_grab_by_difficulty.get(self.difficulty, 0.5)
            # In Sandbox mode, always use fastest wind-up for testing (0.3s)
            if game_config.GAME_INSTANCE is not None:
                state = getattr(game_config.GAME_INSTANCE, 'state', None)
                is_sandbox = state is not None and hasattr(state, 'value') and state.value == 6  # GameState.SANDBOX
                if is_sandbox:
                    self.pre_grab_delay = 0.1
            self.pre_grab_start_time = 0

            # Waiting and stalking behavior
            self.is_stalking = False  # Whether it's actively going for cursor
            self.wait_time = random.uniform(3.0, 8.0)  # Wait 3-8 seconds before stalking
            self.wait_start_time = 0  # When waiting started
            self.stalk_decision_time = random.uniform(1.0, 4.0)  # How long to stalk before deciding
            self.stalk_start_time = 0

            # Taunt text properties
            self.show_taunt_text = False
            self.taunt_alpha = 255
            self.taunt_fade_speed = 1.5  # Slower fade for longer display

            # Movement properties when not grabbing
            self.seek_speed_multiplier = 1.5  # Faster when seeking cursor

        elif self.type == CircleType.SNAKE:
            # Snake specific properties - set these FIRST
            self.is_snake_head = True
            self.segments_killed = 0  # Track segments killed from back

            # Weighted snake length - shorter snakes more common, longer snakes progressively rarer
            length_weights = {
                3: 22,   # Most common
                4: 20,   # Very common
                5: 16,   # Common
                6: 14,   # Moderate
                7: 10,   # Less common
                8: 7,    # Rare
                9: 5,    # Very rare
                10: 3,   # Extremely rare
                11: 2,   # Ultra rare
                12: 1,   # Legendary
                13: 0.5, # Mythical
                14: 0.5  # Mythical
            }
            lengths = list(length_weights.keys())
            weights = list(length_weights.values())
            self.snake_length = random.choices(lengths, weights=weights)[0]

            # Snake properties - head of the snake
            self.color = (0, 150, 0)  # Green color for snake
            # Points based on snake length - longer snakes worth exponentially more
            if self.snake_length <= 9:
                base_points = 60 + (self.snake_length * 15)  # 105 for 3-seg, 195 for 9-seg
            else:
                # Exponential scaling for ultra-long snakes
                base_points = 195 + ((self.snake_length - 9) * 25)  # 220 for 10-seg, 345 for 14-seg
            self.points = int(base_points * points_mult)
            self.base_radius = 20 * self.size_variation  # Smaller than normal
            self.base_speed = 2.2  # Faster speed
            self.segments = []  # Will store segment positions
            self.segment_spacing = 35 * self.scale_factor  # Distance between segments
            self.direction_x = random.uniform(-1, 1)
            self.direction_y = random.uniform(-1, 1)
            # Normalize direction
            dir_length = math.sqrt(self.direction_x**2 + self.direction_y**2)
            if dir_length > 0:
                self.direction_x /= dir_length
                self.direction_y /= dir_length

            # Random speed boost system
            self.speed_boost_timer = 0
            self.speed_boost_cooldown_timer = 0
            self.speed_boost_duration = 0  # Will be set randomly
            self.speed_boost_cooldown_duration = 0  # Will be set randomly
            self.base_detection_range = 180 * self.scale_factor  # Larger detection range
            self.panic_detection_range = 80 * self.scale_factor  # Close range for avoidance only
            
            # Start ready for first proximity trigger (no initial cooldown)
            # Boost system will activate when player gets close

            # Unpredictable movement properties - balanced for segment following
            self.turn_timer = 0
            self.turn_interval = random.randint(30, 90)  # More frequent direction changes
            self.circle_mode = False
            self.circle_timer = 0
            self.circle_duration = 0
            self.circle_direction = 1  # 1 for clockwise, -1 for counterclockwise
            self.circle_start_angle = 0
            self.erratic_mode_timer = 0
            self.zigzag_mode = False
            self.zigzag_timer = 0
            self.zigzag_direction = 1
            self.direction_change_smoothing = 0.7  # Slightly faster direction changes

            # Rainbow snake properties (rare variant)
            self.is_rainbow = random.random() < 0.05  # 5% chance for rainbow snake
            if self.is_rainbow:
                self.color = (255, 100, 255)  # Bright magenta for rainbow head
                self.rainbow_timer = 0
                self.base_speed *= 1.1  # 10% speed boost for rainbow snakes
                # Rainbow snakes are worth significantly more points
                if self.snake_length <= 9:
                    base_points = 80 + (self.snake_length * 20)  # 140 for 3-seg, 260 for 9-seg
                else:
                    # Even higher scaling for ultra-long rainbow snakes
                    base_points = 260 + ((self.snake_length - 9) * 35)  # 295 for 10-seg, 470 for 14-seg
                self.points = int(base_points * points_mult)

            # Initialize segment positions trailing behind head
            for i in range(self.snake_length):
                seg_x = self.x - (i + 1) * self.segment_spacing * self.direction_x
                seg_y = self.y - (i + 1) * self.segment_spacing * self.direction_y
                self.segments.append([seg_x, seg_y])

        elif self.type == CircleType.SHOOTER:
            self.color = DARK_BLUE
            self.points = int(120 * points_mult)  # Very high value target (3x original)
            self.base_radius = 35 * self.size_variation  # Medium-large size
            self.max_health = int(10 * health_mult)  # Strong health - requires 10+ clicks
            self.health = self.max_health
            self.base_speed = 0.5  # Very slow movement
            
            # Shooter-specific properties
            self.detection_range = 150 * self.scale_factor  # Range to detect player cursor
            self.last_shot_time = 0
            self.shot_cooldown = 2000  # 2 seconds between shots
            self.has_fired = False  # Track if it has fired at player yet
            self.active_triangles = []  # Track triangles fired by this shooter
            
            # Spin animation properties
            self.spin_angle = 0  # Current rotation angle
            self.spin_speed = 0  # Current spin speed (radians per frame)
            self.max_spin_speed = 0.2  # Maximum spin speed (radians per frame)
            
            # Base spin-up time (ms) - will be adjusted by difficulty
            self.base_spin_up_time = 300
            # Difficulty-based spin-up time multipliers (lower = faster spin-up)
            self.difficulty_spin_mult = {
                Difficulty.EASY: 1.0,     # 300ms
                Difficulty.MEDIUM: 0.7,   # 210ms
                Difficulty.HARD: 0.5,     # 150ms
                Difficulty.NIGHTMARE: 0.3  # 90ms
            }
            self.spin_up_time = self.base_spin_up_time  # Will be set in update based on difficulty
            self.spin_start_time = 0  # When spinning started
            self.is_spinning = False  # Whether currently spinning up
            
            # Invisibility and teleportation properties
            self.is_invisible = False
            self.invisibility_start_time = 0
            self.invisibility_duration = 0  # Will be set to random 2-4 seconds when going invisible
            self.needs_teleport = False  # Flag to trigger teleportation when becoming visible
            
            # Delay before going invisible after shooting
            self.shot_fired_time = 0  # When the shot was fired
            self.visibility_after_shot = 0  # How long to stay visible after shooting (difficulty-based)
            
        else:  # NORMAL type
            self.points = int(10 * points_mult)
            # Apply size variation to normal circles
            self.base_radius = self.base_radius * self.size_variation
        
        # Apply post-round-20 health bonus to ALL circle types (except split circles and cursor grabbers)
        if post_round_20_health_bonus > 0 and self.split_generation == 0 and self.type != CircleType.CURSOR_GRABBER:
            self.max_health += post_round_20_health_bonus
            self.health = self.max_health
            # Also increase points to compensate for increased difficulty
            points_bonus_multiplier = 1.0 + (post_round_20_health_bonus * 0.3)  # 30% more points per bonus health
            self.points = int(self.points * points_bonus_multiplier)

    def _assign_movement_pattern(self) -> MovementPattern:
        """Randomly assign a movement pattern to the circle based on round and difficulty"""
        # Weight different patterns based on round progression
        if self.round_num < 3:
            # Early rounds: mostly wandering with some zigzag
            patterns = [MovementPattern.WANDERING] * 3 + [MovementPattern.ZIGZAG]
        elif self.round_num < 6:
            # Mid-early rounds: add orbital and bouncy
            patterns = [MovementPattern.WANDERING] * 2 + [MovementPattern.ZIGZAG,
                       MovementPattern.ORBITAL, MovementPattern.BOUNCY]
        elif self.round_num < 10:
            # Mid rounds: add serpentine
            patterns = [MovementPattern.WANDERING, MovementPattern.ZIGZAG,
                       MovementPattern.ORBITAL, MovementPattern.BOUNCY, MovementPattern.SERPENTINE]
        else:
            # Late rounds: all patterns including evasive
            patterns = list(MovementPattern)
            # Higher chance for more challenging patterns in later rounds
            if self.round_num >= 12:
                patterns.extend([MovementPattern.EVASIVE, MovementPattern.PREDICTIVE] * 2)

        return random.choice(patterns)

    def _init_movement_pattern_properties(self):
        """Initialize properties specific to the assigned movement pattern"""
        # Common wandering properties for all patterns
        self.wander_angle = random.uniform(0, 2 * math.pi)
        self.wander_timer = 0
        self.wander_duration = random.randint(60, 180)  # 1-3 seconds at 60fps

        if self.movement_pattern == MovementPattern.WANDERING:
            # Default wandering - uses common properties above
            pass

        elif self.movement_pattern == MovementPattern.ZIGZAG:
            self.zigzag_timer = 0
            self.zigzag_interval = random.randint(30, 90)  # Change direction every 0.5-1.5 seconds
            self.zigzag_direction_x = random.choice([-1, 1])
            self.zigzag_direction_y = random.choice([-1, 1])
            self.zigzag_speed_multiplier = random.uniform(0.8, 1.4)
            self.zigzag_angle = math.atan2(self.zigzag_direction_y, self.zigzag_direction_x)
            self.zigzag_length = random.randint(20, 60)  # Length of each zigzag segment

        elif self.movement_pattern == MovementPattern.ORBITAL:
            self.orbital_center_x = self.x
            self.orbital_center_y = self.y
            self.orbital_radius = random.uniform(40, 120) * self.scale_factor
            self.orbital_angle = random.uniform(0, 2 * math.pi)
            self.orbital_speed = random.uniform(0.02, 0.08) * random.choice([-1, 1])
            self.orbital_direction = random.choice([-1, 1])
            self.orbital_eccentricity = random.uniform(0.7, 1.3)  # For elliptical orbits

        elif self.movement_pattern == MovementPattern.PREDICTIVE:
            self.predicted_mouse_x = 0
            self.predicted_mouse_y = 0
            self.mouse_history = []  # Store recent mouse positions
            self.prediction_strength = random.uniform(0.3, 0.8)
            self.last_avoid_time = 0
            self.prediction_frames = 10  # How many frames ahead to predict

        elif self.movement_pattern == MovementPattern.BOUNCY:
            self.bounce_strength = random.uniform(0.7, 1.3)
            self.bounce_damping = random.uniform(0.85, 0.95)
            self.bounce_threshold = random.uniform(0.5, 1.0)
            self.bounce_angle = random.uniform(0, 2 * math.pi)
            self.bounce_timer = 0

        elif self.movement_pattern == MovementPattern.SERPENTINE:
            self.serpentine_amplitude = random.uniform(20, 60) * self.scale_factor
            self.serpentine_frequency = random.uniform(0.02, 0.06)
            self.serpentine_phase = 0
            self.serpentine_base_direction_x = random.uniform(-1, 1)
            self.serpentine_base_direction_y = random.uniform(-1, 1)
            # Normalize base direction
            length = math.sqrt(self.serpentine_base_direction_x**2 + self.serpentine_base_direction_y**2)
            if length > 0:
                self.serpentine_base_direction_x /= length
                self.serpentine_base_direction_y /= length

        elif self.movement_pattern == MovementPattern.EVASIVE:
            self.evasive_sensitivity = random.uniform(1.2, 2.0)
            self.evasive_reaction_time = random.randint(5, 15)  # Frames to react
            self.evasive_last_mouse_x = 0
            self.evasive_last_mouse_y = 0
            self.evasive_panic_threshold = 60 * self.scale_factor  # Distance to panic
            self.evasive_timer = 0

        # Initialize ambient humming sound for tanks
        self.hum_channel = None
        self.hum_sound = None
        if self.type == CircleType.TANK:
            self.hum_sound = TANK_HUM_SOUND
        elif self.type == CircleType.SUPERTANK:
            self.hum_sound = SUPERTANK_HUM_SOUND

        # Start playing hum sound if it's a tank
        if self.hum_sound:
            try:
                self.hum_channel = pygame.mixer.find_channel()
                if self.hum_channel:
                    # Apply volume control for tank sounds
                    if game_config.GAME_INSTANCE:
                        volume = game_config.GAME_INSTANCE.master_volume * game_config.GAME_INSTANCE.tank_volume
                        self.hum_sound.set_volume(volume)
                    self.hum_channel.play(self.hum_sound, loops=-1)  # Loop indefinitely
            except:
                self.hum_channel = None

        # Supertank regeneration properties
        if self.type == CircleType.SUPERTANK:
            self.last_clicked_time = 0
            self.regen_cooldown = 3.0  # 3 seconds
            self.regen_active = False
            self.regen_timer = 0
            self.regen_rate = 0.5  # Heal 1 health every 0.5 seconds
            
            # Self-destruct mechanism
            self.self_destruct_timer = 0
            # Duration varies by difficulty: Easy=7s, Medium=6s, Hard=5s, Nightmare=4s
            difficulty_duration = {
                Difficulty.EASY: 6.0,      # 7 seconds
                Difficulty.MEDIUM: 5.0,    # 6 seconds
                Difficulty.HARD: 4.0,      # 5 seconds
                Difficulty.NIGHTMARE: 3.0  # 4 seconds
            }
            duration = difficulty_duration.get(self.difficulty, 6.0)  # Default to 6s if unknown
            self.self_destruct_duration = duration * self.target_fps  # Convert to frames
            self.self_destruct_active = False
            self.last_beep_time = 0
            self.beep_interval = 60  # Start with 1 second between beeps (60 frames at 60fps)

    def cleanup_sounds(self):
        """Clean up any playing sounds when circle is removed"""
        if self.hum_channel:
            try:
                self.hum_channel.stop()
            except:
                pass
            self.hum_channel = None

    def take_damage(self) -> bool:
        """Returns True if circle should be removed"""
        self.health -= 1
        
        # Trigger self-destruct for supertank when it reaches half health
        if (self.type == CircleType.SUPERTANK and self.health <= self.max_health // 2 and 
            hasattr(self, 'self_destruct_active') and not self.self_destruct_active):
            self.start_self_destruct()
        
        if self.health <= 0:
            self.dying = True
            # Stop humming sound for tanks when they die
            if self.hum_channel:
                try:
                    self.hum_channel.stop()
                except:
                    pass
                self.hum_channel = None

            # If this is a teleporting (purple) circle, split chance varies by difficulty and round.
            # In Sandbox mode (state value 6) we guarantee a split so testers can always observe it.
            if self.type == CircleType.TELEPORTING and game_config.GAME_INSTANCE is not None:
                # Avoid circular import by checking numeric value (GameState.SANDBOX == 6)
                state = getattr(game_config.GAME_INSTANCE, 'state', None)
                is_sandbox = state is not None and hasattr(state, 'value') and state.value == 6
                
                if is_sandbox:
                    split_chance = 1.0  # 100% in sandbox mode for testing
                else:
                    # Progressive split chance system:
                    # Base: 20% for single-split circles, 25% for double-split circles
                    # Easy: +0.5% every 2 rounds
                    # Medium: +0.5% every round
                    # Hard: +1% every round
                    # Nightmare: +2% every round
                    base_chance = 0.25 if self.max_split_generations == 2 else 0.20
                    
                    # Calculate bonus based on difficulty and round
                    if self.difficulty == Difficulty.EASY:
                        bonus = (self.round_num // 2) * 0.005  # 0.5% every 2 rounds
                    elif self.difficulty == Difficulty.MEDIUM:
                        bonus = (self.round_num - 1) * 0.005  # 0.5% every round (round 1 = no bonus)
                    elif self.difficulty == Difficulty.HARD:
                        bonus = (self.round_num - 1) * 0.01   # 1% every round
                    elif self.difficulty == Difficulty.NIGHTMARE:
                        bonus = (self.round_num - 1) * 0.02   # 2% every round
                    else:
                        bonus = 0
                    
                    split_chance = min(1.0, base_chance + bonus)  # Cap at 100%
                
                # Prevent infinite splitting - use individual circle's max split limit
                if self.split_generation >= self.max_split_generations:
                    split_chance = 0  # No more splitting allowed
                
                # Prevent splitting if resulting circles would be too small
                # Calculate what the new size would be after splitting
                new_size_variation = max(0.4, self.size_variation * 0.6)
                new_radius = self.base_radius * new_size_variation * self.scale_factor
                min_viable_radius = 8 * self.scale_factor  # Minimum viable circle size
                
                if new_radius < min_viable_radius:
                    split_chance = 0  # Don't split if resulting circles would be too small
                
                if random.random() < split_chance:
                    for _ in range(2):
                        # Slight offset so they don't overlap perfectly
                        offset_angle = random.uniform(0, 2 * math.pi)
                        offset_dist = self.radius * 0.5
                        nx = self.x + math.cos(offset_angle) * offset_dist
                        ny = self.y + math.sin(offset_angle) * offset_dist

                        new_circle = Circle(
                            nx,
                            ny,
                            circle_type=CircleType.TELEPORTING,
                            base_speed_multiplier=self.base_speed_multiplier,
                            round_speed_multiplier=self.round_speed_multiplier,
                            scale_factor=self.scale_factor,
                            target_fps=self.target_fps,
                            difficulty=self.difficulty,
                            size_variation=max(0.4, self.size_variation * 0.6),  # smaller size
                            round_num=self.round_num,
                            split_generation=self.split_generation + 1,  # Increment generation
                            max_split_generations=self.max_split_generations  # Inherit parent's limit
                        )
                        game_config.GAME_INSTANCE.circles.append(new_circle)
                    # Each new circle counts toward remaining circles this round
                    if hasattr(game_config.GAME_INSTANCE, 'circles_to_spawn'):
                        game_config.GAME_INSTANCE.circles_to_spawn += 1

            # Play appropriate death sound based on circle type
            if self.type == CircleType.SUPERTANK:
                play_sound(SUPERTANK_DEATH_SOUND, 'tank')
            elif self.type == CircleType.TANK:
                play_sound(TANK_DEATH_SOUND, 'tank')
            else:
                play_sound(DEATH_SOUND, 'effects')
            return True
        else:
            # Play appropriate hit sound based on circle type
            if self.type == CircleType.SUPERTANK:
                play_sound(SUPERTANK_HIT_SOUND, 'tank')
            elif self.type == CircleType.TANK:
                play_sound(TANK_HIT_SOUND, 'tank')
            else:
                play_sound(COLLISION_SOUND, 'effects')
        return False

    def is_clicked(self, pos: Tuple[int, int]) -> bool:
        mx, my = pos

        # Cursor grabbers are invincible while grabbing
        if self.type == CircleType.CURSOR_GRABBER and self.is_grabbing:
            return False

        if self.type == CircleType.HEXAGON:
            # Hexagon hit detection - different logic for filled vs hollow
            # Calculate hexagon vertices (match the drawing code rotation exactly)
            vertices = []
            # Use the exact same radius calculation as drawing code
            draw_radius = max(8, int(self.radius))  # Match the drawing code minimum radius

            for i in range(6):
                # Exact same angle calculation as drawing code
                angle = (i * math.pi / 3) + (math.pi / 2)  # 60 degrees apart, rotated 90 degrees
                x = self.x + draw_radius * math.cos(angle)
                y = self.y + draw_radius * math.sin(angle)
                vertices.append((x, y))

            if self.is_filled:
                # When filled, use improved point-in-polygon test (ray casting algorithm)
                def point_in_polygon(x, y, vertices):
                    n = len(vertices)
                    inside = False

                    j = n - 1  # Last vertex
                    for i in range(n):
                        xi, yi = vertices[i]
                        xj, yj = vertices[j]
                        
                        # Check if point is on a horizontal ray from the test point
                        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                            inside = not inside
                        j = i

                    return inside

                return point_in_polygon(mx, my, vertices)
            else:
                # When hollow, only check if click is on the outline
                def point_to_line_distance(px, py, x1, y1, x2, y2):
                    """Calculate distance from point to line segment with improved precision"""
                    # Vector from line start to end
                    dx = x2 - x1
                    dy = y2 - y1

                    # If line is a point (very small line)
                    line_length_squared = dx * dx + dy * dy
                    if line_length_squared < 0.001:  # Very small threshold
                        return math.sqrt((px - x1) * (px - x1) + (py - y1) * (py - y1))

                    # Parameter t for projection onto line
                    t = ((px - x1) * dx + (py - y1) * dy) / line_length_squared
                    t = max(0.0, min(1.0, t))  # Clamp to line segment

                    # Closest point on line segment
                    closest_x = x1 + t * dx
                    closest_y = y1 + t * dy

                    # Return distance squared to avoid unnecessary sqrt
                    dist_squared = (px - closest_x) * (px - closest_x) + (py - closest_y) * (py - closest_y)
                    return math.sqrt(dist_squared)

                # Match the exact outline thickness calculation from drawing code
                if hasattr(self, 'is_expanding_hexagon') and self.is_expanding_hexagon and hasattr(self, 'thin_outline'):
                    if self.thin_outline:
                        outline_thickness = max(1, int(2 * self.scale_factor))
                    else:
                        outline_thickness = max(3, int(5 * self.scale_factor))
                else:
                    outline_thickness = max(3, int(5 * self.scale_factor))
                
                # Add a small buffer to make clicking slightly more forgiving
                # But still maintain challenge based on difficulty
                difficulty_buffer = {
                    Difficulty.EASY: 2.0,      # More forgiving
                    Difficulty.MEDIUM: 1.5,    # Slightly forgiving
                    Difficulty.HARD: 1.0,      # Exact thickness
                    Difficulty.NIGHTMARE: 0.8  # Slightly harder
                }
                
                # Apply difficulty buffer to outline thickness
                outline_thickness = max(1, outline_thickness * difficulty_buffer[self.difficulty])

                # Check each edge of the hexagon
                for i in range(6):
                    x1, y1 = vertices[i]
                    x2, y2 = vertices[(i + 1) % 6]

                    distance = point_to_line_distance(mx, my, x1, y1, x2, y2)
                    if distance <= outline_thickness:
                        return True

                return False
        else:
            # Standard circular hit detection for other types
            # Use floating-point precision for accurate detection
            dx = self.x - mx
            dy = self.y - my
            distance_squared = dx * dx + dy * dy
            radius_squared = self.radius * self.radius

            # For ghost circles, only allow clicks when they're visible enough
            if self.type == CircleType.GHOST:
                # Don't allow clicks on nearly invisible ghost circles
                # Use 25 as threshold since min_alpha can go down to 30 during proximity
                if hasattr(self, 'ghost_alpha') and self.ghost_alpha < 25:
                    return False
                # Use slightly smaller hit radius for ghost circles to match visual appearance
                effective_radius = self.radius * 0.9
                return distance_squared <= (effective_radius * effective_radius)

            # For shrinking circles, ensure hit detection matches current visual size
            if self.type == CircleType.SHRINKING:
                # Use the current visual radius which matches what's drawn
                visual_radius = max(5, self.radius)  # Match minimum size from shrinking logic
                return distance_squared <= (visual_radius * visual_radius)

            # For small circles, ensure precise hit detection
            if self.type == CircleType.SMALL:
                # Small circles should have precise hit detection matching their smaller size
                return distance_squared <= radius_squared

            # Snake click detection - must kill ALL segments from back to front, then head
            if self.type == CircleType.SNAKE:
                # Check if clicking on a segment
                for i in range(len(self.segments)):
                    # Skip segments that have already been killed
                    if i >= len(self.segments) - self.segments_killed:
                        continue

                    seg_x, seg_y = self.segments[i]
                    dx_seg = seg_x - mx
                    dy_seg = seg_y - my
                    distance_squared_seg = dx_seg * dx_seg + dy_seg * dy_seg

                    # Accurate hit detection matching visual size
                    seg_radius = max(int(self.radius * 0.8), 8)

                    if distance_squared_seg <= (seg_radius * seg_radius):
                        # Can only kill the next expected segment (back to front order)
                        expected_segment_index = len(self.segments) - 1 - self.segments_killed
                        if i == expected_segment_index:
                            # Correct next segment clicked - kill it
                            self.segments_killed += 1
                            # Return False to indicate segment killed but snake not dead yet
                            # Only return True when the entire snake (including head) is killed
                            return False
                        else:
                            # Wrong segment clicked - no effect
                            return False

                # Check if clicking on head (can only kill when ALL segments are gone)
                if self.segments_killed >= len(self.segments):
                    # All segments killed, can now kill the head to finish the snake
                    if distance_squared <= radius_squared:
                        return True  # Snake is completely killed
                else:
                    # Head can't be killed until all segments are destroyed
                    if distance_squared <= radius_squared:
                        return False  # Clicked head but segments remain

                return False

            return distance_squared <= radius_squared

    def start_self_destruct(self):
        """Start the self-destruct sequence for supertank"""
        if self.type == CircleType.SUPERTANK and not self.self_destruct_active:
            self.self_destruct_active = True
            self.self_destruct_timer = 0
            self.last_beep_time = 0
            self.beep_interval = 60  # Reset to 1 second

    def _start_boost_cooldown(self):
        """Start a cooldown period before next boost"""
        # Random cooldown between 2-6 seconds
        cooldown_seconds = random.uniform(2.0, 6.0)
        self.speed_boost_cooldown_duration = int(cooldown_seconds * self.target_fps)
        self.speed_boost_cooldown_timer = self.speed_boost_cooldown_duration
        self.speed_boost_timer = 0
        self.speed_boost_duration = 0
    
    def _start_boost_period(self):
        """Start a boost period with random duration"""
        # Random boost duration between 1-3 seconds as requested
        boost_seconds = random.uniform(1.0, 3.0)
        self.speed_boost_duration = int(boost_seconds * self.target_fps)
        self.speed_boost_timer = self.speed_boost_duration
        self.speed_boost_cooldown_timer = 0
        self.speed_boost_cooldown_duration = 0
    
    def update_boost_system(self, min_distance_to_mouse):
        """Update the proximity-triggered boost system with cooldown - call this every frame for snake circles"""
        if self.type != CircleType.SNAKE:
            return
            
        # Handle active boost period
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= 1
            if self.speed_boost_timer <= 0:
                # Boost finished, start cooldown
                self._start_boost_cooldown()
        
        # Handle cooldown period
        elif self.speed_boost_cooldown_timer > 0:
            self.speed_boost_cooldown_timer -= 1
            # During cooldown, cannot trigger new boost even if player gets close
        
        # Ready for new boost - check proximity
        elif min_distance_to_mouse < self.panic_detection_range:
            # Player is close and no cooldown active - trigger boost!
            self._start_boost_period()

    def update(self, mouse_pos, screen_width, screen_height):
        """Update circle - delegate to behavior module"""
        from circle_behavior import update_circle
        return update_circle(self, mouse_pos, screen_width, screen_height)

    def draw(self, surface):
        """Draw circle - delegate to behavior module"""
        from circle_behavior import draw_circle
        draw_circle(self, surface)
