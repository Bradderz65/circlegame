import pygame
import random
import math
from typing import Tuple

from game_config import *
from circle import CircleType

def _detect_corner_proximity(circle, screen_width, screen_height, margin_multiplier=60):
    """Detect if circle is near corners/edges"""
    margin = margin_multiplier * circle.scale_factor
    near_left = circle.x < margin
    near_right = circle.x > screen_width - margin
    near_top = circle.y < margin
    near_bottom = circle.y > screen_height - margin
    
    in_corner = ((near_left and near_top) or 
                 (near_right and near_top) or 
                 (near_left and near_bottom) or 
                 (near_right and near_bottom))
    
    return {
        'near_left': near_left,
        'near_right': near_right,
        'near_top': near_top,
        'near_bottom': near_bottom,
        'in_corner': in_corner,
        'margin': margin
    }

def _apply_wandering_movement(circle, speed_multiplier, angle_range, duration_range, 
                             timer_attr, angle_attr, duration_attr):
    """Apply wandering movement with configurable parameters"""
    # Initialize attributes if they don't exist
    if not hasattr(circle, timer_attr):
        setattr(circle, timer_attr, 0)
        setattr(circle, angle_attr, random.uniform(0, 2 * math.pi))
        setattr(circle, duration_attr, random.randint(duration_range[0], duration_range[1]))
    
    # Update timer
    timer = getattr(circle, timer_attr) + 1
    setattr(circle, timer_attr, timer)
    
    # Check if time to change direction
    if timer >= getattr(circle, duration_attr):
        current_angle = getattr(circle, angle_attr)
        angle_change = random.uniform(angle_range[0], angle_range[1])
        setattr(circle, angle_attr, current_angle + angle_change)
        setattr(circle, timer_attr, 0)
        setattr(circle, duration_attr, random.randint(duration_range[0], duration_range[1]))
    
    # Apply movement
    angle = getattr(circle, angle_attr)
    vx = math.cos(angle) * circle.speed * speed_multiplier
    vy = math.sin(angle) * circle.speed * speed_multiplier
    
    return vx, vy

