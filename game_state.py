import pygame
import random
import math
import json
import os
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

import game_config
from game_config import (
    GAME_OVER_SOUND, COIN_SOUND, HIT_SOUND, EXPLOSION_SOUND, SPAWN_SOUND,
    COLLISION_SOUND, DEATH_SOUND, TANK_HIT_SOUND, SUPERTANK_HIT_SOUND,
    TANK_DEATH_SOUND, SUPERTANK_DEATH_SOUND, TANK_HUM_SOUND, SUPERTANK_HUM_SOUND, BEEP_SOUND,
    play_sound, BASE_WIDTH, BASE_HEIGHT, DEFAULT_WIDTH, 
    DEFAULT_HEIGHT, BLACK, WHITE, RED, GREEN, BLUE, YELLOW, PURPLE, ORANGE, 
    PINK, GRAY, LIGHT_GRAY, DARK_GRAY, DARK_BLUE, DEEP_PURPLE, NAVY_BLUE, MIDNIGHT_BLUE
)
from circle import Circle, CircleType, Difficulty
from obstacle import Obstacle
from pipe_obstacle import PipeObstacle
from circle_behavior import update_circle, draw_circle

class GameState(Enum):
    MAIN_MENU = 1
    DIFFICULTY_SELECT = 2
    TIME_SELECT = 3
    PLAYING = 4
    GAME_OVER = 5
    SANDBOX = 6

class GameMode(Enum):
    ENDLESS = 1
    TIMED = 2

@dataclass
class HighScore:
    name: str
    score: int
    round_reached: int
    difficulty: str
    click_radius_helper: bool = False  # Whether click radius helper was used
    pipes_disabled: bool = False  # Whether pipes were disabled
    spinners_disabled: bool = False  # Whether spinners were disabled