def update_circle(circle, mouse_pos: Tuple[int, int], screen_width: int, screen_height: int):
    """Update circle position and behavior"""
    mouse_x, mouse_y = mouse_pos
    if circle.dying:
        circle.death_timer += 1
        # Death animation - expand and fade
        expansion_factor = 1 + (circle.death_timer / circle.death_duration) * 2
        circle.radius = (circle.base_radius * circle.scale_factor) * expansion_factor
        return circle.death_timer >= circle.death_duration

    # Handle special type behaviors
    if circle.type.name == 'TELEPORTING':
        # Check if player is within proximity range before allowing teleport
        distance_to_player = ((circle.x - mouse_x) ** 2 + (circle.y - mouse_y) ** 2) ** 0.5
        
        if distance_to_player <= circle.proximity_teleport_range:
            # Player is close - count down teleport timer
            circle.teleport_cooldown -= 1
            
            if circle.teleport_cooldown <= 0:
                # Teleport to a new location
                spawn_margin = 50 * circle.scale_factor
                circle.x = random.randint(int(spawn_margin), int(screen_width - spawn_margin))
                circle.y = random.randint(int(spawn_margin), int(screen_height - spawn_margin))

                # Set next teleport interval using direct proximity interval
                # Apply ±25% randomization to the interval
                random_factor = random.uniform(0.75, 1.25)
                circle.teleport_cooldown = int(circle.proximity_teleport_interval_frames * random_factor)
        else:
            # Player is far - reset teleport timer to be ready when they get close
            # Use a small cooldown so they can teleport quickly when player approaches
            circle.teleport_cooldown = min(circle.teleport_cooldown, int(0.5 * circle.target_fps))

    elif circle.type.name == 'SHRINKING':
        # Scale shrink rate with difficulty
        shrink_mult = getattr(circle, 'shrink_multiplier', 1.0)
        scaled_shrink_rate = circle.shrink_rate * shrink_mult
        circle.base_radius -= scaled_shrink_rate
        if circle.base_radius <= 5:
            circle.base_radius = 30  # Reset size

    elif circle.type.name == 'GHOST':
        # Proximity-based transparency and size changes
        mouse_x, mouse_y = mouse_pos
        dx = circle.x - mouse_x
        dy = circle.y - mouse_y
        distance_to_mouse = math.sqrt(dx * dx + dy * dy)

        # Define proximity thresholds
        proximity_threshold = 120 * circle.scale_factor  # Distance at which effects start
        min_distance = 40 * circle.scale_factor  # Distance for maximum effect

        # Calculate proximity factor (0 = far away, 1 = very close)
        if distance_to_mouse <= min_distance:
            proximity_factor = 1.0
        elif distance_to_mouse >= proximity_threshold:
            proximity_factor = 0.0
        else:
            proximity_factor = 1.0 - (distance_to_mouse - min_distance) / (proximity_threshold - min_distance)

        # Store base values if not already stored
        if not hasattr(circle, 'base_ghost_alpha'):
            circle.base_ghost_alpha = 128
            circle.base_ghost_radius = circle.base_radius
            circle.target_ghost_alpha = circle.base_ghost_alpha
            circle.target_radius_multiplier = 1.0

        # Calculate target values based on proximity
        min_alpha = 30  # Very transparent when close
        min_radius_multiplier = 0.6  # Shrink to 60% when close

        circle.target_ghost_alpha = circle.base_ghost_alpha * (1.0 - proximity_factor * 0.75)  # Reduce alpha by up to 75%
        circle.target_radius_multiplier = 1.0 - proximity_factor * (1.0 - min_radius_multiplier)

        # Ensure minimum values
        circle.target_ghost_alpha = max(min_alpha, circle.target_ghost_alpha)
        circle.target_radius_multiplier = max(min_radius_multiplier, circle.target_radius_multiplier)

        # Smooth transitions back to normal values
        transition_speed = 0.08 * (circle.target_fps / 60)  # Smooth transition speed

        # Apply smooth alpha transition
        alpha_diff = circle.target_ghost_alpha - circle.ghost_alpha
        if abs(alpha_diff) > 1:
            circle.ghost_alpha += alpha_diff * transition_speed
        else:
            circle.ghost_alpha = circle.target_ghost_alpha

        # Apply smooth radius transition
        current_radius_mult = circle.base_radius / circle.base_ghost_radius if circle.base_ghost_radius > 0 else 1.0
        radius_diff = circle.target_radius_multiplier - current_radius_mult
        if abs(radius_diff) > 0.01:
            new_radius_mult = current_radius_mult + radius_diff * transition_speed
            circle.base_radius = circle.base_ghost_radius * new_radius_mult
        else:
            circle.base_radius = circle.base_ghost_radius * circle.target_radius_multiplier

        # Ensure alpha stays within bounds
        circle.ghost_alpha = max(min_alpha, min(255, circle.ghost_alpha))

    if circle.type.name == 'SHOOTER':
        # Shooter behavior - fire triangles when player gets close
        current_time = pygame.time.get_ticks()
        distance_to_mouse = math.sqrt((circle.x - mouse_x) ** 2 + (circle.y - mouse_y) ** 2)
        
        # Check if shooter should go invisible after delay
        if (not hasattr(circle, 'is_invisible') or not circle.is_invisible) and hasattr(circle, 'shot_fired_time') and circle.shot_fired_time > 0:
            # Check if visibility delay has passed
            if current_time - circle.shot_fired_time >= circle.visibility_after_shot:
                # Go invisible now
                circle.is_invisible = True
                circle.invisibility_start_time = current_time
                circle.invisibility_duration = random.randint(2000, 4000)  # 2-4 seconds
                circle.shot_fired_time = 0  # Reset
        
        # Handle invisibility state
        if hasattr(circle, 'is_invisible') and circle.is_invisible:
            # Check if invisibility duration has ended and all triangles are gone
            if (current_time - circle.invisibility_start_time >= circle.invisibility_duration and
                (not hasattr(circle, 'active_triangles') or len(circle.active_triangles) == 0)):
                # Become visible again and teleport
                circle.is_invisible = False
                circle.needs_teleport = True
        
        # Handle teleportation when becoming visible
        if hasattr(circle, 'needs_teleport') and circle.needs_teleport:
            import game_config
            if game_config.GAME_INSTANCE is not None:
                # Teleport to random location
                margin = circle.radius + 20
                circle.x = random.uniform(margin, game_config.GAME_INSTANCE.screen_width - margin)
                circle.y = random.uniform(margin, game_config.GAME_INSTANCE.screen_height - margin)
                circle.needs_teleport = False
        
        # Clean up any triangles that no longer exist in the game
        if hasattr(circle, 'active_triangles'):
            import game_config
            if game_config.GAME_INSTANCE is not None and hasattr(game_config.GAME_INSTANCE, 'triangles'):
                # Remove triangles from our tracking list if they're no longer in the game
                circle.active_triangles = [t for t in circle.active_triangles if t in game_config.GAME_INSTANCE.triangles]
        
        # Handle spin down when player is out of range
        if distance_to_mouse > circle.detection_range and circle.is_spinning:
            circle.is_spinning = False
            circle.spin_speed = 0
        
        # Handle spin animation when player is in range
        if distance_to_mouse <= circle.detection_range:
            # Set spin-up time based on difficulty if not already set
            if not hasattr(circle, 'current_difficulty'):
                import game_config
                if game_config.GAME_INSTANCE is not None:
                    circle.current_difficulty = game_config.GAME_INSTANCE.difficulty
                    # Apply difficulty-based spin-up time
                    if hasattr(circle, 'base_spin_up_time') and hasattr(circle, 'difficulty_spin_mult'):
                        circle.spin_up_time = int(circle.base_spin_up_time * 
                                               circle.difficulty_spin_mult.get(circle.current_difficulty, 1.0))
            
            # Start spinning up if not already spinning
            if not circle.is_spinning:
                circle.is_spinning = True
                circle.spin_start_time = current_time
            
            # Calculate spin speed based on time since spin start (ease-in effect)
            spin_progress = min(1.0, (current_time - circle.spin_start_time) / circle.spin_up_time)
            circle.spin_speed = circle.max_spin_speed * spin_progress
            
            # Update spin angle based on current speed
            circle.spin_angle += circle.spin_speed
            # Keep angle in 0-2π range to prevent floating point overflow
            circle.spin_angle %= 2 * math.pi
            
            # Check if we should fire (only if fully spun up and cooldown is done)
            if (not hasattr(circle, 'is_invisible') or not circle.is_invisible) and \
               current_time - circle.last_shot_time >= circle.shot_cooldown and \
               (not hasattr(circle, 'active_triangles') or len(circle.active_triangles) == 0) and \
               spin_progress >= 1.0:  # Only fire when fully spun up
                
                # Fire triangles in all directions
                import game_config
                if game_config.GAME_INSTANCE is not None:
                    triangle_count = random.randint(5, 9)  # Random number of triangles
                    angle_step = (2 * math.pi) / triangle_count
                    
                    for i in range(triangle_count):
                        angle = i * angle_step + random.uniform(-0.2, 0.2)  # Add slight randomness
                        base_speed = random.uniform(1.5, 2.5) * circle.scale_factor  # Base speed
                        
                        # Apply difficulty-based speed multiplier
                        from circle import Difficulty
                        difficulty_speed_mult = {
                            Difficulty.EASY: 1.0,
                            Difficulty.MEDIUM: 1.2,
                            Difficulty.HARD: 1.4,
                            Difficulty.NIGHTMARE: 1.6
                        }
                        
                        speed_multiplier = 1.0
                        if game_config.GAME_INSTANCE is not None:
                            current_difficulty = game_config.GAME_INSTANCE.difficulty
                            speed_multiplier = difficulty_speed_mult.get(current_difficulty, 1.0)
                        
                        speed = base_speed * speed_multiplier
                        
                        vx = math.cos(angle) * speed
                        vy = math.sin(angle) * speed
                        
                        # Create triangle projectile with shooter reference and size variation
                        from circle import Triangle
                        size_variation = random.uniform(1.0, 1.2)  # 100-120% size variation
                        triangle = Triangle(circle.x, circle.y, vx, vy, circle.scale_factor, shooter=circle, size_variation=size_variation)
                        
                        # Add to game instance triangles list
                        if not hasattr(game_config.GAME_INSTANCE, 'triangles'):
                            game_config.GAME_INSTANCE.triangles = []
                        game_config.GAME_INSTANCE.triangles.append(triangle)
                        
                        # Track this triangle in the shooter's active list
                        if not hasattr(circle, 'active_triangles'):
                            circle.active_triangles = []
                    circle.active_triangles.append(triangle)
                
                circle.last_shot_time = current_time
                circle.has_fired = True
                # Reset spinning after firing
                circle.is_spinning = False
                circle.spin_speed = 0
                
                # Set visibility delay based on difficulty
                import game_config
                if game_config.GAME_INSTANCE is not None:
                    difficulty = game_config.GAME_INSTANCE.difficulty
                    if difficulty == 'Easy':
                        circle.visibility_after_shot = 3000  # 3 seconds
                    elif difficulty == 'Medium':
                        circle.visibility_after_shot = 2500  # 2.5 seconds
                    elif difficulty == 'Hard':
                        circle.visibility_after_shot = 2000  # 2 seconds
                    else:  # Nightmare
                        circle.visibility_after_shot = 1500  # 1.5 seconds
                else:
                    circle.visibility_after_shot = 3000  # Default to easy
                
                # Record when shot was fired (will go invisible after delay)
                circle.shot_fired_time = current_time

    elif circle.type.name == 'HEXAGON':
        # Hexagon behavior - complex interactions
        _update_hexagon_behavior(circle, mouse_pos)

    # Handle tank glow animation
    if (circle.type.name == 'TANK' and circle.is_glowing_tank) or circle.type.name == 'SUPERTANK':
        circle.glow_pulse_timer += 1
        # Create a pulsing glow effect
        pulse_speed = 0.1 * (circle.target_fps / 60)  # Scale with FPS
        circle.glow_alpha = int(128 + 127 * math.sin(circle.glow_pulse_timer * pulse_speed))

    # Handle supertank regeneration
    if circle.type.name == 'SUPERTANK' and hasattr(circle, 'last_clicked_time'):
        current_time = pygame.time.get_ticks() / 1000.0  # Convert to seconds
        
        # Check if we should start regenerating
        if circle.last_clicked_time > 0 and (current_time - circle.last_clicked_time) >= circle.regen_cooldown:
            if not circle.regen_active and circle.health < circle.max_health:
                circle.regen_active = True
                circle.regen_timer = current_time
            circle.last_clicked_time = 0  # Reset the click timer
        
        # Continue regenerating if active
        if circle.regen_active and circle.health < circle.max_health:
            if (current_time - circle.regen_timer) >= circle.regen_rate:
                circle.health = min(circle.max_health, circle.health + 1)
                circle.regen_timer = current_time
                # Stop regenerating if fully healed
                if circle.health >= circle.max_health:
                    circle.regen_active = False
    
    # Handle self-destruct sequence for supertank
    if circle.type.name == 'SUPERTANK' and hasattr(circle, 'self_destruct_active') and circle.self_destruct_active:
        circle.self_destruct_timer += 1
        
        # Calculate progress (0 to 1)
        progress = circle.self_destruct_timer / circle.self_destruct_duration
        
        # Accelerating beep frequency
        # Start at 1 second intervals, accelerate to 0.1 second intervals
        max_interval = 60  # 1 second at 60fps
        min_interval = 6   # 0.1 second at 60fps
        current_interval = max_interval - (max_interval - min_interval) * progress
        circle.beep_interval = max(min_interval, int(current_interval))
        
        # Play beep sound at intervals
        if circle.self_destruct_timer - circle.last_beep_time >= circle.beep_interval:
            from game_config import BEEP_SOUND, play_sound
            play_sound(BEEP_SOUND, 'effects')
            circle.last_beep_time = circle.self_destruct_timer
        
        # Check if self-destruct is complete
        if circle.self_destruct_timer >= circle.self_destruct_duration:
            # Explode! Damage player and create visual explosion effect
            import game_config
            from game_config import play_sound, EXPLOSION_SOUND
            if game_config.GAME_INSTANCE is not None:
                game_config.GAME_INSTANCE.lives -= 1
                # Trigger explosion screen flash effect (orange/yellow flash)
                game_config.GAME_INSTANCE.trigger_explosion_flash()
                # Play explosion sound
                play_sound(EXPLOSION_SOUND, 'effects')
            # Mark circle for removal
            circle.dying = True
            return True  # Indicate explosion occurred

    circle.radius = circle.base_radius * circle.scale_factor

    # Apply movement patterns
    _apply_movement_patterns(circle, mouse_pos, screen_width, screen_height)

    return False  # Not dead

def _update_hexagon_behavior(circle, mouse_pos):
    """Handle complex hexagon behavior"""
    mouse_x, mouse_y = mouse_pos
    dx = circle.x - mouse_x
    dy = circle.y - mouse_y
    distance_to_mouse = math.sqrt(dx * dx + dy * dy)

    # Calculate proximity factor for hollow transition
    if distance_to_mouse <= circle.min_distance:
        proximity_factor = 1.0
    elif distance_to_mouse >= circle.proximity_threshold:
        proximity_factor = 0.0
    else:
        proximity_factor = 1.0 - (distance_to_mouse - circle.min_distance) / (circle.proximity_threshold - circle.min_distance)

    # Calculate target alpha based on proximity
    min_alpha = 15
    max_alpha = 255

    # Apply difficulty-based exponential curve
    difficulty_curve_exponent = {
        1: 0.7,      # EASY
        2: 1.0,      # MEDIUM
        3: 1.3,      # HARD
        4: 1.6       # NIGHTMARE
    }

    round_curve_bonus = (circle.round_num - 8) * 0.02
    round_curve_bonus = max(0, min(0.3, round_curve_bonus))

    final_exponent = difficulty_curve_exponent[circle.difficulty.value] + round_curve_bonus
    circle.target_alpha = max_alpha - (proximity_factor ** final_exponent) * (max_alpha - min_alpha)

    # Smooth alpha transition
    alpha_diff = circle.target_alpha - circle.hollow_alpha
    if abs(alpha_diff) > 1:
        circle.hollow_alpha += alpha_diff * circle.hollow_transition_speed
    else:
        circle.hollow_alpha = circle.target_alpha

    circle.hollow_alpha = max(min_alpha, min(max_alpha, circle.hollow_alpha))

    # Growth mechanic for growing hexagons
    if hasattr(circle, 'is_growing_hexagon') and circle.is_growing_hexagon:
        _handle_hexagon_growth(circle, proximity_factor)

    # Random behavior patterns
    _handle_hexagon_random_behavior(circle)

    # Expanding hexagon behavior
    if hasattr(circle, 'is_expanding_hexagon') and circle.is_expanding_hexagon:
        _handle_expanding_hexagon(circle, distance_to_mouse)

    # Update filled state
    _update_hexagon_filled_state(circle)

def _handle_hexagon_growth(circle, proximity_factor):
    """Handle growing hexagon behavior"""
    if proximity_factor > 0.05:
        growth_factor = min(proximity_factor * 2.0, 1.0)
        max_growth_multiplier = {
            1: 1.5,  # EASY
            2: 2.0,  # MEDIUM
            3: 2.5,  # HARD
            4: 3.0   # NIGHTMARE
        }
        max_growth = max_growth_multiplier[circle.difficulty.value]
        circle.target_growth_multiplier = 1.0 + growth_factor * (max_growth - 1.0)
    else:
        circle.target_growth_multiplier = 1.0

    # Smooth growth transition
    growth_diff = circle.target_growth_multiplier - circle.growth_multiplier
    if abs(growth_diff) > 0.01:
        circle.growth_multiplier += growth_diff * circle.growth_transition_speed
    else:
        circle.growth_multiplier = circle.target_growth_multiplier

    # Update radius for normal and random_pulse hexagons
    if circle.random_growth_behavior != 'random_size':
        if circle.random_growth_behavior == 'normal':
            circle.radius = circle.base_hexagon_radius * circle.growth_multiplier
        elif circle.random_growth_behavior == 'random_pulse':
            base_size = circle.base_hexagon_radius * circle.growth_multiplier
            circle.radius = max(circle.radius, base_size)

def _handle_hexagon_random_behavior(circle):
    """Handle random behavior patterns for hexagons"""
    circle.behavior_timer += 1
    if circle.behavior_timer >= circle.behavior_interval:
        circle.behavior_timer = 0
        circle.behavior_interval = random.randint(60, 180)

        if circle.random_growth_behavior == 'random_pulse':
            circle.random_target_size = random.uniform(0.6, 2.2)
        elif circle.random_growth_behavior == 'random_size':
            circle.random_target_size = random.uniform(0.4, 2.5)
        elif circle.random_growth_behavior == 'random_hollow':
            circle.random_target_alpha = random.choice([30, 80, 120, 180, 255])

    # Apply random behaviors
    if circle.random_growth_behavior == 'random_pulse':
        current_size = circle.radius / circle.base_hexagon_radius
        size_diff = circle.random_target_size - current_size
        if abs(size_diff) > 0.02:
            mouse_growth_size = circle.base_hexagon_radius * circle.growth_multiplier
            random_size = circle.base_hexagon_radius * circle.random_target_size
            target_size = max(mouse_growth_size, random_size)
            current_radius_diff = target_size - circle.radius
            circle.radius += current_radius_diff * 0.04

    elif circle.random_growth_behavior == 'random_size':
        current_size = circle.radius / circle.base_hexagon_radius
        size_diff = circle.random_target_size - current_size
        if abs(size_diff) > 0.02:
            circle.radius += size_diff * 0.06 * circle.base_hexagon_radius

    elif circle.random_growth_behavior == 'random_hollow':
        alpha_diff = circle.random_target_alpha - circle.hollow_alpha
        if abs(alpha_diff) > 2:
            circle.hollow_alpha += alpha_diff * 0.08
        else:
            circle.hollow_alpha = circle.random_target_alpha

        circle.is_filled = circle.hollow_alpha > 120

        # Still allow mouse proximity growth for random_hollow hexagons
        if hasattr(circle, 'is_growing_hexagon') and circle.is_growing_hexagon:
            # Apply proximity-based growth calculation here if needed
            pass

def _handle_expanding_hexagon(circle, distance_to_mouse):
    """Handle expanding hexagon behavior"""
    expand_trigger_distance = 120 * circle.scale_factor

    if distance_to_mouse < expand_trigger_distance and circle.expansion_phase == 'expanding':
        proximity_factor = max(0, 1.0 - (distance_to_mouse / expand_trigger_distance))

        if hasattr(circle, 'expansion_type') and circle.expansion_type == 'fast':
            expansion_rate = circle.expansion_speed * (1.0 + proximity_factor * 3.0)
        else:
            expansion_rate = circle.expansion_speed * (1.0 + proximity_factor * 1.5)

        circle.expansion_progress += expansion_rate

        if circle.expansion_progress >= 1.0:
            circle.expansion_progress = 1.0
            circle.expansion_phase = 'hollowing'
            circle.hollow_timer = 0

        circle.scale_factor = circle.base_scale + (circle.max_expansion - circle.base_scale) * circle.expansion_progress

    elif circle.expansion_phase == 'hollowing':
        if hasattr(circle, 'expansion_type') and circle.expansion_type == 'fast':
            hollowing_rate = circle.hollow_speed * 2.0
        else:
            hollowing_rate = circle.hollow_speed * 0.7

        circle.hollow_timer += hollowing_rate
        if circle.hollow_timer >= 1.0:
            circle.hollow_timer = 1.0
            circle.expansion_phase = 'hollow_cooldown'
            circle.reset_cooldown = circle.reset_cooldown_duration

        circle.hollow_alpha = int(255 * (1.0 - circle.hollow_timer))
        circle.is_filled = circle.hollow_alpha > 50

    elif circle.expansion_phase == 'hollow_cooldown':
        if distance_to_mouse >= expand_trigger_distance * 1.2:
            circle.reset_cooldown -= 1
            if circle.reset_cooldown <= 0:
                circle.expansion_phase = 'expanding'
                circle.expansion_progress = 0.0
                circle.scale_factor = circle.base_scale
                circle.hollow_alpha = 255
                circle.is_filled = True
                circle.reset_cooldown_duration = random.randint(120, 360)
        else:
            circle.reset_cooldown = circle.reset_cooldown_duration

        circle.hollow_alpha = 30
        circle.is_filled = False

    elif distance_to_mouse >= expand_trigger_distance * 1.5 and circle.expansion_phase == 'expanding' and circle.expansion_progress < 0.3:
        circle.expansion_progress -= circle.expansion_speed * 0.5
        if circle.expansion_progress <= 0:
            circle.expansion_progress = 0
            circle.scale_factor = circle.base_scale

def _update_hexagon_filled_state(circle):
    """Update hexagon filled state based on alpha"""
    base_alpha_threshold = 200
    difficulty_threshold_reduction = {
        1: -20,  # EASY
        2: 0,    # MEDIUM
        3: 20,   # HARD
        4: 40    # NIGHTMARE
    }

    round_threshold_increase = (circle.round_num - 8) * 2
    round_threshold_increase = max(0, min(25, round_threshold_increase))

    final_threshold = base_alpha_threshold - difficulty_threshold_reduction[circle.difficulty.value] + round_threshold_increase
    final_threshold = max(160, final_threshold)

    circle.is_filled = circle.hollow_alpha > final_threshold

def _apply_movement_patterns(circle, mouse_pos, screen_width, screen_height):
    """Apply movement patterns and handle different circle types"""
    if circle.type.name == 'HEXAGON':
        _handle_hexagon_movement(circle, mouse_pos)
    elif circle.type.name == 'CURSOR_GRABBER':
        _handle_cursor_grabber_movement(circle, mouse_pos, screen_width, screen_height)
    elif circle.type.name == 'SNAKE':
        _handle_snake_movement(circle, mouse_pos, screen_width, screen_height)
    else:
        _handle_standard_movement(circle, mouse_pos, screen_width, screen_height)