class Game:
    def __init__(self):
        # Set the global GAME_INSTANCE in game_config so all modules can access it
        game_config.GAME_INSTANCE = self
        
        # Track which rounds have had obstacles spawned and whether we've spawned them this round
        self.rounds_with_obstacles = set()
        self.obstacles_spawned_this_round = False  # Track if we've spawned obstacles this round
        self.obstacles_for_this_round = 0  # Predetermined number of obstacles for current round
        
        # Track pipe obstacles separately
        self.pipe_obstacles = []
        self.pipe_obstacles_this_round = 0  # Number of pipe obstacles spawned this round
        self.last_pipe_spawn_time = 0       # When the last pipe obstacle was spawned
        self.pending_pipe_spawn = False     # Whether we should try to spawn a pipe obstacle
        self.force_quick_pipes = False     # Toggle to force quick pipe spawning always
        self.quick_burst_remaining = 0     # Number of pipes remaining in current quick burst
        self.in_quick_burst = False        # Whether we're currently in a quick burst mode
        # Pipe warning flash control
        self.pipe_flash_armed = False      # Whether a flash is armed for the next spawn
        self.pipe_flash_time = 0           # Time (ms) when the flash should trigger

        # Get monitor resolution for fullscreen
        info = pygame.display.Info()
        self.monitor_width = info.current_w
        self.monitor_height = info.current_h

        # Start in windowed mode
        self.screen_width = DEFAULT_WIDTH
        self.screen_height = DEFAULT_HEIGHT
        self.fullscreen = False

        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Circle Clicker Game - Press F11 for Fullscreen")
        self.clock = pygame.time.Clock()

        # Try to detect monitor refresh rate and set appropriate FPS
        self.target_fps = self._get_optimal_fps()

        # Calculate scaling factor based on current resolution
        self.scale_factor = min(self.screen_width / BASE_WIDTH, self.screen_height / BASE_HEIGHT)

        # Scaled fonts
        self.font = pygame.font.Font(None, int(36 * self.scale_factor))
        self.big_font = pygame.font.Font(None, int(72 * self.scale_factor))
        self.small_font = pygame.font.Font(None, int(24 * self.scale_factor))

        self.state = GameState.MAIN_MENU
        self.difficulty = Difficulty.MEDIUM
        self.game_mode = GameMode.ENDLESS
        self.time_limit = 60  # seconds
        self.time_remaining = 0
        self.game_start_time = 0
        self.circles: List[Circle] = []
        # Triangle projectiles from shooter circles
        self.triangles = []
        # Moving obstacles (max 2 active)
        from obstacle import Obstacle  # late import to avoid circular
        self.obstacles: List[Obstacle] = []
        # Starting lives
        self.lives = 4
        self.score = 0
        self.round_num = 1
        self.circles_to_spawn = 1
        self.spawn_timer = 0
        self.spawn_delay = self.target_fps  # 1 second between spawns at current FPS

        self.high_scores = self.load_high_scores()
        
        self.player_name = ""
        self.name_input_active = False

        # UI visibility toggle
        self.show_ui = True

        # Cursor grabbing state
        self.cursor_is_grabbed = False
        self.virtual_mouse_pos = (0, 0)
        
        # Cursor hiding state (from shooter triangles)
        self.cursor_hidden = False
        self.cursor_hide_start_time = 0
        self.cursor_hide_duration = 3000  # 3 seconds in milliseconds

        # Sandbox pause functionality
        self.sandbox_paused = False

        # Volume controls
        self.master_volume = 1.0
        self.tank_volume = 3.5  # Start with tank volume higher for better audibility
        self.effects_volume = 1.0
        self.show_volume_help = False
        
        # Screen flash effects
        self.screen_flash_alpha = 0
        self.screen_flash_color = (255, 100, 100)  # Reddish color for hit effect
        self.pipe_warning_flash_alpha = 0
        self.pipe_warning_flash_color = (100, 100, 255)  # Bluish color for pipe warning
        self.explosion_flash_alpha = 0
        self.explosion_flash_color = (255, 200, 0)  # Orange/yellow color for explosion
        
        # Accessibility settings
        self.accessibility = {
            'pipe_warning_flash': True,  # Flash screen before pipe spawns
            'dynamic_background': True,  # Enable dynamic star system (enabled by default)
            'click_radius_helper': False,  # Show visual click radius around cursor
            'disable_pipes': False,  # Disable pipe obstacles
            'disable_spinners': False,  # Disable spinner obstacles
            'music_enabled': True  # Enable background music
        }
        
        # Click radius helper properties
        self.click_radius = 30  # Base radius in pixels
        self.min_click_radius = 10
        self.max_click_radius = 100
        self.show_accessibility_menu = False
        self.accessibility_menu_index = 0  # selected option index
        # Main menu keyboard selection index
        self.menu_selected_index = 0
        
        # Click radius helper tutorial popup
        self.show_click_radius_tutorial = False
        self.click_radius_tutorial_start_time = 0
        self.click_radius_tutorial_duration = 10.0  # 10 seconds
        
        # Load accessibility settings after initializing defaults
        self.load_accessibility_settings()

        # Difficulty settings
        self.difficulty_settings = {
            Difficulty.EASY: {
                "base_speed_multiplier": 0.3,      # Even slower
                "speed_increase_per_round": 0.01,   # Slower progression
                "max_speed_multiplier": 1.5,       # Lower cap
                "description": "Slow and steady",
                "pipe_settings": {
                    "spawn_chance": 0.15,          # 5% chance to spawn pipes each round
                    "min_round": 8,                 # Earliest round pipes can appear
                    "min_spawn_delay": 5000,        # 5 seconds between pipe spawns (ms)
                    "max_spawn_delay": 15000,       # 15 seconds max between pipe spawns
                    "max_pipes_per_round": 2,       # Max pipes per round
                    "gap_height": 200,              # Gap height in pixels
                    "speed_multiplier": 0.8,        # Speed multiplier for pipes
                    "vertical_speed_range": (0.3, 1.0)  # Range for vertical movement speed
                }
            },
            Difficulty.MEDIUM: {
                "base_speed_multiplier": 0.4,      # Slower
                "speed_increase_per_round": 0.015,  # Slower progression
                "max_speed_multiplier": 2.0,       # Lower cap
                "description": "Balanced challenge",
                "pipe_settings": {
                    "spawn_chance": 0.25,          # 10% chance to spawn pipes each round
                    "min_round": 6,                 # Earlier than easy but later than hard
                    "min_spawn_delay": 4000,        # 4 seconds between pipe spawns (ms)
                    "max_spawn_delay": 12000,       # 12 seconds max between pipe spawns
                    "max_pipes_per_round": 3,       # More pipes per round
                    "gap_height": 180,              # Slightly smaller gap
                    "speed_multiplier": 1.0,        # Normal speed
                    "vertical_speed_range": (0.4, 1.2)  # Slightly faster vertical movement
                }
            },
            Difficulty.HARD: {
                "base_speed_multiplier": 0.6,      # Slower
                "speed_increase_per_round": 0.02,   # Slower progression
                "max_speed_multiplier": 2.5,       # Lower cap
                "description": "Fast and furious",
                "pipe_settings": {
                    "spawn_chance": 0.45,          # 25% chance to spawn pipes each round
                    "min_round": 4,                 # Earlier than medium
                    "min_spawn_delay": 3000,        # 3 seconds between pipe spawns (ms)
                    "max_spawn_delay": 10000,       # 10 seconds max between pipe spawns
                    "max_pipes_per_round": 4,       # More pipes per round
                    "gap_height": 160,              # Smaller gap
                    "speed_multiplier": 1.2,        # Faster pipes
                    "vertical_speed_range": (0.5, 1.5)  # More vertical movement
                }
            },
            Difficulty.NIGHTMARE: {
                "base_speed_multiplier": 0.8,      # Slower
                "speed_increase_per_round": 0.025,  # Slower progression
                "max_speed_multiplier": 3.0,       # Lower cap
                "description": "Insane speed!",
                "pipe_settings": {
                    "spawn_chance": 0.55,          # 50% chance to spawn pipes each round
                    "min_round": 1,                 # Immediate challenge from round 1
                    "min_spawn_delay": 2000,        # 2 seconds between pipe spawns (ms)
                    "max_spawn_delay": 8000,        # 8 seconds max between pipe spawns
                    "max_pipes_per_round": 5,       # Lots of pipes
                    "gap_height": 140,              # Very small gap
                    "speed_multiplier": 1.5,        # Very fast pipes
                    "vertical_speed_range": (0.6, 2.0)  # Very fast and erratic movement
                }
            }
        }

    def _get_optimal_fps(self) -> int:
        """Detect optimal FPS based on monitor capabilities"""
        try:
            # For your 165Hz monitor, we'll target 165 FPS
            # This provides the smoothest possible experience
            if TARGET_FPS == 165:
                return 165
            elif TARGET_FPS > 165:
                return 165  # Cap at 165Hz for your monitor
            else:
                return TARGET_FPS

        except:
            # Fallback to 165 FPS since we know your monitor supports it
            return 165

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode"""
        self.fullscreen = not self.fullscreen

        if self.fullscreen:
            self.screen_width = self.monitor_width
            self.screen_height = self.monitor_height
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.FULLSCREEN)
        else:
            self.screen_width = DEFAULT_WIDTH
            self.screen_height = DEFAULT_HEIGHT
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

        # Recalculate scaling factor
        self.scale_factor = min(self.screen_width / BASE_WIDTH, self.screen_height / BASE_HEIGHT)

        # Update fonts with new scale
        self.font = pygame.font.Font(None, int(36 * self.scale_factor))
        self.big_font = pygame.font.Font(None, int(72 * self.scale_factor))
        self.small_font = pygame.font.Font(None, int(24 * self.scale_factor))

        # Update window caption
        caption = "Circle Clicker Game - "
        caption += "Press F11 for Windowed" if self.fullscreen else "Press F11 for Fullscreen"
        pygame.display.set_caption(caption)

        # Rescale existing circles
        for circle in self.circles:
            # Convert current position to ratio
            x_ratio = circle.x / (circle.x + (BASE_WIDTH * circle.scale_factor))
            y_ratio = circle.y / (circle.y + (BASE_HEIGHT * circle.scale_factor))

            # Update circle's scale factor
            old_scale = circle.scale_factor
            circle.scale_factor = self.scale_factor

            # Rescale properties
            circle.radius = circle.base_radius * self.scale_factor
            circle.speed = (circle.speed / old_scale) * self.scale_factor
            circle.avoid_distance = 100 * self.scale_factor
            circle.avoid_strength = 3 * self.scale_factor
            circle.shrink_rate = 0.15 * self.scale_factor

            # Adjust position proportionally
            circle.x = (circle.x / old_scale) * self.scale_factor
            circle.y = (circle.y / old_scale) * self.scale_factor

            # Keep circles within bounds
            circle.x = max(circle.radius, min(self.screen_width - circle.radius, circle.x))
            circle.y = max(circle.radius, min(self.screen_height - circle.radius, circle.y))

    def get_current_speed_multiplier(self) -> float:
        """Calculate current speed multiplier based on round and difficulty"""
        settings = self.difficulty_settings[self.difficulty]
        base = settings["base_speed_multiplier"]
        increase_per_round = settings["speed_increase_per_round"]
        max_multiplier = settings["max_speed_multiplier"]

        # Speed increases each round
        round_bonus = (self.round_num - 1) * increase_per_round
        total_multiplier = base + round_bonus

        # Cap at maximum
        return min(total_multiplier, max_multiplier)

    def load_high_scores(self) -> List[HighScore]:
        """Load high scores from JSON file"""
        try:
            if os.path.exists("high_scores.json"):
                with open("high_scores.json", "r") as f:
                    data = json.load(f)
                    scores = []
                    for score_data in data:
                        # Handle old scores without difficulty or accessibility info
                        difficulty = score_data.get("difficulty", "Medium")
                        click_radius_helper = score_data.get("click_radius_helper", False)
                        pipes_disabled = score_data.get("pipes_disabled", False)
                        spinners_disabled = score_data.get("spinners_disabled", False)
                        scores.append(HighScore(
                            score_data["name"],
                            score_data["score"],
                            score_data["round_reached"],
                            difficulty,
                            click_radius_helper,
                            pipes_disabled,
                            spinners_disabled
                        ))
                    return scores
        except Exception as e:
            print(f"Error loading high scores: {e}")
        return []

    def save_high_scores(self):
        try:
            data = [{
                "name": hs.name, 
                "score": hs.score, 
                "round_reached": hs.round_reached, 
                "difficulty": hs.difficulty, 
                "click_radius_helper": hs.click_radius_helper,
                "pipes_disabled": hs.pipes_disabled,
                "spinners_disabled": hs.spinners_disabled
            } for hs in self.high_scores]
            with open("high_scores.json", "w") as f:
                json.dump(data, f)
        except:
            pass
    
    def save_accessibility_settings(self):
        """Save accessibility settings to file"""
        try:
            settings_data = {
                'accessibility': self.accessibility,
                'click_radius': self.click_radius
            }
            with open("accessibility_settings.json", "w") as f:
                json.dump(settings_data, f)
        except Exception as e:
            print(f"Error saving accessibility settings: {e}")
    
    def load_accessibility_settings(self):
        """Load accessibility settings from file"""
        try:
            if os.path.exists("accessibility_settings.json"):
                with open("accessibility_settings.json", "r") as f:
                    settings_data = json.load(f)
                    
                # Load accessibility toggles
                if 'accessibility' in settings_data:
                    for key, value in settings_data['accessibility'].items():
                        if key in self.accessibility:
                            self.accessibility[key] = value
                
                # Load click radius
                if 'click_radius' in settings_data:
                    radius = settings_data['click_radius']
                    if self.min_click_radius <= radius <= self.max_click_radius:
                        self.click_radius = radius
                        
        except Exception as e:
            print(f"Error loading accessibility settings: {e}")

    def add_high_score(self, name: str, score: int, round_reached: int):
        difficulty_name = self.difficulty.name.capitalize()
        mode_name = "Timed" if self.game_mode == GameMode.TIMED else "Endless"
        display_difficulty = f"{difficulty_name} ({mode_name})"
        if self.game_mode == GameMode.TIMED:
            display_difficulty += f" {self.time_limit}s"

        # Check if this player already has a score in this difficulty/mode
        existing_score_index = None
        for i, hs in enumerate(self.high_scores):
            if hs.name.lower() == name.lower() and hs.difficulty == display_difficulty:
                existing_score_index = i
                break
        
        new_high_score = HighScore(
            name, 
            score, 
            round_reached, 
            display_difficulty, 
            self.accessibility.get('click_radius_helper', False),
            self.accessibility.get('disable_pipes', False),
            self.accessibility.get('disable_spinners', False)
        )
        
        if existing_score_index is not None:
            # Player already has a score in this mode/difficulty
            existing_score = self.high_scores[existing_score_index]
            if score > existing_score.score:
                # New score is better - replace the old one
                self.high_scores[existing_score_index] = new_high_score
                print(f"Updated {name}'s high score from {existing_score.score} to {score}!")
            elif score == existing_score.score and round_reached > existing_score.round_reached:
                # Same score but reached higher round - update
                self.high_scores[existing_score_index] = new_high_score
                print(f"Updated {name}'s record - same score but reached round {round_reached}!")
            else:
                # New score is not better - don't add it
                print(f"{name} already has a better score ({existing_score.score}) in {display_difficulty}")
                return
        else:
            # No existing score for this player in this mode/difficulty - add new entry
            self.high_scores.append(new_high_score)
            print(f"Added new high score for {name}: {score} points!")
        
        # Sort by score (highest first) and keep top 15
        self.high_scores.sort(key=lambda x: x.score, reverse=True)
        self.high_scores = self.high_scores[:15]
        self.save_high_scores()

    def get_circle_type_for_round(self, round_num: int) -> CircleType:
        # Introduce new circle types gradually
        available_types = [CircleType.NORMAL]

        if round_num >= 2:
            available_types.append(CircleType.FAST)
        if round_num >= 3:
            available_types.append(CircleType.SMALL)
        if round_num >= 4:
            available_types.append(CircleType.SHRINKING)
        if round_num >= 5:
            available_types.append(CircleType.TELEPORTING)
        if round_num >= 6:
            available_types.append(CircleType.GHOST)
        if round_num >= 7:
            available_types.append(CircleType.TANK)
        if round_num >= 8:
            available_types.append(CircleType.HEXAGON)
        if round_num >= 9:
            available_types.append(CircleType.SNAKE)
        if round_num >= 10:
            available_types.append(CircleType.CURSOR_GRABBER)
        if round_num >= 12:
            available_types.append(CircleType.SHOOTER)
        if round_num >= 14:
            available_types.append(CircleType.SUPERTANK)

        # Higher rounds have more difficult circles
        if round_num >= 5:
            weights = []
            for circle_type in available_types:
                if circle_type == CircleType.NORMAL:
                    weights.append(max(1, 10 - round_num))  # Decrease normal circles
                elif circle_type == CircleType.TANK:
                    # Tanks become more common but cap at moderate level
                    weights.append(min(4, round_num - 5))  # Start at weight 2 (round 7), max 4
                elif circle_type in [CircleType.GHOST, CircleType.TELEPORTING]:
                    # Other difficult circles increase normally
                    weights.append(min(5, round_num - 3))  # Increase difficult circles
                elif circle_type == CircleType.HEXAGON:
                    # Hexagons are moderately common, challenging enemy
                    weights.append(min(4, round_num - 6))  # Start at weight 2 (round 8), max 4
                elif circle_type == CircleType.SNAKE:
                    # Snakes are challenging, moderate spawn rate
                    weights.append(min(3, round_num - 8))  # Start at weight 1 (round 9), max 3
                elif circle_type == CircleType.SUPERTANK:
                    # Supertanks are rare but not too rare - increased spawn rate
                    # Start with weight 1.0 at round 14, increase to max 3.0
                    base_weight = max(1.0, (round_num - 14) * 0.2)
                    weights.append(min(3.0, base_weight))
                elif circle_type == CircleType.CURSOR_GRABBER:
                    # Cursor grabbers are more common but limited to max 2 per round
                    # Start with weight 2.0 at round 10, increase to max 4.0
                    base_weight = max(2.0, (round_num - 10) * 0.2)
                    weights.append(min(4.0, base_weight))
                elif circle_type == CircleType.SHOOTER:
                    # Shooters are rare but dangerous - moderate spawn rate
                    # Start with weight 1.0 at round 12, increase to max 2.5
                    base_weight = max(1.0, (round_num - 12) * 0.15)
                    weights.append(min(2.5, base_weight))
                else:
                    # Standard weight for FAST, SMALL, SHRINKING
                    weights.append(3)

            return random.choices(available_types, weights=weights)[0]

        return random.choice(available_types)

    def spawn_circle(self):
        # Spawn away from mouse
        mouse_x, mouse_y = pygame.mouse.get_pos()
        spawn_margin = 50 * self.scale_factor
        min_distance = 150 * self.scale_factor

        attempts = 0
        while attempts < 50:
            x = random.randint(int(spawn_margin), int(self.screen_width - spawn_margin))
            y = random.randint(int(spawn_margin), int(self.screen_height - spawn_margin))

            distance_to_mouse = math.sqrt((x - mouse_x) ** 2 + (y - mouse_y) ** 2)
            if distance_to_mouse > min_distance:
                circle_type = self.get_circle_type_for_round(self.round_num)

                # Limit cursor grabbers to max 2 per round
                if circle_type == CircleType.CURSOR_GRABBER:
                    cursor_grabber_count = sum(1 for c in self.circles if c.type == CircleType.CURSOR_GRABBER)
                    if cursor_grabber_count >= 2:
                        # Too many cursor grabbers, pick a different type
                        available_types = [CircleType.NORMAL, CircleType.FAST, CircleType.SMALL]
                        if self.round_num >= 4:
                            available_types.append(CircleType.SHRINKING)
                        if self.round_num >= 5:
                            available_types.append(CircleType.TELEPORTING)
                        if self.round_num >= 6:
                            available_types.append(CircleType.GHOST)
                        circle_type = random.choice(available_types)

                # Get speed multipliers
                base_speed_mult = self.difficulty_settings[self.difficulty]["base_speed_multiplier"]
                round_speed_mult = self.get_current_speed_multiplier() / base_speed_mult

                # Add size variation for circles after round 7 (excluding small circles)
                size_variation = 1.0
                if self.round_num >= 8 and circle_type != CircleType.SMALL:
                    # 20% chance for smaller (0.8x), 20% chance for bigger (1.2x), 60% chance for normal
                    rand_val = random.random()
                    if rand_val < 0.2:
                        size_variation = 0.8  # 20% smaller
                    elif rand_val < 0.4:
                        size_variation = 1.2  # 20% bigger

                circle = Circle(x, y, circle_type, base_speed_mult, round_speed_mult, self.scale_factor, self.target_fps, self.difficulty, size_variation, self.round_num)
                self.circles.append(circle)
                play_sound(SPAWN_SOUND)
                break
            attempts += 1

        # Fallback if we can't find a good spot
        if attempts >= 50:
            x = random.randint(int(spawn_margin), int(self.screen_width - spawn_margin))
            y = random.randint(int(spawn_margin), int(self.screen_height - spawn_margin))
            circle_type = self.get_circle_type_for_round(self.round_num)

            base_speed_mult = self.difficulty_settings[self.difficulty]["base_speed_multiplier"]
            round_speed_mult = self.get_current_speed_multiplier() / base_speed_mult

            # Add size variation for circles after round 7 (excluding small circles)
            size_variation = 1.0
            if self.round_num >= 8 and circle_type != CircleType.SMALL:
                # 20% chance for smaller (0.8x), 20% chance for bigger (1.2x), 60% chance for normal
                rand_val = random.random()
                if rand_val < 0.2:
                    size_variation = 0.8  # 20% smaller
                elif rand_val < 0.4:
                    size_variation = 1.2  # 20% bigger

            circle = Circle(x, y, circle_type, base_speed_mult, round_speed_mult,
                           self.scale_factor, self.target_fps, self.difficulty,
                           size_variation, self.round_num)
            self.circles.append(circle)
            play_sound(SPAWN_SOUND)

    def _handle_all_circle_collisions(self):
        """Handle collisions between all circles using elastic collision physics with improved wandering preservation"""
        # Check each pair of circles only once
        for i in range(len(self.circles)):
            for j in range(i + 1, len(self.circles)):
                circle1 = self.circles[i]
                circle2 = self.circles[j]

                # Skip if either circle is dying
                if circle1.dying or circle2.dying:
                    continue

                # Calculate distance between circle centers
                dx = circle2.x - circle1.x
                dy = circle2.y - circle1.y
                distance = math.sqrt(dx * dx + dy * dy)

                # Define interaction distances - reduced comfort zone for better wandering
                min_distance = circle1.radius + circle2.radius
                comfort_distance = min_distance * 1.15  # Reduced from 1.3 to allow closer proximity

                if distance > 0:
                    # Normalize the separation vector
                    nx = dx / distance
                    ny = dy / distance

                    # Handle direct collision (overlapping)
                    if distance < min_distance:
                        # Calculate overlap amount
                        overlap = min_distance - distance

                        # More gentle separation to prevent bouncing
                        separation_factor = overlap * 0.5  # Reduced from 0.6
                        circle1.x -= nx * separation_factor
                        circle1.y -= ny * separation_factor
                        circle2.x += nx * separation_factor
                        circle2.y += ny * separation_factor

                        # Calculate relative velocity
                        dvx = circle2.vx - circle1.vx
                        dvy = circle2.vy - circle1.vy

                        # Calculate relative velocity in collision normal direction
                        dvn = dvx * nx + dvy * ny

                        # Only apply collision response if circles are moving toward each other
                        if dvn < 0:
                            # Calculate collision impulse (more conservative elastic collision)
                            impulse = 1.5 * dvn / 2  # Reduced from 2 * dvn to be gentler

                            # Apply collision response with moderate damping for stability
                            damping = 0.85  # Increased damping for smoother collisions
                            impulse_x = impulse * nx * damping
                            impulse_y = impulse * ny * damping

                            # Update velocities
                            circle1.vx += impulse_x
                            circle1.vy += impulse_y
                            circle2.vx -= impulse_x
                            circle2.vy -= impulse_y

                            # Add minimal separation force
                            separation_strength = 1.0 * self.scale_factor  # Reduced from 2.0
                            circle1.vx -= nx * separation_strength
                            circle1.vy -= ny * separation_strength
                            circle2.vx += nx * separation_strength
                            circle2.vy += ny * separation_strength

                    # Handle proximity (close but not overlapping) - much gentler anti-clumping
                    elif distance < comfort_distance:
                        # Apply very gentle separation force when circles are too close
                        proximity_factor = (comfort_distance - distance) / (comfort_distance - min_distance)
                        separation_strength = 0.5 * self.scale_factor * proximity_factor  # Reduced from 1.0

                        # Apply very light separation forces
                        circle1.vx -= nx * separation_strength * 0.05  # Reduced from 0.1
                        circle1.vy -= ny * separation_strength * 0.05
                        circle2.vx += nx * separation_strength * 0.05
                        circle2.vy += ny * separation_strength * 0.05

                    # More lenient velocity limiting to preserve wandering energy
                    max_collision_speed = max(circle1.speed, circle2.speed) * 1.5  # Reduced from 2.0

                    # Limit circle1 velocity
                    circle1_speed = math.sqrt(circle1.vx * circle1.vx + circle1.vy * circle1.vy)
                    if circle1_speed > max_collision_speed:
                        circle1.vx = (circle1.vx / circle1_speed) * max_collision_speed
                        circle1.vy = (circle1.vy / circle1_speed) * max_collision_speed

                    # Limit circle2 velocity
                    circle2_speed = math.sqrt(circle2.vx * circle2.vx + circle2.vy * circle2.vy)
                    if circle2_speed > max_collision_speed:
                        circle2.vx = (circle2.vx / circle2_speed) * max_collision_speed
                        circle2.vy = (circle2.vy / circle2_speed) * max_collision_speed

                    # Keep circles within screen bounds after collision
                    circle1.x = max(circle1.radius, min(self.screen_width - circle1.radius, circle1.x))
                    circle1.y = max(circle1.radius, min(self.screen_height - circle1.radius, circle1.y))
                    circle2.x = max(circle2.radius, min(self.screen_width - circle2.radius, circle2.x))
                    circle2.y = max(circle2.radius, min(self.screen_height - circle2.radius, circle2.y))

    def start_new_game(self):
        self.state = GameState.PLAYING
        # Clean up all tank hum sounds before clearing
        for circle in self.circles:
            circle.cleanup_sounds()
        self.circles.clear()
        self.triangles.clear()  # Clear any remaining triangles
        # Reset cursor state
        self.cursor_hidden = False
        pygame.mouse.set_visible(True)
        self.score = 0
        self.round_num = 1
        self.circles_to_spawn = 1
        self.spawn_timer = 0
        self.obstacles.clear()
        self.lives = 4

        # Initialize timer for timed mode
        if self.game_mode == GameMode.TIMED:
            self.game_start_time = pygame.time.get_ticks()
            self.time_remaining = self.time_limit

    def next_round(self):
        """Start the next round."""
        self.round_num += 1
        # After round 20, cap circle spawns based on difficulty (+2 per difficulty level)
        if self.round_num > 20:
            difficulty_max_circles = {
                Difficulty.EASY: 20,      # Base maximum
                Difficulty.MEDIUM: 23,    # +2 circles
                Difficulty.HARD: 27,      # +4 circles
                Difficulty.NIGHTMARE: 35  # +6 circles
            }
            self.circles_to_spawn = difficulty_max_circles[self.difficulty]
        else:
            self.circles_to_spawn = self.round_num
        self.spawn_timer = 0
        
        # Reset obstacle tracking for new round
        self.obstacles_spawned_this_round = False
        self.obstacles.clear()
        self.pipe_obstacles.clear()
        
        # Round-based maximum obstacle limits (when each count becomes available)
        max_obstacles_by_round = {
            Difficulty.EASY: {
                5: 1,   # Max 1 obstacle from round 5-10
                10: 2,  # Max 2 obstacles from round 10-17
                17: 3   # Max 3 obstacles from round 17+
            },
            Difficulty.MEDIUM: {
                4: 1,   # Max 1 obstacle from round 4-8
                8: 2,   # Max 2 obstacles from round 8-14
                14: 3   # Max 3 obstacles from round 14+
            },
            Difficulty.HARD: {
                3: 1,   # Max 1 obstacle from round 3-6
                6: 2,   # Max 2 obstacles from round 6-10
                10: 3   # Max 3 obstacles from round 10+
            },
            Difficulty.NIGHTMARE: {
                2: 1,   # Max 1 obstacle from round 2-4
                4: 2,   # Max 2 obstacles from round 4-7
                7: 3    # Max 3 obstacles from round 7+
            }
        }[self.difficulty]
        
        # Determine current maximum obstacles allowed
        current_max = 0  # Default to 0 (no obstacles before minimum round)
        for round_threshold, max_count in sorted(max_obstacles_by_round.items()):
            if self.round_num >= round_threshold:
                current_max = max_count
        
        # Use original spawn percentages (same as before round limits)
        obstacle_chances = {
            Difficulty.EASY:      (0.80, 0.15, 0.04, 0.01),  # 80% none, 15% one, 4% two, 1% three
            Difficulty.MEDIUM:    (0.65, 0.25, 0.08, 0.02),  # 65% none, 25% one, 8% two, 2% three
            Difficulty.HARD:      (0.45, 0.35, 0.15, 0.05),  # 45% none, 35% one, 15% two, 5% three
            Difficulty.NIGHTMARE: (0.30, 0.40, 0.20, 0.10),  # 30% none, 40% one, 20% two, 10% three
        }[self.difficulty]
        
        # Determine number of obstacles for this round
        rand = random.random()
        cumulative = 0
        self.obstacles_for_this_round = 0
        
        for num_obstacles, chance in enumerate(obstacle_chances):
            cumulative += chance
            if rand < cumulative:
                self.obstacles_for_this_round = min(num_obstacles, current_max)  # Ensure we don't exceed max
                break
        
        # Mark round for obstacles if we're spawning any
        if self.obstacles_for_this_round > 0:
            self.rounds_with_obstacles.add(self.round_num)
        else:
            self.rounds_with_obstacles.discard(self.round_num)
        
        # Reset pipe obstacle tracking for new round
        self.pipe_obstacles_this_round = 0
        self.last_pipe_spawn_time = pygame.time.get_ticks()
        self.next_pipe_spawn_time = 0  # Will be set when we decide to spawn a pipe
        self.pending_pipe_spawn = False
        # Reset burst system
        self.in_quick_burst = False
        self.quick_burst_remaining = 0
        # Reset flash arming
        self.pipe_flash_armed = False
        self.pipe_flash_time = 0
        
        # Check if we should enable pipe spawning this round based on difficulty settings
        pipe_settings = self.difficulty_settings[self.difficulty]["pipe_settings"]
        spawn_roll = random.random()
        spawn_chance = pipe_settings["spawn_chance"]
        if (self.round_num >= pipe_settings["min_round"] and 
            spawn_roll < spawn_chance):
            self.pending_pipe_spawn = True
            # Schedule the first pipe spawn with a random delay
            self.schedule_next_pipe_spawn()

    def schedule_next_pipe_spawn(self):
        """Schedule the next pipe spawn with a random delay based on difficulty.
        Occasionally (30%) schedule a quick follow-up spawn 300-800 ms later.
        """
        if not self.pending_pipe_spawn:
            return

        pipe_settings = self.difficulty_settings[self.difficulty]["pipe_settings"]

        # If force_quick_pipes is enabled, always use quick spawn
        if self.force_quick_pipes:
            delay = random.randint(500, 1200)
        # If we're in a quick burst, use quick delay
        elif self.in_quick_burst and self.quick_burst_remaining > 0:
            delay = random.randint(500, 1200)
            self.quick_burst_remaining -= 1
            # End burst when no pipes remaining
            if self.quick_burst_remaining <= 0:
                self.in_quick_burst = False
        else:
            delay = random.randint(
                pipe_settings["min_spawn_delay"],
                pipe_settings["max_spawn_delay"]
            )
            # 30% chance to trigger a quick burst (if room for multiple pipes)
            remaining_pipe_slots = pipe_settings["max_pipes_per_round"] - self.pipe_obstacles_this_round
            if remaining_pipe_slots > 1 and random.random() < 0.3:
                # Determine burst size based on difficulty and available slots
                if self.difficulty.name == 'EASY':
                    max_burst = min(3, remaining_pipe_slots)  # 2-3 pipes
                    burst_size = random.randint(2, max_burst)
                elif self.difficulty.name == 'MEDIUM':
                    max_burst = min(3, remaining_pipe_slots)  # 2-3 pipes  
                    burst_size = random.randint(2, max_burst)
                else:  # HARD and NIGHTMARE
                    max_burst = min(5, remaining_pipe_slots)  # 2-5 pipes
                    burst_size = random.randint(2, max_burst)
                
                # Start the burst - change delay to quick for immediate next spawn
                self.in_quick_burst = True
                self.quick_burst_remaining = burst_size - 1
                delay = random.randint(500, 1200)  # Make the next spawn quick too

        self.next_pipe_spawn_time = pygame.time.get_ticks() + delay
        # Arm the warning flash to trigger ~500ms before spawn (or immediately if less than 500ms away)
        if self.accessibility.get('pipe_warning_flash', True):
            self.pipe_flash_armed = True
            self.pipe_flash_time = max(0, self.next_pipe_spawn_time - 500)
        
    def update_tank_volumes(self):
        """Update volume for all currently playing tank hum sounds"""
        tank_volume = self.master_volume * self.tank_volume
        for circle in self.circles:
            if circle.hum_sound and hasattr(circle, 'hum_channel'):
                try:
                    circle.hum_sound.set_volume(tank_volume)
                except:
                    pass

    def start_sandbox_mode(self):
        """Start sandbox mode for testing all circle types"""
        self.state = GameState.SANDBOX
        # Clean up all tank hum sounds before clearing
        for circle in self.circles:
            circle.cleanup_sounds()
        self.circles.clear()
        self.triangles.clear()  # Clear any remaining triangles
        # Reset cursor state
        self.cursor_hidden = False
        pygame.mouse.set_visible(True)
        self.score = 0
        self.round_num = 15  # High round for all special features
        self.circles_to_spawn = 0
        self.spawn_timer = 0
        self.sandbox_paused = False  # Reset pause state
        self.lives = 3  # Reset lives

    def spawn_sandbox_circle(self, circle_type: CircleType):
        """Spawn a specific circle type in sandbox mode"""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        spawn_margin = 50 * self.scale_factor
        min_distance = 150 * self.scale_factor

        # Try to spawn away from mouse, but don't be too strict
        attempts = 0
        while attempts < 20:
            x = random.randint(int(spawn_margin), int(self.screen_width - spawn_margin))
            y = random.randint(int(spawn_margin), int(self.screen_height - spawn_margin))

            distance_to_mouse = math.sqrt((x - mouse_x) ** 2 + (y - mouse_y) ** 2)
            if distance_to_mouse > min_distance or attempts > 10:
                break
            attempts += 1

        # Get speed multipliers
        base_speed_mult = self.difficulty_settings[self.difficulty]["base_speed_multiplier"]
        round_speed_mult = self.get_current_speed_multiplier() / base_speed_mult

        # Random size variation
        size_variation = random.choice([0.8, 1.0, 1.2]) if circle_type != CircleType.SMALL else 1.0

        circle = Circle(x, y, circle_type, base_speed_mult, round_speed_mult,
                       self.scale_factor, self.target_fps, self.difficulty,
                       size_variation, self.round_num)
        self.circles.append(circle)

    def spawn_sandbox_obstacle(self):
        """Spawn a spinning obstacle in sandbox mode"""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        spawn_margin = 100
        min_distance_from_cursor = int(240 * self.scale_factor)
        
        # Try to spawn away from mouse and other obstacles
        best_pos = None
        best_dist = -1
        for attempt in range(30):
            ox = random.randint(spawn_margin, self.screen_width - spawn_margin)
            oy = random.randint(spawn_margin, self.screen_height - spawn_margin)
            
            # Check distance from cursor
            dx = ox - mouse_x
            dy = oy - mouse_y
            distance_from_cursor = (dx * dx + dy * dy) ** 0.5
            
            # Check distance from other obstacles
            too_close_to_obstacle = any(
                ((ox - o.x) ** 2 + (oy - o.y) ** 2) ** 0.5 < 220 
                for o in self.obstacles
            )
            
            if not too_close_to_obstacle and distance_from_cursor > best_dist:
                best_dist = distance_from_cursor
                best_pos = (ox, oy)
            
            if distance_from_cursor >= min_distance_from_cursor and not too_close_to_obstacle:
                self.obstacles.append(Obstacle(ox, oy, self.scale_factor, self.screen_width, self.screen_height))
                return
        
        # Fallback to farthest valid sampled position
        if best_pos is not None:
            ox, oy = best_pos
            self.obstacles.append(Obstacle(ox, oy, self.scale_factor, self.screen_width, self.screen_height))

    def spawn_pipe_obstacle(self):
        """Spawn a pipe obstacle (used by automatic spawning system)"""
        # Don't spawn if pipes are disabled
        if self.accessibility.get('disable_pipes', False):
            return
            
        pipe_settings = self.difficulty_settings[self.difficulty]["pipe_settings"]
        
        # Create new pipe obstacle
        pipe = PipeObstacle(
            self.screen_width, 
            self.screen_height, 
            self.scale_factor
        )
        
        # Apply difficulty-based settings
        gap_height_base = pipe_settings["gap_height"] * self.scale_factor
        speed_multiplier = pipe_settings["speed_multiplier"]
        min_vert_speed, max_vert_speed = pipe_settings["vertical_speed_range"]

        # Introduce variability in gap height (±20%)
        pipe.gap_height = random.uniform(0.8 * gap_height_base, 1.2 * gap_height_base)

        # Introduce variability in pipe width (thickness)
        min_width = 40 * self.scale_factor
        max_width = 80 * self.scale_factor
        pipe.width = random.uniform(min_width, max_width)
        # Ensure the pipe starts fully off-screen with the new width
        pipe.x = -pipe.width

        pipe.speed *= speed_multiplier
        pipe.vertical_speed = random.uniform(min_vert_speed, max_vert_speed)
        
        self.pipe_obstacles.append(pipe)
        
        # If quick pipe mode is enabled, schedule the next spawn
        if self.force_quick_pipes:
            self.pending_pipe_spawn = True
            self.schedule_next_pipe_spawn()
        # In sandbox mode, also trigger natural burst system (30% chance)
        elif self.state == GameState.SANDBOX and not self.in_quick_burst:
            if random.random() < 0.3:
                # Determine burst size based on difficulty (sandbox has no limits)
                if self.difficulty.name == 'EASY':
                    burst_size = random.randint(2, 3)  # 2-3 pipes
                elif self.difficulty.name == 'MEDIUM':
                    burst_size = random.randint(2, 3)  # 2-3 pipes  
                else:  # HARD and NIGHTMARE
                    burst_size = random.randint(2, 5)  # 2-5 pipes
                
                # Start the burst
                self.in_quick_burst = True
                self.quick_burst_remaining = burst_size - 1
                self.pending_pipe_spawn = True
                self.schedule_next_pipe_spawn()

    def handle_click(self, pos: Tuple[int, int]):
        # Ignore clicks while cursor is hidden (e.g., after triangle hit)
        if hasattr(self, 'cursor_hidden') and self.cursor_hidden:
            return
        if self.state == GameState.PLAYING or self.state == GameState.SANDBOX:
            # If cursor is grabbed, use virtual mouse position instead of click position
            if hasattr(self, 'cursor_is_grabbed') and self.cursor_is_grabbed and hasattr(self, 'virtual_mouse_pos'):
                pos = self.virtual_mouse_pos
            # Find all circles that could be clicked at this position
            clickable_circles = []
            for circle in self.circles:
                # Check if circle can be clicked (either normal click or within accessibility radius)
                can_click = False
                if self.accessibility.get('click_radius_helper', False):
                    # First check if the circle would normally be clickable (respects game mechanics)
                    if circle.is_clicked(pos):
                        # Normal click works, so it's definitely clickable
                        can_click = True
                    else:
                        # Normal click doesn't work, check if enhanced radius would help
                        # But ONLY if the circle doesn't have special restrictions
                        
                        # Skip grabbers that are actively grabbing
                        if circle.type == CircleType.CURSOR_GRABBER and hasattr(circle, 'is_grabbing') and circle.is_grabbing:
                            can_click = False
                        # Skip snake heads when segments still exist
                        elif (circle.type == CircleType.SNAKE and hasattr(circle, 'segments') and 
                              hasattr(circle, 'segments_killed') and circle.segments_killed < len(circle.segments)):
                            # For snakes, we need to check if this would be clicking the head when segments remain
                            distance = math.sqrt((circle.x - pos[0]) ** 2 + (circle.y - pos[1]) ** 2)
                            if distance <= (self.click_radius + circle.radius):
                                # This would be clicking the head area, but segments remain - not allowed
                                can_click = False
                            else:
                                # Check if clicking on any valid segment with enhanced radius
                                for i in range(len(circle.segments)):
                                    # Skip segments that have already been killed
                                    if i >= len(circle.segments) - circle.segments_killed:
                                        continue
                                    
                                    seg_x, seg_y = circle.segments[i]
                                    seg_distance = math.sqrt((seg_x - pos[0]) ** 2 + (seg_y - pos[1]) ** 2)
                                    seg_radius = max(int(circle.radius * 0.8), 8)
                                    
                                    if seg_distance <= (self.click_radius + seg_radius):
                                        # Check if this is the correct next segment (back to front order)
                                        expected_segment_index = len(circle.segments) - 1 - circle.segments_killed
                                        if i == expected_segment_index:
                                            # Instead of setting can_click=True, call is_clicked with segment position
                                            # This ensures proper segment handling through the existing logic
                                            can_click = circle.is_clicked((seg_x, seg_y))
                                            break
                        else:
                            # For other circle types, use enhanced radius detection
                            distance = math.sqrt((circle.x - pos[0]) ** 2 + (circle.y - pos[1]) ** 2)
                            can_click = distance <= (self.click_radius + circle.radius)
                else:
                    # Use normal click detection
                    can_click = circle.is_clicked(pos)
                
                # Don't allow clicking invisible shooters
                is_invisible_shooter = (circle.type == CircleType.SHOOTER and 
                                       hasattr(circle, 'is_invisible') and circle.is_invisible)
                
                if can_click and not circle.dying and not is_invisible_shooter:
                    # Calculate distance from click to circle center for priority
                    distance = math.sqrt((circle.x - pos[0]) ** 2 + (circle.y - pos[1]) ** 2)

                    # Create priority score: smaller distance = higher priority
                    # Also prioritize special types (hexagons, tanks) over normal circles
                    type_priority = 0
                    if circle.type == CircleType.HEXAGON:
                        type_priority = -5  # Hexagons get priority (negative = better)
                    elif circle.type in [CircleType.TANK, CircleType.SUPERTANK]:
                        type_priority = -3  # Tanks get priority
                    elif circle.type == CircleType.SMALL:
                        type_priority = -2  # Small circles get priority (harder to hit)

                    # Combine distance and type priority
                    priority_score = distance + type_priority
                    clickable_circles.append((circle, priority_score))

            if clickable_circles:
                # Sort by priority score - lowest score gets hit first
                clickable_circles.sort(key=lambda x: x[1])

                # Hit the highest priority circle
                target_circle = clickable_circles[0][0]
                
                # Track supertank clicks for regeneration timing
                if target_circle.type == CircleType.SUPERTANK and hasattr(target_circle, 'last_clicked_time'):
                    target_circle.last_clicked_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds
                    target_circle.regen_active = False  # Stop any active regeneration
                
                if target_circle.take_damage():
                    self.score += target_circle.points
                    play_sound(COIN_SOUND)

    def update(self):
        if self.state == GameState.PLAYING:
            # Check for cursor grabbers FIRST and completely override mouse input if grabbed
            cursor_is_grabbed = False
            for circle in self.circles:
                if (circle.type == CircleType.CURSOR_GRABBER and
                    circle.is_grabbing and
                    hasattr(circle, 'cursor_target_x') and
                    hasattr(circle, 'cursor_target_y')):
                    # Cursor is grabbed - completely ignore real mouse position
                    mouse_pos = (int(circle.cursor_target_x), int(circle.cursor_target_y))
                    cursor_is_grabbed = True
                    break  # Only one cursor grabber should control at a time

            # Only use real mouse position if cursor is not grabbed
            if not cursor_is_grabbed:
                mouse_pos = pygame.mouse.get_pos()

            # Store grabbed state for use in event handling and drawing
            self.cursor_is_grabbed = cursor_is_grabbed
            self.virtual_mouse_pos = mouse_pos

            # ------------------ Obstacles ------------------
            # Spawn obstacles at the start of rounds that were chosen to have them (unless disabled)
            if (not self.accessibility.get('disable_spinners', False) and
                self.circles_to_spawn == self.round_num and 
                not self.obstacles_spawned_this_round and  # Only spawn once per round
                self.round_num in self.rounds_with_obstacles):
                
                # Mark that we've spawned obstacles this round
                self.obstacles_spawned_this_round = True
                
                # Spawn first obstacle away from cursor
                cursor_pos = self.virtual_mouse_pos if self.cursor_is_grabbed else pygame.mouse.get_pos()
                # Scale the required distance by resolution so spinners never spawn on the cursor
                min_distance_from_cursor = int(240 * self.scale_factor)
                
                # Use the predetermined number of obstacles for this round
                num_obstacles = self.obstacles_for_this_round

                # Clear any existing obstacles first (shouldn't be any, but just in case)
                self.obstacles.clear()

                # Spawn the decided number of obstacles, respecting spacing rules
                for _ in range(num_obstacles):
                    placed = False
                    best_pos = None
                    best_dist = -1
                    for attempt in range(30):
                        ox = random.randint(100, self.screen_width - 100)
                        oy = random.randint(100, self.screen_height - 100)

                        dx = ox - cursor_pos[0]
                        dy = oy - cursor_pos[1]
                        distance = (dx * dx + dy * dy) ** 0.5

                        # Check distance from other obstacles already placed in this loop
                        too_close = any(((ox - o.x) ** 2 + (oy - o.y) ** 2) ** 0.5 < 220 for o in self.obstacles)

                        if not too_close and distance > best_dist:
                            best_dist = distance
                            best_pos = (ox, oy)

                        if distance >= min_distance_from_cursor and not too_close:
                            self.obstacles.append(Obstacle(ox, oy, self.scale_factor, self.screen_width, self.screen_height))
                            placed = True
                            break
                    # Fallback: place at farthest tested valid position (still not too close to others)
                    if not placed and best_pos is not None:
                        ox, oy = best_pos
                        self.obstacles.append(Obstacle(ox, oy, self.scale_factor, self.screen_width, self.screen_height))
            
            # Handle pipe obstacle spawning during gameplay
            if self.state == GameState.PLAYING and self.pending_pipe_spawn:
                current_time = pygame.time.get_ticks()
                pipe_settings = self.difficulty_settings[self.difficulty]["pipe_settings"]
                
                # Trigger warning flash before spawn using an armed timestamp
                if (self.accessibility.get('pipe_warning_flash', True) and
                    self.pending_pipe_spawn and
                    self.pipe_flash_armed and
                    current_time >= getattr(self, 'pipe_flash_time', 0) and
                    self.pipe_obstacles_this_round < pipe_settings["max_pipes_per_round"]):
                    self.pipe_warning_flash_alpha = 100  # Start flash
                    self.pipe_flash_armed = False
                
                # Check if it's time to spawn a new pipe (unless disabled in accessibility)
                if (not self.accessibility.get('disable_pipes', False) and
                    current_time >= self.next_pipe_spawn_time and 
                    self.pipe_obstacles_this_round < pipe_settings["max_pipes_per_round"]):
                    
                    # Spawn a new pipe obstacle
                    pipe = PipeObstacle(
                        self.screen_width, 
                        self.screen_height, 
                        self.scale_factor
                    )
                    pipe.spawn_time = current_time  # Track when this pipe was spawned
                    
                    # Apply difficulty-based settings
                    gap_height_base = pipe_settings["gap_height"] * self.scale_factor
                    speed_multiplier = pipe_settings["speed_multiplier"]
                    min_vert_speed, max_vert_speed = pipe_settings["vertical_speed_range"]

                    # Introduce variability in gap height (±20%)
                    pipe.gap_height = random.uniform(0.8 * gap_height_base, 1.2 * gap_height_base)

                    # Introduce variability in pipe width (thickness)
                    min_width = 40 * self.scale_factor
                    max_width = 80 * self.scale_factor
                    pipe.width = random.uniform(min_width, max_width)
                    # Ensure the pipe starts fully off-screen with the new width
                    pipe.x = -pipe.width

                    pipe.speed *= speed_multiplier
                    pipe.vertical_speed = random.uniform(min_vert_speed, max_vert_speed)
                    
                    self.pipe_obstacles.append(pipe)
                    self.pipe_obstacles_this_round += 1
                    self.last_pipe_spawn_time = current_time
                    
                    # Schedule next pipe spawn if we haven't reached the max
                    if self.pipe_obstacles_this_round < pipe_settings["max_pipes_per_round"]:
                        self.schedule_next_pipe_spawn()
                    else:
                        self.pending_pipe_spawn = False
                
                # Regular obstacle spawning during active gameplay has been disabled.
                # All spinning obstacles are now spawned at the start of the round
                # with a maximum of three per round.
            # Update obstacles (they no longer expire until round end)
            for obs in self.obstacles:
                obs.update()
                
            # Update pipe obstacles
            current_time = pygame.time.get_ticks()
            for pipe in list(self.pipe_obstacles):
                pipe.update()
                # Remove pipe if it's off screen or has been around too long (safety check)
                if pipe.is_off_screen() or (current_time - pipe.spawn_time > 30000):  # 30 second max lifetime
                    self.pipe_obstacles.remove(pipe)
            
            # Cursor position for hit test
            cursor_pos = self.virtual_mouse_pos if self.cursor_is_grabbed else pygame.mouse.get_pos()
            
            # Check for collisions with obstacles
            for obs in self.obstacles + self.pipe_obstacles:
                # Skip if this obstacle is on cooldown
                if hasattr(obs, 'hit_cooldown') and obs.hit_cooldown > 0:
                    obs.hit_cooldown -= 1
                    continue
                    
                # Check for collision based on obstacle type
                is_hit = False
                if hasattr(obs, 'is_cursor_hit'):  # Pipe obstacle
                    is_hit = obs.is_cursor_hit(cursor_pos)
                else:  # Regular obstacle - use circle collision with radius
                    dx = obs.x - cursor_pos[0]
                    dy = obs.y - cursor_pos[1]
                    distance_sq = dx*dx + dy*dy
                    is_hit = distance_sq < (obs.radius ** 2)
                
                # Handle hit
                if is_hit:
                    self.lives -= 1
                    self.screen_flash_alpha = 255  # Trigger screen flash
                    play_sound(HIT_SOUND, 'effects', self)
                    obs.hit_cooldown = 30  # 0.5 seconds at 60 FPS
                    
                    if self.lives <= 0:
                        self.state = GameState.GAME_OVER
                        self.name_input_active = True
                        play_sound(GAME_OVER_SOUND, 'effects', self)
                        return

            # Update circles
            # Pass circles reference to cursor grabbers for coordination
            for circle in self.circles:
                if circle.type == CircleType.CURSOR_GRABBER:
                    circle._game_circles_ref = self.circles

            for circle in self.circles[:]:
                if update_circle(circle, mouse_pos, self.screen_width, self.screen_height):
                    circle.cleanup_sounds()
                    self.circles.remove(circle)

            # Handle circle-to-circle collisions separately
            self._handle_all_circle_collisions()
            
            # Update triangles and check cursor collisions
            current_time = pygame.time.get_ticks()
            for triangle in self.triangles[:]:
                if not triangle.update(self.screen_width, self.screen_height):
                    self.triangles.remove(triangle)  # Remove expired triangles
                    continue
                    
                # Check collision with cursor (only if cursor is not already hidden)
                if not self.cursor_hidden and triangle.check_cursor_collision(mouse_pos[0], mouse_pos[1]):
                    print(f"DEBUG: Triangle hit cursor at {mouse_pos}! Hiding cursor.")
                    # Hide cursor for 2 seconds
                    self.cursor_hidden = True
                    self.cursor_hide_start_time = current_time
                    pygame.mouse.set_visible(False)
                    triangle.start_fade(100)  # Very fast fade when hit by cursor (100ms)
            
            # Check if cursor should be unhidden
            if self.cursor_hidden and current_time - self.cursor_hide_start_time >= self.cursor_hide_duration:
                self.cursor_hidden = False
                pygame.mouse.set_visible(True)

            # Spawn new circles
            if self.circles_to_spawn > 0:
                self.spawn_timer += 1
                if self.spawn_timer >= self.spawn_delay:
                    self.spawn_circle()
                    self.circles_to_spawn -= 1
                    self.spawn_timer = 0

            # Handle round progression based on game mode
            if self.game_mode == GameMode.ENDLESS:
                # Check if round is complete for endless mode
                if self.circles_to_spawn == 0 and len([c for c in self.circles if not c.dying]) == 0:
                    self.next_round()
            else:  # Timed mode
                # Same round progression as endless mode, but with timer
                if self.circles_to_spawn == 0 and len([c for c in self.circles if not c.dying]) == 0:
                    self.next_round()

        elif self.state == GameState.SANDBOX:
            # In sandbox mode, circles still move and behave normally (unless paused)
            if not self.sandbox_paused:
                # Check for cursor grabbers FIRST and completely override mouse input if grabbed
                cursor_is_grabbed = False
                for circle in self.circles:
                    if (circle.type == CircleType.CURSOR_GRABBER and
                        circle.is_grabbing and
                        hasattr(circle, 'cursor_target_x') and
                        hasattr(circle, 'cursor_target_y')):
                        # Cursor is grabbed - completely ignore real mouse position
                        mouse_pos = (int(circle.cursor_target_x), int(circle.cursor_target_y))
                        cursor_is_grabbed = True
                        break  # Only one cursor grabber should control at a time

                # Only use real mouse position if cursor is not grabbed
                if not cursor_is_grabbed:
                    mouse_pos = pygame.mouse.get_pos()

                # Store grabbed state for use in event handling and drawing
                self.cursor_is_grabbed = cursor_is_grabbed
                self.virtual_mouse_pos = mouse_pos

                # Update circles
                # Pass circles reference to cursor grabbers for coordination
                for circle in self.circles:
                    if circle.type == CircleType.CURSOR_GRABBER:
                        circle._game_circles_ref = self.circles

                for circle in self.circles[:]:
                    if update_circle(circle, mouse_pos, self.screen_width, self.screen_height):
                        circle.cleanup_sounds()
                        self.circles.remove(circle)

                # Handle circle-to-circle collisions separately
                self._handle_all_circle_collisions()
                
                # Update triangles and check cursor collisions
                current_time = pygame.time.get_ticks()
                for triangle in self.triangles[:]:
                    if not triangle.update(self.screen_width, self.screen_height):
                        self.triangles.remove(triangle)  # Remove expired triangles
                        continue
                        
                    # Check collision with cursor (only if cursor is not already hidden)
                    if not self.cursor_hidden and triangle.check_cursor_collision(mouse_pos[0], mouse_pos[1]):
                        print(f"DEBUG: Triangle hit cursor at {mouse_pos}! Hiding cursor.")
                        # Hide cursor for 2 seconds
                        self.cursor_hidden = True
                        self.cursor_hide_start_time = current_time
                        pygame.mouse.set_visible(False)
                        triangle.start_fade(100)  # Very fast fade when hit by cursor (100ms)
                
                # Check if cursor should be unhidden
                if self.cursor_hidden and current_time - self.cursor_hide_start_time >= self.cursor_hide_duration:
                    self.cursor_hidden = False
                    pygame.mouse.set_visible(True)
                
                # Update spinning obstacles
                for obs in self.obstacles:
                    obs.update()
                
                # Update pipe obstacles
                for pipe in list(self.pipe_obstacles):
                    pipe.update()
                    if pipe.is_off_screen():
                        self.pipe_obstacles.remove(pipe)
                
                # Handle automatic pipe spawning in quick pipe mode (unless disabled)
                if (not self.accessibility.get('disable_pipes', False) and
                    self.pending_pipe_spawn and hasattr(self, 'next_pipe_spawn_time')):
                    current_time = pygame.time.get_ticks()
                    if current_time >= self.next_pipe_spawn_time:
                        self.spawn_pipe_obstacle()
                        self.pending_pipe_spawn = False
                
                # Check for collisions with spinning obstacles
                cursor_pos = self.virtual_mouse_pos if self.cursor_is_grabbed else pygame.mouse.get_pos()
                for obs in self.obstacles:
                    dx = obs.x - cursor_pos[0]
                    dy = obs.y - cursor_pos[1]
                    distance = (dx * dx + dy * dy) ** 0.5
                    if distance < obs.radius:
                        if not hasattr(obs, 'hit_cooldown') or obs.hit_cooldown <= 0:
                            self.lives -= 1
                            self.screen_flash_alpha = 255  # Trigger screen flash
                            play_sound(HIT_SOUND, 'effects', self)
                            obs.hit_cooldown = 30  # 0.5 seconds at 60 FPS
                            if self.lives <= 0:
                                self.lives = 1  # Prevent game over in sandbox
                    
                    # Update cooldown
                    if hasattr(obs, 'hit_cooldown') and obs.hit_cooldown > 0:
                        obs.hit_cooldown -= 1
                
                # Check for collisions with pipe obstacles
                for pipe in self.pipe_obstacles:
                    if pipe.is_cursor_hit(cursor_pos):
                        if not hasattr(pipe, 'hit_cooldown') or pipe.hit_cooldown <= 0:
                            self.lives -= 1
                            self.screen_flash_alpha = 255  # Trigger screen flash
                            play_sound(HIT_SOUND, 'effects', self)
                            pipe.hit_cooldown = 30  # 0.5 seconds at 60 FPS
                            if self.lives <= 0:
                                self.lives = 1  # Prevent game over in sandbox
                    
                    # Update cooldown
                    if hasattr(pipe, 'hit_cooldown') and pipe.hit_cooldown > 0:
                        pipe.hit_cooldown -= 1

            # No automatic spawning or round progression in sandbox mode
        
        # Handle timer countdown for timed mode
        if self.game_mode == GameMode.TIMED and self.state == GameState.PLAYING:
            # Calculate elapsed time since game started
            current_time = pygame.time.get_ticks()
            elapsed_time = (current_time - self.game_start_time) / 1000.0  # Convert to seconds
            
            # Update remaining time
            self.time_remaining = max(0, self.time_limit - elapsed_time)
            
            # Check if time is up
            if self.time_remaining <= 0:
                self.state = GameState.GAME_OVER
    
    def trigger_explosion_flash(self):
        """Trigger explosion screen flash effect"""
        print("DEBUG: Explosion flash triggered! Alpha set to 255")
        self.explosion_flash_alpha = 255  # Full intensity explosion flash