def _handle_hexagon_movement(circle, mouse_pos):
    """Handle hexagon movement patterns"""
    mouse_x, mouse_y = mouse_pos
    follow_activation_distance = 100 * circle.scale_factor

    dx = circle.x - mouse_x
    dy = circle.y - mouse_y
    distance = math.sqrt(dx * dx + dy * dy)

    # Follow mouse behavior
    if distance < follow_activation_distance and distance > 8:
        base_follow_strength = 3 * circle.scale_factor
        follow_strength_multiplier = {
            1: 0.8,  # EASY
            2: 1.0,  # MEDIUM
            3: 1.3,  # HARD
            4: 1.6   # NIGHTMARE
        }
        follow_strength = base_follow_strength * follow_strength_multiplier[circle.difficulty.value]

        follow_x = (-dx / distance) * follow_strength
        follow_y = (-dy / distance) * follow_strength

        follow_intensity = {
            1: 0.04,  # EASY
            2: 0.05,  # MEDIUM
            3: 0.07,  # HARD
            4: 0.09   # NIGHTMARE
        }

        intensity = follow_intensity[circle.difficulty.value]

        wander_while_following = 0.08 * circle.scale_factor
        random_x = random.uniform(-wander_while_following, wander_while_following)
        random_y = random.uniform(-wander_while_following, wander_while_following)

        circle.vx += follow_x * intensity + random_x
        circle.vy += follow_y * intensity + random_y
    elif distance <= 8:
        tiny_wander = 0.05 * circle.scale_factor
        circle.vx += random.uniform(-tiny_wander, tiny_wander)
        circle.vy += random.uniform(-tiny_wander, tiny_wander)
    else:
        distant_wander = 0.12 * circle.scale_factor
        circle.vx += random.uniform(-distant_wander, distant_wander)
        circle.vy += random.uniform(-distant_wander, distant_wander)

    # Update position
    circle.x += circle.vx
    circle.y += circle.vy

    # Apply screen boundary constraints to prevent going off-screen
    # Get screen dimensions from game instance if available
    screen_width = getattr(circle, 'screen_width', 800)  # Default fallback
    screen_height = getattr(circle, 'screen_height', 600)  # Default fallback
    
    # Try to get actual screen dimensions from game config
    import game_config
    if game_config.GAME_INSTANCE is not None:
        screen_width = game_config.GAME_INSTANCE.screen_width
        screen_height = game_config.GAME_INSTANCE.screen_height
    
    # Keep hexagon within screen bounds (with radius buffer)
    radius_buffer = circle.radius + 5  # Small buffer to keep fully on screen
    
    if circle.x - radius_buffer < 0:
        circle.x = radius_buffer
        circle.vx = abs(circle.vx) * 0.5  # Bounce back with reduced velocity
    elif circle.x + radius_buffer > screen_width:
        circle.x = screen_width - radius_buffer
        circle.vx = -abs(circle.vx) * 0.5  # Bounce back with reduced velocity
        
    if circle.y - radius_buffer < 0:
        circle.y = radius_buffer
        circle.vy = abs(circle.vy) * 0.5  # Bounce back with reduced velocity
    elif circle.y + radius_buffer > screen_height:
        circle.y = screen_height - radius_buffer
        circle.vy = -abs(circle.vy) * 0.5  # Bounce back with reduced velocity

    # Apply velocity damping
    circle.vx *= 0.98
    circle.vy *= 0.98

def _handle_cursor_grabber_movement(circle, mouse_pos, screen_width, screen_height):
    """Handle cursor grabber movement and behavior"""
    mouse_x, mouse_y = mouse_pos
    dx = mouse_x - circle.x
    dy = mouse_y - circle.y
    distance_to_mouse = math.sqrt(dx * dx + dy * dy)
    current_time = pygame.time.get_ticks() / 1000.0

    if not circle.is_grabbing:
        if circle.wait_start_time == 0:
            circle.wait_start_time = current_time

        if not circle.is_stalking and (current_time - circle.wait_start_time) < circle.wait_time:
            # Normal movement patterns while waiting
            _apply_standard_mouse_avoidance(circle, mouse_pos)
            _apply_movement_pattern_behavior(circle, mouse_pos)
        elif not circle.is_stalking:
            # Check for other active cursor grabbers
            other_grabber_active = False
            if hasattr(circle, '_game_circles_ref'):
                for other_circle in circle._game_circles_ref:
                    if (other_circle != circle and
                        other_circle.type.name == 'CURSOR_GRABBER' and
                        (other_circle.is_grabbing or (hasattr(other_circle, 'is_stalking') and
                         hasattr(other_circle, 'will_attack') and
                         other_circle.is_stalking and other_circle.will_attack))):
                        other_grabber_active = True
                        break

            if other_grabber_active:
                circle.wait_time = random.uniform(1.0, 3.0)
                circle.wait_start_time = current_time
            else:
                circle.is_stalking = True
                circle.stalk_start_time = current_time
                if random.random() < 0.7:
                    circle.will_attack = True
                else:
                    circle.will_attack = False
                    circle.wait_time = random.uniform(2.0, 5.0)
                    circle.wait_start_time = current_time
                    circle.is_stalking = False

        elif circle.is_stalking and circle.will_attack:
            # Attack mode - move aggressively toward cursor
            if distance_to_mouse > 0:
                move_speed = circle.speed * circle.seek_speed_multiplier * 3
                attack_force = move_speed * 0.15
                circle.vx = (dx / distance_to_mouse) * attack_force
                circle.vy = (dy / distance_to_mouse) * attack_force

            # Wind-up: must remain in range for a short delay before grab engages
            if distance_to_mouse <= circle.grab_distance:
                # Initialize pre-grab timer on first entry
                if not hasattr(circle, 'pre_grab_start_time'):
                    circle.pre_grab_start_time = 0
                if not hasattr(circle, 'pre_grab_delay'):
                    # Fallback delay if not set on the circle (defaults to Medium)
                    circle.pre_grab_delay = 0.5

                if circle.pre_grab_start_time == 0:
                    circle.pre_grab_start_time = current_time
                # If stayed in range long enough, engage grab
                elif (current_time - circle.pre_grab_start_time) >= circle.pre_grab_delay:
                    circle.is_grabbing = True
                    circle.grab_start_time = current_time
                    circle.grab_offset_x = random.uniform(-5, 5)
                    circle.grab_offset_y = random.uniform(-5, 5)
                    circle.color = (255, 100, 100)
                    circle.show_taunt_text = True
                    circle.taunt_alpha = 255
                    # Reset pre-grab timer for any future cycles
                    circle.pre_grab_start_time = 0
            else:
                # Out of range: reset wind-up timer
                if hasattr(circle, 'pre_grab_start_time'):
                    circle.pre_grab_start_time = 0
    else:
        # Grabbing behavior
        current_time = pygame.time.get_ticks() / 1000.0
        grab_time_elapsed = current_time - circle.grab_start_time

        # Chaotic movement while grabbing
        movement_speed = circle.speed * 1.5
        wave1 = math.sin(grab_time_elapsed * 3) * 1.8
        wave2 = math.cos(grab_time_elapsed * 4) * 1.5
        wave3 = math.sin(grab_time_elapsed * 2) * 1.0

        jitter_x = random.uniform(-1, 1)
        jitter_y = random.uniform(-1, 1)

        circle.x += (wave1 + jitter_x) * movement_speed
        circle.y += (wave2 + wave3 + jitter_y) * movement_speed

        # Keep within bounds
        circle.x = max(circle.radius + 20, min(screen_width - circle.radius - 20, circle.x))
        circle.y = max(circle.radius + 20, min(screen_height - circle.radius - 20, circle.y))

        # Set cursor target position
        circle.cursor_target_x = circle.x
        circle.cursor_target_y = circle.y

        # Fade taunt text
        if circle.show_taunt_text:
            circle.taunt_alpha -= circle.taunt_fade_speed
            if circle.taunt_alpha <= 0:
                circle.show_taunt_text = False
                circle.taunt_alpha = 0

        # Check if grab duration is over
        if grab_time_elapsed >= circle.grab_duration:
            circle.is_grabbing = False
            from circle import CircleType
            circle.type = CircleType.NORMAL  # Change to NORMAL type
            circle.color = RED
            circle.points = 10
            circle.vx = random.uniform(-1, 1)
            circle.vy = random.uniform(-1, 1)

    # Apply movement updates when not grabbing
    if not circle.is_grabbing:
        circle.x += circle.vx
        circle.y += circle.vy
        circle.vx *= 0.98
        circle.vy *= 0.98

        # Boundary bouncing
        if circle.x <= circle.radius or circle.x >= screen_width - circle.radius:
            circle.vx *= -0.8
            circle.x = max(circle.radius, min(screen_width - circle.radius, circle.x))
        if circle.y <= circle.radius or circle.y >= screen_height - circle.radius:
            circle.vy *= -0.8
            circle.y = max(circle.radius, min(screen_height - circle.radius, circle.y))

def _handle_snake_movement(circle, mouse_pos, screen_width, screen_height):
    """Handle snake movement and behavior"""
    mouse_x, mouse_y = mouse_pos

    # Calculate distance to mouse (check both head and segments)
    dx_mouse_head = circle.x - mouse_x
    dy_mouse_head = circle.y - mouse_y
    distance_to_mouse_head = math.sqrt(dx_mouse_head * dx_mouse_head + dy_mouse_head * dy_mouse_head)

    min_distance_to_mouse = distance_to_mouse_head
    if len(circle.segments) > 0:
        for segment in circle.segments:
            if len(circle.segments) - circle.segments_killed > 0:
                seg_x, seg_y = segment
                dx_seg = seg_x - mouse_x
                dy_seg = seg_y - mouse_y
                dist_to_seg = math.sqrt(dx_seg * dx_seg + dy_seg * dy_seg)
                min_distance_to_mouse = min(min_distance_to_mouse, dist_to_seg)

    # Update proximity-triggered boost system with cooldown
    circle.update_boost_system(min_distance_to_mouse)

    # Calculate current speed with boost
    current_speed = circle.speed
    if circle.speed_boost_timer > 0:
        current_speed *= 1.8

    # Movement-based corner detection - detect when snake is stuck or moving erratically
    corner_escape_active = False
    
    # Initialize movement tracking attributes
    if not hasattr(circle, 'position_history'):
        circle.position_history = []
    if not hasattr(circle, 'movement_distances'):
        circle.movement_distances = []
    if not hasattr(circle, 'direction_changes'):
        circle.direction_changes = []
    if not hasattr(circle, 'last_direction'):
        circle.last_direction = (circle.direction_x, circle.direction_y)
    if not hasattr(circle, 'corner_escape_timer'):
        circle.corner_escape_timer = 0
    if not hasattr(circle, 'escape_ignore_cursor_timer'):
        circle.escape_ignore_cursor_timer = 0
    if not hasattr(circle, 'stuck_threshold_timer'):
        circle.stuck_threshold_timer = 0

    # Track current position
    current_pos = (circle.x, circle.y)
    circle.position_history.append(current_pos)
    
    # Keep only last 30 positions (0.5 seconds at 60fps)
    if len(circle.position_history) > 30:
        circle.position_history.pop(0)
    
    # Calculate movement distance from last frame
    if len(circle.position_history) >= 2:
        last_pos = circle.position_history[-2]
        movement_dist = math.sqrt((current_pos[0] - last_pos[0])**2 + (current_pos[1] - last_pos[1])**2)
        circle.movement_distances.append(movement_dist)
        
        # Keep only last 20 movement distances
        if len(circle.movement_distances) > 20:
            circle.movement_distances.pop(0)
    
    # Track direction changes (erratic movement)
    current_direction = (circle.direction_x, circle.direction_y)
    if circle.last_direction:
        # Calculate angle difference between current and last direction
        dot_product = (current_direction[0] * circle.last_direction[0] + 
                      current_direction[1] * circle.last_direction[1])
        # Clamp dot product to avoid math domain errors
        dot_product = max(-1, min(1, dot_product))
        angle_diff = math.acos(abs(dot_product))
        circle.direction_changes.append(angle_diff)
        
        # Keep only last 15 direction changes
        if len(circle.direction_changes) > 15:
            circle.direction_changes.pop(0)
    
    circle.last_direction = current_direction
    
    # Detect if snake is cornered based on movement patterns
    is_cornered = False
    
    if len(circle.movement_distances) >= 10 and len(circle.direction_changes) >= 10:
        # Check for low movement (stuck)
        avg_movement = sum(circle.movement_distances[-10:]) / 10
        low_movement = avg_movement < current_speed * 0.3  # Moving less than 30% of expected speed
        
        # Check for erratic movement (frequent direction changes)
        recent_direction_changes = circle.direction_changes[-10:]
        large_changes = sum(1 for change in recent_direction_changes if change > 0.5)  # > ~30 degrees
        erratic_movement = large_changes >= 6  # 6 or more large direction changes in last 10 frames
        
        # Check if near screen edges (but don't require it)
        edge_margin = 80
        near_edge = (circle.x < edge_margin or circle.x > screen_width - edge_margin or 
                    circle.y < edge_margin or circle.y > screen_height - edge_margin)
        
        # Snake is cornered if it has low movement OR erratic movement (especially near edges)
        if low_movement or (erratic_movement and near_edge) or (erratic_movement and avg_movement < current_speed * 0.6):
            is_cornered = True
            circle.stuck_threshold_timer += 1
        else:
            circle.stuck_threshold_timer = max(0, circle.stuck_threshold_timer - 1)
    
    # Trigger corner escape if stuck for a few frames
    if is_cornered and circle.stuck_threshold_timer >= 3:
        corner_escape_active = True
        circle.corner_escape_timer += 1
    else:
        circle.corner_escape_timer = max(0, circle.corner_escape_timer - 1)
    
    # Decay escape ignore cursor timer
    if circle.escape_ignore_cursor_timer > 0:
        circle.escape_ignore_cursor_timer -= 1

    # Enhanced corner escape logic - PRIORITIZE OVER MOUSE AVOIDANCE
    if corner_escape_active:
        
        # Set ignore cursor timer when starting escape (2 seconds = 120 frames at 60fps)
        if circle.corner_escape_timer == 1:  # Just started escaping
            circle.escape_ignore_cursor_timer = 120
        
        # Always use aggressive escape when cornered
        if circle.corner_escape_timer > 3:
            # Use random direction toward center with some variation
            center_x = screen_width / 2
            center_y = screen_height / 2
            to_center_x = center_x - circle.x
            to_center_y = center_y - circle.y
            
            # Normalize and add some randomness
            length = math.sqrt(to_center_x**2 + to_center_y**2)
            if length > 0:
                to_center_x /= length
                to_center_y /= length
            
            # Add random component to avoid predictable movement
            random_angle = random.uniform(-math.pi/2, math.pi/2)  # ±90 degrees for more variation
            cos_r = math.cos(random_angle)
            sin_r = math.sin(random_angle)
            
            circle.direction_x = to_center_x * cos_r - to_center_y * sin_r
            circle.direction_y = to_center_x * sin_r + to_center_y * cos_r
            
            # Reset timer after escape attempt
            if circle.corner_escape_timer > 20:
                circle.corner_escape_timer = 0
                circle.stuck_threshold_timer = 0
        else:
            # Initial escape - pick a random direction away from current position
            escape_angle = random.uniform(0, 2 * math.pi)
            circle.direction_x = math.cos(escape_angle)
            circle.direction_y = math.sin(escape_angle)

        # Normalize direction
        dir_length = math.sqrt(circle.direction_x**2 + circle.direction_y**2)
        if dir_length > 0:
            circle.direction_x /= dir_length
            circle.direction_y /= dir_length

    # Mouse avoidance (only if not escaping corners AND not in ignore period)
    elif not corner_escape_active and circle.escape_ignore_cursor_timer == 0 and min_distance_to_mouse < circle.base_detection_range and min_distance_to_mouse > 0:
        avoid_strength = 1.2 if circle.speed_boost_timer > 0 else 0.8
        avoid_force = avoid_strength * (circle.base_detection_range - min_distance_to_mouse) / circle.base_detection_range

        avoid_x = (dx_mouse_head / distance_to_mouse_head) * avoid_force
        avoid_y = (dy_mouse_head / distance_to_mouse_head) * avoid_force

        blend_factor = 0.6 if circle.speed_boost_timer > 0 else 0.4
        circle.direction_x = circle.direction_x * (1 - blend_factor) + avoid_x * blend_factor
        circle.direction_y = circle.direction_y * (1 - blend_factor) + avoid_y * blend_factor

        dir_length = math.sqrt(circle.direction_x**2 + circle.direction_y**2)
        if dir_length > 0:
            circle.direction_x /= dir_length
            circle.direction_y /= dir_length

    # Regular movement patterns when not avoiding
    elif not corner_escape_active:
        _handle_snake_movement_patterns(circle)

    # Store old head position and move
    old_head_x = circle.x
    old_head_y = circle.y

    circle.x += circle.direction_x * current_speed
    circle.y += circle.direction_y * current_speed

    # Screen boundary handling with 30px margin - ALWAYS bounce for snakes, never wrap
    # Snakes should never teleport across screen and should bounce before hitting edge
    
    margin = 30
    
    if circle.x < margin:
        circle.x = margin
        circle.direction_x = abs(circle.direction_x)  # Bounce right
    elif circle.x > screen_width - margin:
        circle.x = screen_width - margin
        circle.direction_x = -abs(circle.direction_x)  # Bounce left
        
    if circle.y < margin:
        circle.y = margin
        circle.direction_y = abs(circle.direction_y)  # Bounce down
    elif circle.y > screen_height - margin:
        circle.y = screen_height - margin
        circle.direction_y = -abs(circle.direction_y)  # Bounce up

    # Update segments
    if len(circle.segments) > 0:
        prev_x, prev_y = old_head_x, old_head_y

        for i in range(len(circle.segments)):
            curr_seg_x, curr_seg_y = circle.segments[i]

            dx = prev_x - curr_seg_x
            dy = prev_y - curr_seg_y
            distance = math.sqrt(dx*dx + dy*dy)

            if distance > circle.segment_spacing:
                if distance > 0:
                    move_x = (dx / distance) * (distance - circle.segment_spacing)
                    move_y = (dy / distance) * (distance - circle.segment_spacing)
                    circle.segments[i][0] += move_x
                    circle.segments[i][1] += move_y

            prev_x, prev_y = curr_seg_x, curr_seg_y

def _handle_snake_movement_patterns(circle):
    """Handle snake movement patterns and AI"""
    # Update timers
    circle.turn_timer += 1
    if circle.erratic_mode_timer > 0:
        circle.erratic_mode_timer -= 1
    if circle.zigzag_mode:
        circle.zigzag_timer += 1

    # Circle mode
    if not circle.circle_mode and not circle.zigzag_mode and random.random() < 0.004:
        circle.circle_mode = True
        circle.circle_timer = 0
        circle.circle_duration = random.randint(120, 240)
        circle.circle_direction = random.choice([-1, 1])
        circle.circle_start_angle = math.atan2(circle.direction_y, circle.direction_x)

    # Zigzag mode
    elif not circle.circle_mode and not circle.zigzag_mode and random.random() < 0.005:
        circle.zigzag_mode = True
        circle.zigzag_timer = 0
        circle.zigzag_direction = random.choice([-1, 1])

    # Execute movement modes
    if circle.circle_mode:
        circle.circle_timer += 1
        circle_speed = 0.06
        angle_increment = circle_speed * circle.circle_direction
        current_angle = math.atan2(circle.direction_y, circle.direction_x)
        new_angle = current_angle + angle_increment

        circle.direction_x = math.cos(new_angle)
        circle.direction_y = math.sin(new_angle)

        if circle.circle_timer >= circle.circle_duration or random.random() < 0.005:
            circle.circle_mode = False
            circle.circle_timer = 0
            if random.random() < 0.3:
                circle.erratic_mode_timer = random.randint(60, 120)

    elif circle.zigzag_mode:
        if circle.zigzag_timer % random.randint(20, 30) == 0:
            circle.zigzag_direction *= -1

        zigzag_angle = 0.15 * circle.zigzag_direction
        current_angle = math.atan2(circle.direction_y, circle.direction_x)
        new_angle = current_angle + zigzag_angle
        target_x = math.cos(new_angle)
        target_y = math.sin(new_angle)

        circle.direction_x = circle.direction_x * 0.8 + target_x * 0.2
        circle.direction_y = circle.direction_y * 0.8 + target_y * 0.2

        dir_length = math.sqrt(circle.direction_x**2 + circle.direction_y**2)
        if dir_length > 0:
            circle.direction_x /= dir_length
            circle.direction_y /= dir_length

        if random.random() < 0.008:
            circle.zigzag_mode = False
            circle.zigzag_timer = 0

    # Erratic mode
    elif circle.erratic_mode_timer > 0:
        if random.random() < 0.08:
            angle_change = random.uniform(-0.6, 0.6)
            current_angle = math.atan2(circle.direction_y, circle.direction_x)
            new_angle = current_angle + angle_change

            target_x = math.cos(new_angle)
            target_y = math.sin(new_angle)

            circle.direction_x = circle.direction_x * circle.direction_change_smoothing + target_x * (1 - circle.direction_change_smoothing)
            circle.direction_y = circle.direction_y * circle.direction_change_smoothing + target_y * (1 - circle.direction_change_smoothing)

            dir_length = math.sqrt(circle.direction_x**2 + circle.direction_y**2)
            if dir_length > 0:
                circle.direction_x /= dir_length
                circle.direction_y /= dir_length

    # Normal wandering
    else:
        if circle.turn_timer >= circle.turn_interval:
            turn_type = random.choice(['small', 'medium', 'curve', 'S-curve'])

            if turn_type == 'small':
                angle_change = random.uniform(-0.3, 0.3)
            elif turn_type == 'medium':
                angle_change = random.uniform(-0.6, 0.6)
            elif turn_type == 'curve':
                angle_change = random.uniform(-0.9, 0.9)
            elif turn_type == 'S-curve':
                angle_change = random.uniform(-0.4, 0.4)
                current_angle = math.atan2(circle.direction_y, circle.direction_x)
                new_angle = current_angle + angle_change
                target_x = math.cos(new_angle)
                target_y = math.sin(new_angle)

                circle.direction_x = circle.direction_x * 0.7 + target_x * 0.3
                circle.direction_y = circle.direction_y * 0.7 + target_y * 0.3

                dir_length = math.sqrt(circle.direction_x**2 + circle.direction_y**2)
                if dir_length > 0:
                    circle.direction_x /= dir_length
                    circle.direction_y /= dir_length

            if turn_type != 'S-curve':
                current_angle = math.atan2(circle.direction_y, circle.direction_x)
                new_angle = current_angle + angle_change
                target_x = math.cos(new_angle)
                target_y = math.sin(new_angle)

                circle.direction_x = circle.direction_x * circle.direction_change_smoothing + target_x * (1 - circle.direction_change_smoothing)
                circle.direction_y = circle.direction_y * circle.direction_change_smoothing + target_y * (1 - circle.direction_change_smoothing)

                dir_length = math.sqrt(circle.direction_x**2 + circle.direction_y**2)
                if dir_length > 0:
                    circle.direction_x /= dir_length
                    circle.direction_y /= dir_length

            circle.turn_timer = 0
            circle.turn_interval = random.randint(30, 90)

            mode_roll = random.random()
            if mode_roll < 0.15:
                circle.erratic_mode_timer = random.randint(60, 120)
            elif mode_roll < 0.25:
                circle.zigzag_mode = True
                circle.zigzag_timer = 0

        elif random.random() < 0.04:
            micro_turn = random.uniform(-0.1, 0.1)
            current_angle = math.atan2(circle.direction_y, circle.direction_x)
            new_angle = current_angle + micro_turn
            target_x = math.cos(new_angle)
            target_y = math.sin(new_angle)

            circle.direction_x = circle.direction_x * 0.95 + target_x * 0.05
            circle.direction_y = circle.direction_y * 0.95 + target_y * 0.05

            dir_length = math.sqrt(circle.direction_x**2 + circle.direction_y**2)
            if dir_length > 0:
                circle.direction_x /= dir_length
                circle.direction_y /= dir_length

def _handle_standard_movement(circle, mouse_pos, screen_width, screen_height):
    """Handle standard circle movement with patterns"""
    _apply_standard_mouse_avoidance(circle, mouse_pos)
    _apply_movement_pattern_behavior(circle, mouse_pos)
    _apply_standard_physics(circle, screen_width, screen_height)

def _apply_standard_mouse_avoidance(circle, mouse_pos):
    """Apply mouse avoidance for standard circles"""
    # Skip mouse avoidance during corner escape erratic mode
    if hasattr(circle, 'corner_escape_timer') and circle.corner_escape_timer > 0:
        return
        
    mouse_x, mouse_y = mouse_pos
    dx_mouse = circle.x - mouse_x
    dy_mouse = circle.y - mouse_y
    distance_to_mouse = math.sqrt(dx_mouse * dx_mouse + dy_mouse * dy_mouse)

    # Apply mouse avoidance (except for EVASIVE and PREDICTIVE which handle it themselves)
    if (circle.movement_pattern.name not in ['EVASIVE', 'PREDICTIVE'] and
        distance_to_mouse < circle.avoid_distance and distance_to_mouse > 0):
        
        avoid_force = circle.avoid_strength * (circle.avoid_distance - distance_to_mouse) / circle.avoid_distance
        avoid_x = avoid_force * (dx_mouse / distance_to_mouse)
        avoid_y = avoid_force * (dy_mouse / distance_to_mouse)

        avoidance_strength = 0.3
        circle.vx += avoid_x * avoidance_strength
        circle.vy += avoid_y * avoidance_strength

def _apply_movement_pattern_behavior(circle, mouse_pos):
    """Apply specific movement pattern behaviors"""
    if circle.movement_pattern.name == 'WANDERING':
        # Use shared wandering movement with standard parameters
        wander_vx, wander_vy = _apply_wandering_movement(
            circle, 0.1, (-math.pi/3, math.pi/3), (60, 180),
            'wander_timer', 'wander_angle', 'wander_duration'
        )
        circle.vx += wander_vx
        circle.vy += wander_vy

    elif circle.movement_pattern.name == 'ZIGZAG':
        circle.zigzag_timer += 1
        if circle.zigzag_timer >= circle.zigzag_interval:
            circle.zigzag_angle += random.choice([math.pi/2, -math.pi/2, math.pi/3, -math.pi/3])
            circle.zigzag_timer = 0
            circle.zigzag_interval = random.randint(30, 90)

        speed_mult = circle.zigzag_speed_multiplier * 0.5
        circle.vx += math.cos(circle.zigzag_angle) * circle.speed * speed_mult
        circle.vy += math.sin(circle.zigzag_angle) * circle.speed * speed_mult

    # Add other movement patterns as needed...

def _apply_standard_physics(circle, screen_width, screen_height):
    """Apply standard physics to circle movement"""
    # Check for corner detection and handle erratic movement
    _handle_corner_escape(circle, screen_width, screen_height)
    
    # Limit velocity
    max_vel = circle.speed
    vel_magnitude = math.sqrt(circle.vx * circle.vx + circle.vy * circle.vy)
    if vel_magnitude > max_vel:
        circle.vx = (circle.vx / vel_magnitude) * max_vel
        circle.vy = (circle.vy / vel_magnitude) * max_vel

    # Anti-static mechanism
    min_velocity_threshold = 0.2 * circle.scale_factor
    if vel_magnitude < min_velocity_threshold:
        boost_strength = 0.3 * circle.scale_factor
        boost_x = random.uniform(-boost_strength, boost_strength)
        boost_y = random.uniform(-boost_strength, boost_strength)
        circle.vx += boost_x
        circle.vy += boost_y

    # Velocity damping
    velocity_damping = 0.995
    circle.vx *= velocity_damping
    circle.vy *= velocity_damping

    # Update position
    circle.x += circle.vx
    circle.y += circle.vy

    # Bounce off walls (weaker bouncing during corner escape)
    bounce_damping = 0.3 if hasattr(circle, 'corner_escape_timer') and circle.corner_escape_timer > 0 else 0.8
    
    if circle.x - circle.radius <= 0 or circle.x + circle.radius >= screen_width:
        circle.vx *= -bounce_damping
        circle.x = max(circle.radius, min(screen_width - circle.radius, circle.x))
    if circle.y - circle.radius <= 0 or circle.y + circle.radius >= screen_height:
        circle.vy *= -bounce_damping
        circle.y = max(circle.radius, min(screen_height - circle.radius, circle.y))

def _handle_corner_escape(circle, screen_width, screen_height):
    """Handle corner escape erratic movement for normal circles"""
    # Initialize corner escape timer if it doesn't exist
    if not hasattr(circle, 'corner_escape_timer'):
        circle.corner_escape_timer = 0
    
    # Use shared corner detection
    corner_info = _detect_corner_proximity(circle, screen_width, screen_height)
    
    # Start corner escape if in corner and not already escaping
    if corner_info['in_corner'] and circle.corner_escape_timer <= 0:
        # Randomize escape intensity - some escapes are more dramatic
        if random.random() < 0.3:  # 30% chance for intense escape
            circle.corner_escape_timer = 180  # 3 seconds
            circle.escape_intensity = 'intense'
        else:
            circle.corner_escape_timer = 120  # 2 seconds
            circle.escape_intensity = 'normal'
    
    # Apply corner escape movement
    if circle.corner_escape_timer > 0:
        # Get escape intensity (default to normal if not set)
        intensity = getattr(circle, 'escape_intensity', 'normal')
        
        # Different safe distances for different intensities
        if intensity == 'intense':
            safe_distance = 200 * circle.scale_factor  # Must go much further
        else:
            safe_distance = 120 * circle.scale_factor  # Normal distance
            
        far_from_edges = (circle.x > safe_distance and 
                         circle.x < screen_width - safe_distance and
                         circle.y > safe_distance and 
                         circle.y < screen_height - safe_distance)
        
        # Intense escapes don't exit early as often
        early_exit_chance = 1.0 if intensity == 'normal' else 0.7
        
        if far_from_edges and random.random() < early_exit_chance:
            # Exit escape mode when in safe area
            circle.corner_escape_timer = 0
        else:
            # Still escaping - apply escape forces based on intensity
            if intensity == 'intense':
                escape_strength = 4.0 * circle.scale_factor  # Much stronger
                velocity_boost = 1.6  # Bigger boost
            else:
                escape_strength = 2.5 * circle.scale_factor  # Normal strength
                velocity_boost = 1.3  # Normal boost
            
            # Push directly away from edges
            if corner_info['near_left']:
                circle.vx += escape_strength  # Push right
            if corner_info['near_right']:
                circle.vx -= escape_strength  # Push left
            if corner_info['near_top']:
                circle.vy += escape_strength  # Push down
            if corner_info['near_bottom']:
                circle.vy -= escape_strength  # Push up
            
            # Apply velocity boost
            circle.vx *= velocity_boost
            circle.vy *= velocity_boost
            
            # Decrease timer as fallback
            circle.corner_escape_timer -= 1

def draw_circle(circle, surface):
    """Draw circle with all visual effects"""
    if circle.dying:
        # Death animation - fade out
        alpha = 255 * (1 - circle.death_timer / circle.death_duration)
        color = (*circle.color, int(alpha))

        death_surface = pygame.Surface((circle.radius * 2, circle.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(death_surface, color, (circle.radius, circle.radius), int(circle.radius))
        surface.blit(death_surface, (circle.x - circle.radius, circle.y - circle.radius))
    else:
        # Choose drawing method based on circle type
        if circle.type.name == 'GHOST':
            _draw_ghost_circle(circle, surface)
        elif (circle.type.name == 'TANK' and circle.is_glowing_tank) or circle.type.name == 'SUPERTANK':
            _draw_glowing_tank(circle, surface)
        elif circle.type.name == 'HEXAGON':
            _draw_hexagon(circle, surface)
        elif circle.type.name == 'CURSOR_GRABBER':
            _draw_cursor_grabber(circle, surface)
        elif circle.type.name == 'SNAKE':
            _draw_snake(circle, surface)
        elif circle.type.name == 'SHOOTER':
            _draw_shooter_circle(circle, surface)
        else:
            _draw_standard_circle(circle, surface)

        # Draw health bar for all circles with multiple health points
        if circle.max_health > 1:
            _draw_health_bar(circle, surface)

def _draw_ghost_circle(circle, surface):
    """Draw ghost circle with alpha transparency"""
    ghost_surface = pygame.Surface((circle.radius * 2, circle.radius * 2), pygame.SRCALPHA)
    color_with_alpha = (*circle.color, circle.ghost_alpha)
    pygame.draw.circle(ghost_surface, color_with_alpha, (circle.radius, circle.radius), int(circle.radius))
    surface.blit(ghost_surface, (circle.x - circle.radius, circle.y - circle.radius))

def _draw_glowing_tank(circle, surface):
    """Draw tank with glow effects"""
    glow_radius = int(circle.radius * 1.5)
    glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)

    # Different glow effects based on tank type
    if circle.type.name == 'SUPERTANK':
        for i in range(6):
            glow_size = glow_radius - (i * 2)
            if glow_size > 0:
                glow_alpha = max(0, circle.glow_alpha - (i * 15))
                glow_color = (255, 50, 50, glow_alpha)
                pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_size)
    elif circle.is_hyper_tank:
        for i in range(4):
            glow_size = glow_radius - (i * 3)
            if glow_size > 0:
                glow_alpha = max(0, circle.glow_alpha - (i * 25))
                glow_color = (150, 200, 255, glow_alpha)
                pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_size)
    else:
        for i in range(3):
            glow_size = glow_radius - (i * 5)
            if glow_size > 0:
                glow_alpha = max(0, circle.glow_alpha - (i * 40))
                glow_color = (100, 150, 255, glow_alpha)
                pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_size)

    surface.blit(glow_surface, (circle.x - glow_radius, circle.y - glow_radius))
    pygame.draw.circle(surface, circle.color, (int(circle.x), int(circle.y)), int(circle.radius))
    
    # Draw self-destruct indicator for supertank
    if (circle.type.name == 'SUPERTANK' and hasattr(circle, 'self_destruct_active') and 
        circle.self_destruct_active):
        
        # Calculate progress and flashing
        progress = circle.self_destruct_timer / circle.self_destruct_duration
        
        # Flash frequency increases with progress
        flash_speed = 0.1 + (progress * 0.4)  # From 0.1 to 0.5
        flash_cycle = (pygame.time.get_ticks() * flash_speed / 1000.0) % 1.0
        
        # Only draw when flash is "on" (creates blinking effect)
        if flash_cycle < 0.5:
            # Center circle size (small)
            center_radius = max(3, int(circle.radius * 0.3))
            
            # Color changes from red to green as time progresses
            if progress < 0.83:  # Red for first 5 seconds (5/6 = 0.83)
                center_color = (255, 0, 0)  # Red
            else:  # Green in final second
                center_color = (0, 255, 0)  # Green
            
            # Draw the flashing center circle
            pygame.draw.circle(surface, center_color, (int(circle.x), int(circle.y)), center_radius)

def _draw_hexagon(circle, surface):
    """Draw hexagon with fill/hollow effects"""
    center = (int(circle.x), int(circle.y))
    radius = max(8, int(circle.radius))

    # Calculate hexagon vertices
    vertices = []
    for i in range(6):
        angle = (i * math.pi / 3) + (math.pi / 2)
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        vertices.append((x, y))

    if circle.is_filled:
        # Draw filled hexagon
        color_with_alpha = (*circle.color, int(circle.hollow_alpha))
        if circle.hollow_alpha < 255:
            hex_surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            local_vertices = [(x - center[0] + radius + 2, y - center[1] + radius + 2) for x, y in vertices]
            pygame.draw.polygon(hex_surface, color_with_alpha, local_vertices)
            surface.blit(hex_surface, (center[0] - radius - 2, center[1] - radius - 2))
        else:
            pygame.draw.polygon(surface, circle.color, vertices)
    else:
        # Draw hollow hexagon
        if hasattr(circle, 'is_expanding_hexagon') and circle.is_expanding_hexagon and hasattr(circle, 'thin_outline'):
            if circle.thin_outline:
                outline_thickness = max(1, int(2 * circle.scale_factor))
            else:
                outline_thickness = max(3, int(5 * circle.scale_factor))
        else:
            outline_thickness = max(3, int(5 * circle.scale_factor))

        if circle.hollow_alpha < 255:
            hex_surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            local_vertices = [(x - center[0] + radius + 2, y - center[1] + radius + 2) for x, y in vertices]
            color_with_alpha = (*circle.color, int(circle.hollow_alpha))
            pygame.draw.polygon(hex_surface, color_with_alpha, local_vertices, outline_thickness)
            surface.blit(hex_surface, (center[0] - radius - 2, center[1] - radius - 2))
        else:
            pygame.draw.polygon(surface, circle.color, vertices, outline_thickness)

def _draw_cursor_grabber(circle, surface):
    """Draw cursor grabber with special effects"""
    center = (int(circle.x), int(circle.y))
    radius = int(circle.radius)

    if circle.is_grabbing:
        # Pulsing glow when grabbing
        glow_radius = int(radius * 1.8)
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)

        pulse_intensity = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 100 + 50
        glow_color = (255, 100, 100, int(pulse_intensity))
        pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, (circle.x - glow_radius, circle.y - glow_radius))

        pygame.draw.circle(surface, circle.color, center, radius)

        # Draw "arms" reaching toward cursor
        mouse_x, mouse_y = pygame.mouse.get_pos()
        dx = mouse_x - circle.x
        dy = mouse_y - circle.y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0 and distance < 100:
            arm_length = min(radius * 2, distance)
            end_x = circle.x + (dx / distance) * arm_length
            end_y = circle.y + (dy / distance) * arm_length
            pygame.draw.line(surface, (255, 150, 150), center, (int(end_x), int(end_y)), 2)
    else:
        pygame.draw.circle(surface, circle.color, center, radius)

    # Draw taunt text when grabbing
    if circle.show_taunt_text and circle.taunt_alpha > 0:
        font = pygame.font.Font(None, int(48 * circle.scale_factor))
        text_surf = font.render("haha i got u", True, (255, 255, 255))
        alpha_surf = pygame.Surface(text_surf.get_size(), pygame.SRCALPHA)
        alpha_surf.set_alpha(max(0, min(255, int(circle.taunt_alpha))))
        alpha_surf.blit(text_surf, (0, 0))

        text_rect = alpha_surf.get_rect(center=(center[0], center[1] - radius - 30))
        surface.blit(alpha_surf, text_rect)

def _draw_snake(circle, surface):
    """Draw snake with head and segments"""
    head_center = (int(circle.x), int(circle.y))
    head_radius = int(circle.radius)

    # Rainbow effects for rainbow snakes
    if hasattr(circle, 'is_rainbow') and circle.is_rainbow:
        if hasattr(circle, 'rainbow_timer'):
            circle.rainbow_timer += 1
        else:
            circle.rainbow_timer = 0

        glow_radius = int(head_radius * 1.8)
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)

        time_factor = circle.rainbow_timer * 0.1
        r = int(127 + 127 * math.sin(time_factor))
        g = int(127 + 127 * math.sin(time_factor + 2))
        b = int(127 + 127 * math.sin(time_factor + 4))
        rainbow_glow = (r, g, b, 80)

        pygame.draw.circle(glow_surface, rainbow_glow, (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, (circle.x - glow_radius, circle.y - glow_radius))

    # Speed boost glow
    elif hasattr(circle, 'speed_boost_timer') and circle.speed_boost_timer > 0:
        glow_radius = int(head_radius * 1.6)
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)

        pulse_intensity = abs(math.sin(pygame.time.get_ticks() * 0.02)) * 80 + 40
        glow_color = (255, 255, 100, int(pulse_intensity))
        pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, (circle.x - glow_radius, circle.y - glow_radius))

    # Circle mode glow
    elif hasattr(circle, 'circle_mode') and circle.circle_mode:
        glow_radius = int(head_radius * 1.3)
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)

        spiral_intensity = abs(math.sin(pygame.time.get_ticks() * 0.01)) * 60 + 30
        glow_color = (100, 255, 100, int(spiral_intensity))
        pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, (circle.x - glow_radius, circle.y - glow_radius))

    pygame.draw.circle(surface, circle.color, head_center, head_radius)

    # Draw segments
    for i, segment in enumerate(circle.segments):
        if i >= len(circle.segments) - circle.segments_killed:
            continue

        seg_x, seg_y = segment
        seg_center = (int(seg_x), int(seg_y))
        seg_radius = max(int(head_radius * 0.8), 8)

        if hasattr(circle, 'is_rainbow') and circle.is_rainbow:
            time_factor = (circle.rainbow_timer + i * 20) * 0.1
            r = int(127 + 127 * math.sin(time_factor))
            g = int(127 + 127 * math.sin(time_factor + 2))
            b = int(127 + 127 * math.sin(time_factor + 4))
            segment_color = (r, g, b)
        else:
            segment_color = (0, 100, 0)

        pygame.draw.circle(surface, segment_color, seg_center, seg_radius)

        # Draw connections
        if i == 0:
            pygame.draw.line(surface, segment_color, head_center, seg_center, 3)
        else:
            prev_seg = circle.segments[i-1]
            prev_center = (int(prev_seg[0]), int(prev_seg[1]))
            pygame.draw.line(surface, segment_color, prev_center, seg_center, 3)

    # Draw eyes
    eye_offset = head_radius * 0.6
    eye_size = max(3, int(head_radius * 0.15))

    eye1_x = circle.x + circle.direction_x * eye_offset * 0.5 + circle.direction_y * eye_offset * 0.3
    eye1_y = circle.y + circle.direction_y * eye_offset * 0.5 - circle.direction_x * eye_offset * 0.3
    eye2_x = circle.x + circle.direction_x * eye_offset * 0.5 - circle.direction_y * eye_offset * 0.3
    eye2_y = circle.y + circle.direction_y * eye_offset * 0.5 + circle.direction_x * eye_offset * 0.3

    pygame.draw.circle(surface, (255, 255, 255), (int(eye1_x), int(eye1_y)), eye_size)
    pygame.draw.circle(surface, (255, 255, 255), (int(eye2_x), int(eye2_y)), eye_size)
    pygame.draw.circle(surface, (0, 0, 0), (int(eye1_x), int(eye1_y)), max(1, eye_size - 1))
    pygame.draw.circle(surface, (0, 0, 0), (int(eye2_x), int(eye2_y)), max(1, eye_size - 1))

def _draw_shooter_circle(circle, surface):
    """Draw shooter circle with special visual effects"""
    # Don't draw if invisible
    if hasattr(circle, 'is_invisible') and circle.is_invisible:
        return
        
    # Draw main circle body
    pygame.draw.circle(surface, circle.color, (int(circle.x), int(circle.y)), int(circle.radius))
    
    # Draw detection range indicator (faint circle when player is nearby)
    import game_config
    if game_config.GAME_INSTANCE is not None:
        mouse_pos = pygame.mouse.get_pos()
        distance_to_mouse = math.sqrt((circle.x - mouse_pos[0]) ** 2 + (circle.y - mouse_pos[1]) ** 2)
        
        if distance_to_mouse <= circle.detection_range:
            # Draw detection range as a faint circle
            range_surface = pygame.Surface((circle.detection_range * 2, circle.detection_range * 2), pygame.SRCALPHA)
            pygame.draw.circle(range_surface, (*RED, 30), 
                             (int(circle.detection_range), int(circle.detection_range)), 
                             int(circle.detection_range), 2)
            surface.blit(range_surface, 
                        (circle.x - circle.detection_range, circle.y - circle.detection_range))
    
    # Draw cannon barrels (multiple small circles around the perimeter with spinning effect)
    cannon_count = 8
    cannon_radius = 4 * circle.scale_factor
    
    # Calculate the current rotation based on spin_angle
    base_angle = getattr(circle, 'spin_angle', 0)
    
    for i in range(cannon_count):
        # Calculate angle with spin applied
        angle = base_angle + (2 * math.pi * i) / cannon_count
        
        # Calculate cannon position with some offset for visual interest
        offset_radius = circle.radius * 0.9  # Slightly inside the main circle
        cannon_x = circle.x + math.cos(angle) * offset_radius
        cannon_y = circle.y + math.sin(angle) * offset_radius
        
        # Draw outer black circle (outline)
        pygame.draw.circle(surface, BLACK, (int(cannon_x), int(cannon_y)), int(cannon_radius))
        
        # Draw inner colored circle - change color based on spin speed for visual feedback
        if hasattr(circle, 'spin_speed') and circle.spin_speed > 0:
            # Calculate color based on spin speed (from blue to red as speed increases)
            speed_ratio = min(1.0, circle.spin_speed / circle.max_spin_speed)
            cannon_color = (
                int(100 + 155 * speed_ratio),  # R: 100-255
                100,                           # G: Fixed at 100
                int(255 - 155 * speed_ratio)   # B: 255-100
            )
        else:
            cannon_color = GRAY
            
        pygame.draw.circle(surface, cannon_color, (int(cannon_x), int(cannon_y)), int(cannon_radius - 1))
    
    # Draw center core
    core_radius = circle.radius * 0.3
    pygame.draw.circle(surface, BLACK, (int(circle.x), int(circle.y)), int(core_radius))
    pygame.draw.circle(surface, DARK_BLUE, (int(circle.x), int(circle.y)), int(core_radius - 2))

def _draw_standard_circle(circle, surface):
    """Draw standard circle"""
    pygame.draw.circle(surface, circle.color, (int(circle.x), int(circle.y)), int(circle.radius))

def _draw_health_bar(circle, surface):
    """Draw health bar and health numbers for all circles with multiple health"""
    # Don't draw health bar for invisible shooters
    if (circle.type == CircleType.SHOOTER and 
        hasattr(circle, 'is_invisible') and circle.is_invisible):
        return
        
    # Adjust bar size based on circle size
    bar_width = max(30, circle.radius * 1.8)  # Minimum width for small circles
    bar_height = max(4, int(6 * circle.scale_factor))
    bar_x = circle.x - bar_width // 2
    bar_y = circle.y - circle.radius - (18 * circle.scale_factor)

    # Background (red)
    pygame.draw.rect(surface, RED, (bar_x, bar_y, bar_width, bar_height))
    
    # Health fill (green to yellow to red based on health percentage)
    health_percentage = circle.health / circle.max_health
    if health_percentage > 0.6:
        health_color = GREEN
    elif health_percentage > 0.3:
        health_color = YELLOW
    else:
        health_color = ORANGE
    
    health_width = health_percentage * bar_width
    pygame.draw.rect(surface, health_color, (bar_x, bar_y, health_width, bar_height))
    
    # Border around health bar
    pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)
    
    # Draw health numbers for circles with high health (4+ max health)
    if circle.max_health >= 4:
        # Create font for health text
        font_size = max(12, int(14 * circle.scale_factor))
        try:
            font = pygame.font.Font(None, font_size)
        except:
            font = pygame.font.Font(None, 20)  # Fallback
        
        health_text = f"{circle.health}/{circle.max_health}"
        text_surface = font.render(health_text, True, WHITE)
        text_rect = text_surface.get_rect()
        text_rect.centerx = circle.x
        text_rect.bottom = bar_y - 2
        
        # Draw text background for better visibility
        bg_rect = text_rect.copy()
        bg_rect.inflate(4, 2)
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (0, 0, 0, 180), (0, 0, bg_rect.width, bg_rect.height))
        surface.blit(bg_surface, bg_rect)
        
        surface.blit(text_surface, text_rect)
