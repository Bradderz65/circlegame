import pygame
import math
import time
import random

from game_config import *
from game_state import GameMode

# Lightweight caches to avoid recreating the same heavy surfaces every frame
# Keyed by parameters that affect the visual output.
SHADOW_CACHE = {}
VIGNETTE_CACHE = {}
GLOW_CACHE = {}

def draw_shadow(surface, rect, radius=12, spread=6, alpha=90):
    """Draw a soft shadow behind a rect using a cached alpha surface."""
    key = (rect.width, rect.height, radius, spread, alpha)
    shadow_surface = SHADOW_CACHE.get(key)
    if shadow_surface is None:
        shadow_surface = pygame.Surface((rect.width + spread * 2, rect.height + spread * 2), pygame.SRCALPHA)
        shadow_color = (0, 0, 0, alpha)
        pygame.draw.rect(
            shadow_surface,
            shadow_color,
            pygame.Rect(0, 0, rect.width + spread * 2, rect.height + spread * 2),
            border_radius=radius + 2,
        )
        SHADOW_CACHE[key] = shadow_surface
    surface.blit(shadow_surface, (rect.x - spread, rect.y - spread))

def draw_panel(surface, rect, bg_color, border_color, radius=12, border_width=2, with_shadow=True):
    """Draw a rounded panel with optional soft shadow (shadow cached)."""
    if with_shadow:
        draw_shadow(surface, rect, radius=radius, spread=8, alpha=80)
    pygame.draw.rect(surface, bg_color, rect, border_radius=radius)
    if border_width:
        pygame.draw.rect(surface, border_color, rect, border_width, border_radius=radius)

def draw_vignette(surface, intensity=120):
    """Darken edges to focus attention to center (cached per size + intensity)."""
    w, h = surface.get_size()
    key = (w, h, intensity)
    overlay = VIGNETTE_CACHE.get(key)
    if overlay is None:
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w / 2, h / 2
        max_r = math.hypot(cx, cy)
        for i in range(8):
            # Draw expanding transparent rings toward edges
            t = i / 7
            a = int(intensity * (t ** 2))
            color = (0, 0, 0, a)
            margin = int(t * max(cx, cy))
            pygame.draw.rect(
                overlay,
                color,
                pygame.Rect(margin, margin, w - margin * 2, h - margin * 2),
                2,
                border_radius=20,
            )
        VIGNETTE_CACHE[key] = overlay
    surface.blit(overlay, (0, 0))

def _get_glow_surface(text, font, color, glow_color, glow_size=6, glow_alpha=60):
    """Build and cache a text+glow surface independent of position."""
    key = (text, font.get_height(), color, glow_color, glow_size, glow_alpha)
    cached = GLOW_CACHE.get(key)
    if cached is not None:
        return cached

    base = font.render(text, True, color)
    glow = font.render(text, True, glow_color)

    # Allocate with padding for glow around all sides
    pad = glow_size
    surf_w = base.get_width() + pad * 2
    surf_h = base.get_height() + pad * 2
    glow_surface = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

    center = (surf_w // 2, surf_h // 2)
    for r in range(1, glow_size + 1):
        alpha = int(glow_alpha * (1 - (r - 1) / glow_size))
        glow_surf = glow.copy()
        glow_surf.set_alpha(alpha)
        for dx, dy in (
            (r, 0), (-r, 0), (0, r), (0, -r), (r, r), (-r, -r), (r, -r), (-r, r)
        ):
            rect = glow_surf.get_rect(center=(center[0] + dx, center[1] + dy))
            glow_surface.blit(glow_surf, rect)

    # Draw base text centered
    base_rect = base.get_rect(center=center)
    glow_surface.blit(base, base_rect)
    GLOW_CACHE[key] = glow_surface
    return glow_surface

def draw_text_with_glow(surface, text, font, color, glow_color, center, glow_size=6, glow_alpha=60):
    """Render text with a soft glow using a cached precomposed surface."""
    glow_surface = _get_glow_surface(text, font, color, glow_color, glow_size, glow_alpha)
    rect = glow_surface.get_rect(center=center)
    surface.blit(glow_surface, rect)

def draw_simple_background(game):
    """Draw a plain black background for accessibility"""
    # Simply fill the screen with black - no animations, gradients, or moving elements
    game.screen.fill(BLACK)

def draw_enhanced_background(game):
    """Draw an optimized enhanced background with static gradient and color-transitioning stars
    
    Fixed: Background and stars now properly recreate when screen size changes (F11 fullscreen toggle)
    """
    # Initialize star color transition timer
    if not hasattr(game, 'star_color_start_time'):
        game.star_color_start_time = time.time()
    
    # Create static gradient background surface (recreate if screen size changed)
    if (not hasattr(game, 'background_gradient_surface') or 
        not hasattr(game, 'background_surface_size') or 
        game.background_surface_size != (game.screen_width, game.screen_height)):
        
        game.background_gradient_surface = pygame.Surface((game.screen_width, game.screen_height))
        game.background_surface_size = (game.screen_width, game.screen_height)
        
        # Use static colors - beautiful blue to purple gradient
        static_top = DARK_BLUE
        static_bottom = DEEP_PURPLE
        
        # Create perfectly smooth gradient line-by-line
        for y in range(game.screen_height):
            ratio = y / game.screen_height
            
            # Interpolate between static_top and static_bottom
            r = int(static_top[0] + (static_bottom[0] - static_top[0]) * ratio)
            g = int(static_top[1] + (static_bottom[1] - static_top[1]) * ratio)
            b = int(static_top[2] + (static_bottom[2] - static_top[2]) * ratio)
            
            color = (r, g, b)
            pygame.draw.line(game.background_gradient_surface, color, (0, y), (game.screen_width, y))
    
    # Blit the cached gradient
    game.screen.blit(game.background_gradient_surface, (0, 0))
    
    # Add enhanced space-like star field (regenerate if screen size changed)
    if (not hasattr(game, 'background_stars') or 
        not hasattr(game, 'stars_screen_size') or 
        game.stars_screen_size != (game.screen_width, game.screen_height)):
        
        game.background_stars = []
        game.stars_screen_size = (game.screen_width, game.screen_height)
        
        # Generate highly varied and dynamic stars
        for _ in range(30):  # Reduced for performance while keeping richness
            # Choose star behavior type
            behavior = random.choices(
                ['static', 'drifting', 'pulsing', 'twinkling', 'shooting', 'orbiting'],
                weights=[40, 20, 15, 15, 5, 5]
            )[0]
            
            # Choose star shape/pattern
            shape = random.choices(
                ['pixel', 'cross', 'diamond', 'plus', 'sparkle', 'circle'],
                weights=[30, 25, 20, 15, 7, 3]
            )[0]
            
            star = {
                'x': random.uniform(0, game.screen_width),
                'y': random.uniform(0, game.screen_height),
                'base_x': 0,  # Will be set for orbiting stars
                'base_y': 0,  # Will be set for orbiting stars
                'brightness': random.uniform(0.4, 1.0),
                'base_brightness': random.uniform(0.4, 1.0),
                'twinkle_speed': random.uniform(0.005, 0.08),
                'size': random.choices([1, 2, 3, 4], weights=[40, 35, 20, 5])[0],
                'behavior': behavior,
                'shape': shape,
                'star_type': random.choices(['normal', 'bright', 'dim', 'colorful'], weights=[50, 25, 15, 10])[0],
                'age': random.uniform(0, 100),  # For animation phases
                'speed': random.uniform(0.1, 2.0),  # For movement
                'direction': random.uniform(0, 2 * math.pi),  # Movement direction
                'orbit_radius': random.uniform(10, 30),  # For orbiting stars
                'orbit_speed': random.uniform(0.01, 0.05),  # Orbit speed
                'pulse_speed': random.uniform(0.02, 0.1),  # Pulsing speed
                'color_offset': random.uniform(0, 1),  # Individual color phase offset
                'trail_length': random.randint(3, 8) if behavior == 'shooting' else 0,
                'trail_positions': []  # For shooting stars
            }
            
            # Set base position for orbiting stars
            if behavior == 'orbiting':
                star['base_x'] = star['x']
                star['base_y'] = star['y']
            
            game.background_stars.append(star)
    
    # Draw dynamic and varied stars
    current_time = time.time()
    dt = 1/60  # Assume 60 FPS for movement calculations
    
    for star in game.background_stars:
        # Update star age for animations
        star['age'] += dt
        
        # Handle different star behaviors
        if star['behavior'] == 'drifting':
            # Slowly drift across screen
            star['x'] += math.cos(star['direction']) * star['speed'] * dt
            star['y'] += math.sin(star['direction']) * star['speed'] * dt
            
            # Wrap around screen edges
            if star['x'] < 0: star['x'] = game.screen_width
            elif star['x'] > game.screen_width: star['x'] = 0
            if star['y'] < 0: star['y'] = game.screen_height
            elif star['y'] > game.screen_height: star['y'] = 0
            
        elif star['behavior'] == 'orbiting':
            # Orbit around a fixed point
            angle = star['age'] * star['orbit_speed']
            star['x'] = star['base_x'] + math.cos(angle) * star['orbit_radius']
            star['y'] = star['base_y'] + math.sin(angle) * star['orbit_radius']
            
        elif star['behavior'] == 'shooting':
            # Shooting star with trail
            old_pos = (star['x'], star['y'])
            star['x'] += math.cos(star['direction']) * star['speed'] * 5  # Faster movement
            star['y'] += math.sin(star['direction']) * star['speed'] * 5
            
            # Add to trail
            star['trail_positions'].append(old_pos)
            if len(star['trail_positions']) > star['trail_length']:
                star['trail_positions'].pop(0)
            
            # Reset if off screen
            if (star['x'] < -50 or star['x'] > game.screen_width + 50 or 
                star['y'] < -50 or star['y'] > game.screen_height + 50):
                star['x'] = random.uniform(0, game.screen_width)
                star['y'] = random.uniform(0, game.screen_height)
                star['trail_positions'] = []
        
        # Calculate brightness based on behavior and type
        base_brightness = star['brightness']
        
        if star['behavior'] == 'twinkling':
            twinkle = math.sin(current_time * star['twinkle_speed'] * 15) * 0.5 + 0.5
            base_brightness *= twinkle
        elif star['behavior'] == 'pulsing':
            pulse = (math.sin(current_time * star['pulse_speed'] * 10) + 1) / 2
            base_brightness = star['base_brightness'] * (0.3 + pulse * 0.7)
        else:
            # Standard twinkling for other types
            twinkle = math.sin(current_time * star['twinkle_speed'] * 10) * 0.3 + 0.7
            base_brightness *= twinkle
        
        # Adjust brightness based on star type
        if star['star_type'] == 'bright':
            base_brightness *= 1.4
        elif star['star_type'] == 'dim':
            base_brightness *= 0.6
        elif star['star_type'] == 'colorful':
            base_brightness *= 1.2
        
        brightness = int(base_brightness * 255)
        
        # Calculate star color with individual offset (very slow 5-minute cycle)
        elapsed_time = time.time() - game.star_color_start_time
        color_cycle = ((elapsed_time / 300.0) + star['color_offset']) % 1.0  # 5 minutes for complete cycle
        
        if star['star_type'] == 'colorful':
            # Colorful stars cycle through rainbow
            hue_cycle = (color_cycle * 6) % 6
            if hue_cycle < 1:  # Red to Yellow
                red_component = brightness
                green_component = int(brightness * hue_cycle)
                blue_component = 0
            elif hue_cycle < 2:  # Yellow to Green
                red_component = int(brightness * (2 - hue_cycle))
                green_component = brightness
                blue_component = 0
            elif hue_cycle < 3:  # Green to Cyan
                red_component = 0
                green_component = brightness
                blue_component = int(brightness * (hue_cycle - 2))
            elif hue_cycle < 4:  # Cyan to Blue
                red_component = 0
                green_component = int(brightness * (4 - hue_cycle))
                blue_component = brightness
            elif hue_cycle < 5:  # Blue to Magenta
                red_component = int(brightness * (hue_cycle - 4))
                green_component = 0
                blue_component = brightness
            else:  # Magenta to Red
                red_component = brightness
                green_component = 0
                blue_component = int(brightness * (6 - hue_cycle))
        else:
            # Standard color transition: Blue-White -> Purple-White -> Pink-White -> Blue-White
            if color_cycle < 0.33:  # Blue to Purple phase
                phase = color_cycle / 0.33
                red_component = int(brightness + (phase * 40))
                green_component = int(brightness * (1 - phase * 0.2))
                blue_component = int((brightness + 30) * (1 - phase * 0.1))
            elif color_cycle < 0.66:  # Purple to Pink phase
                phase = (color_cycle - 0.33) / 0.33
                red_component = int(brightness + 40 + (phase * 30))
                green_component = int(brightness * (0.8 + phase * 0.1))
                blue_component = int((brightness + 30) * (0.9 - phase * 0.3))
            else:  # Pink back to Blue phase
                phase = (color_cycle - 0.66) / 0.34
                red_component = int(brightness + 70 - (phase * 70))
                green_component = int(brightness * (0.9 + phase * 0.1))
                blue_component = int((brightness + 30) * (0.6 + phase * 0.4))
        
        star_color = (min(255, max(0, red_component)), 
                     min(255, max(0, green_component)), 
                     min(255, max(0, blue_component)))
        
        # Draw shooting star trail first
        if star['behavior'] == 'shooting' and star['trail_positions']:
            for i, (trail_x, trail_y) in enumerate(star['trail_positions']):
                trail_alpha = (i + 1) / len(star['trail_positions']) * 0.5
                trail_color = tuple(int(c * trail_alpha) for c in star_color)
                if (0 <= trail_x < game.screen_width and 0 <= trail_y < game.screen_height):
                    game.screen.set_at((int(trail_x), int(trail_y)), trail_color)
        
        # Draw the main star
        star_x, star_y = int(star['x']), int(star['y'])
        
        if 0 <= star_x < game.screen_width and 0 <= star_y < game.screen_height:
            draw_star_shape(game.screen, star_x, star_y, star['shape'], star['size'], star_color)

def clamp_color(color):
    """Ensure color values are valid (0-255)"""
    return tuple(max(0, min(255, int(c))) for c in color)

def draw_star_shape(surface, x, y, shape, size, color):
    """Draw different star shapes and patterns"""
    # Ensure base color is valid
    color = clamp_color(color)
    
    if shape == 'pixel':
        surface.set_at((x, y), color)
        
    elif shape == 'cross':
        # Cross pattern
        for i in range(1, size + 1):
            alpha = max(0, 1 - i * 0.2)
            dim_color = clamp_color(tuple(c * alpha for c in color))
            # Horizontal line
            if 0 <= x - i < surface.get_width() and 0 <= y < surface.get_height():
                surface.set_at((x - i, y), dim_color)
            if 0 <= x + i < surface.get_width() and 0 <= y < surface.get_height():
                surface.set_at((x + i, y), dim_color)
            # Vertical line
            if 0 <= x < surface.get_width() and 0 <= y - i < surface.get_height():
                surface.set_at((x, y - i), dim_color)
            if 0 <= x < surface.get_width() and 0 <= y + i < surface.get_height():
                surface.set_at((x, y + i), dim_color)
        surface.set_at((x, y), color)  # Bright center
        
    elif shape == 'diamond':
        # Diamond pattern
        for dy in range(-size, size + 1):
            width = size - abs(dy)
            for dx in range(-width, width + 1):
                px, py = x + dx, y + dy
                if 0 <= px < surface.get_width() and 0 <= py < surface.get_height():
                    distance = abs(dx) + abs(dy)
                    alpha = max(0, 1 - (distance / (size + 1)))
                    pixel_color = clamp_color(tuple(c * alpha for c in color))
                    surface.set_at((px, py), pixel_color)
                    
    elif shape == 'plus':
        # Plus sign pattern
        for i in range(-size, size + 1):
            alpha = max(0, 1 - (abs(i) / (size + 1)))
            pixel_color = clamp_color(tuple(c * alpha for c in color))
            # Horizontal
            if 0 <= x + i < surface.get_width() and 0 <= y < surface.get_height():
                surface.set_at((x + i, y), pixel_color)
            # Vertical
            if 0 <= x < surface.get_width() and 0 <= y + i < surface.get_height():
                surface.set_at((x, y + i), pixel_color)
                
    elif shape == 'sparkle':
        # Sparkle pattern (4-pointed star)
        surface.set_at((x, y), color)  # Center
        for i in range(1, size + 1):
            alpha = max(0, 1 - (i * 0.3))
            dim_color = clamp_color(tuple(c * alpha for c in color))
            # Main cross
            for dx, dy in [(i, 0), (-i, 0), (0, i), (0, -i)]:
                px, py = x + dx, y + dy
                if 0 <= px < surface.get_width() and 0 <= py < surface.get_height():
                    surface.set_at((px, py), dim_color)
            # Diagonal points (smaller)
            if i <= size // 2:
                diagonal_color = clamp_color(tuple(c * alpha * 0.5 for c in color))
                for dx, dy in [(i, i), (-i, -i), (i, -i), (-i, i)]:
                    px, py = x + dx, y + dy
                    if 0 <= px < surface.get_width() and 0 <= py < surface.get_height():
                        surface.set_at((px, py), diagonal_color)
                        
    elif shape == 'circle':
        # Circular star
        for dy in range(-size, size + 1):
            for dx in range(-size, size + 1):
                distance = math.sqrt(dx*dx + dy*dy)
                if distance <= size:
                    px, py = x + dx, y + dy
                    if 0 <= px < surface.get_width() and 0 <= py < surface.get_height():
                        alpha = max(0, 1 - (distance / (size + 1)))
                        pixel_color = clamp_color(tuple(c * alpha for c in color))
                        surface.set_at((px, py), pixel_color)

def draw_background(game):
    """Draw background based on accessibility settings"""
    if game.accessibility.get('dynamic_background', False):
        draw_enhanced_background(game)
    else:
        draw_simple_background(game)

def draw_main_menu(game):
    # Background + optional vignette
    draw_background(game)
    # Disable vignette in fullscreen to avoid thin ring artifact above buttons
    if not getattr(game, 'fullscreen', False):
        draw_vignette(game.screen, intensity=100)

    # Title and tagline
    title_y = int(120 * game.scale_factor)
    draw_text_with_glow(
        game.screen,
        "CIRCLE CLICKER",
        game.big_font,
        LIGHT_BLUE,
        (80, 140, 220),
        (game.screen_width // 2, title_y),
        glow_size=10,
        glow_alpha=80,
    )

    tagline = game.font.render("Fast. Precise. Addictive.", True, YELLOW)
    game.screen.blit(tagline, tagline.get_rect(center=(game.screen_width // 2, title_y + int(40 * game.scale_factor))))

    # Centered button stack
    buttons = get_main_menu_buttons(game)
    # Compute a tight panel around actual button rects to avoid extra outline space above
    if buttons:
        left = min(r.left for _, r, _ in buttons)
        right = max(r.right for _, r, _ in buttons)
        top = min(r.top for _, r, _ in buttons)
        bottom = max(r.bottom for _, r, _ in buttons)

        # Use asymmetric padding: keep smaller top padding to prevent a visible bar above
        pad_x = int(16 * game.scale_factor)
        # Extend the panel slightly more above the buttons for balanced padding
        pad_top = int(18 * game.scale_factor)
        pad_bottom = int(16 * game.scale_factor)

        panel_rect = pygame.Rect(
            left - pad_x,
            top - pad_top,
            (right - left) + pad_x * 2,
            (bottom - top) + pad_top + pad_bottom,
        )
        draw_panel(game.screen, panel_rect, (18, 20, 32), LIGHT_BLUE, radius=16, border_width=2, with_shadow=True)

    selected_idx = getattr(game, 'menu_selected_index', 0)
    for i, (label, rect, action) in enumerate(buttons):
        is_active = (i == selected_idx)
        draw_menu_button(game, rect, label, is_active)

    # Bottom hotkeys hint
    hint = game.small_font.render("Space: Play  •  S: Sandbox  •  H: Scores  •  A: Accessibility  •  F11: Fullscreen", True, LIGHT_GRAY)
    game.screen.blit(hint, hint.get_rect(center=(game.screen_width // 2, game.screen_height - int(40 * game.scale_factor))))

def draw_menu_button(game, rect, text, hover):
    base = (30, 34, 52)
    active_bg = (38, 50, 78)
    border = LIGHT_BLUE if hover else (90, 90, 120)
    bg = active_bg if hover else base
    draw_panel(game.screen, rect, bg, border, radius=12, border_width=3 if hover else 2, with_shadow=hover)

    # Left accent bar when active
    if hover:
        accent_w = max(6, int(6 * game.scale_factor))
        accent = pygame.Rect(rect.left + 4, rect.top + 4, accent_w, rect.height - 8)
        pygame.draw.rect(game.screen, LIGHT_BLUE, accent, border_radius=6)

    # Label
    color = WHITE if hover else LIGHT_GRAY
    label = game.font.render(text, True, color)
    game.screen.blit(label, label.get_rect(center=rect.center))

def get_main_menu_buttons(game):
    # Define button specs
    labels = [
        ("Play", 'play'),
        ("Sandbox", 'sandbox'),
        ("High Scores", 'scores'),
        ("Accessibility", 'accessibility'),
        ("Quit", 'quit'),
    ]
    btn_w = int(420 * game.scale_factor)
    btn_h = int(58 * game.scale_factor)
    spacing = int(14 * game.scale_factor)
    start_y = int(game.screen_height * 0.35)
    x = game.screen_width // 2 - btn_w // 2

    out = []
    y = start_y
    for text, action in labels:
        rect = pygame.Rect(x, y, btn_w, btn_h)
        out.append((text, rect, action))
        y += btn_h + spacing
    return out

def draw_circle_type_icon(surface, x, y, r, type_name: str):
    """Draw a small icon representing a circle type at (x, y) with radius r"""
    # Helper: draw hexagon
    def hex_points(cx, cy, radius):
        pts = []
        for k in range(6):
            ang = math.radians(60 * k - 30)
            pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
        return pts

    # Base style
    outline = WHITE
    name = type_name.lower()

    if name == 'normal':
        pygame.draw.circle(surface, RED, (x, y), r)
        pygame.draw.circle(surface, outline, (x, y), r, 2)
    elif name == 'fast':
        pygame.draw.circle(surface, BLUE, (x, y), r)
        pygame.draw.circle(surface, outline, (x, y), r, 2)
        # motion lines
        for dx in (int(-r*1.2), int(-r*1.6)):
            pygame.draw.line(surface, LIGHT_BLUE, (x+dx, y - r//3), (x+dx + r//2, y - r//3), 2)
            pygame.draw.line(surface, LIGHT_BLUE, (x+dx, y + r//3), (x+dx + r//2, y + r//3), 2)
    elif name == 'teleporting' or name == 'teleport':
        pygame.draw.circle(surface, PURPLE, (x, y), r)
        pygame.draw.circle(surface, outline, (x, y), r, 2)
        # sparkles
        for ang in range(0, 360, 90):
            ax = x + int((r + 6) * math.cos(math.radians(ang)))
            ay = y + int((r + 6) * math.sin(math.radians(ang)))
            pygame.draw.circle(surface, LIGHT_GRAY, (ax, ay), 2)
    elif name == 'shrinking' or name == 'shrink':
        pygame.draw.circle(surface, ORANGE, (x, y), r)
        pygame.draw.circle(surface, outline, (x, y), r, 2)
        pygame.draw.circle(surface, YELLOW, (x, y), max(1, int(r*0.55)), 2)
    elif name == 'small':
        rr = max(2, int(r * 0.55))
        pygame.draw.circle(surface, YELLOW, (x, y), rr)
        pygame.draw.circle(surface, outline, (x, y), rr, 2)
    elif name == 'ghost':
        # Semi-transparent fill with outline
        temp = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
        pygame.draw.circle(temp, (*LIGHT_GRAY, 120), (r*2, r*2), r)
        surface.blit(temp, (x - r*2, y - r*2))
        pygame.draw.circle(surface, LIGHT_GRAY, (x, y), r, 2)
    elif name == 'tank':
        # New tank icon: heavy armor with shield emblem
        rr = int(r * 1.15)
        pygame.draw.circle(surface, DARK_GRAY, (x, y), rr)
        pygame.draw.circle(surface, WHITE, (x, y), rr, 4)  # thick outer ring
        # inner armor plate
        inner = int(rr * 0.65)
        pygame.draw.circle(surface, GRAY, (x, y), inner)
        # shield emblem
        shield_w = int(inner * 0.9)
        shield_h = int(inner * 0.9)
        top = (x, y - shield_h // 2)
        right = (x + shield_w // 2, y - shield_h // 6)
        bottom = (x, y + shield_h // 2)
        left = (x - shield_w // 2, y - shield_h // 6)
        pygame.draw.polygon(surface, DARK_GRAY, [top, right, bottom, left])
        pygame.draw.polygon(surface, BLACK, [top, right, bottom, left], 1)
    elif name == 'supertank':
        rr = int(r * 1.15)
        pygame.draw.circle(surface, RED, (x, y), rr)
        pygame.draw.circle(surface, WHITE, (x, y), rr, 3)
        # star center
        star_r_outer = max(3, rr // 2)
        star_r_inner = max(2, star_r_outer // 2)
        pts = []
        for k in range(10):
            ang = -math.pi/2 + k * (math.pi/5)
            rad = star_r_outer if k % 2 == 0 else star_r_inner
            pts.append((x + rad * math.cos(ang), y + rad * math.sin(ang)))
        pygame.draw.polygon(surface, YELLOW, [(int(px), int(py)) for px, py in pts])
    elif name == 'hexagon':
        pts = hex_points(x, y, r)
        pygame.draw.polygon(surface, LIGHT_BLUE, pts)
        pygame.draw.polygon(surface, outline, pts, 2)
    elif name == 'cursor grabber' or name == 'cursor_grabber':
        pygame.draw.circle(surface, PINK, (x, y), r)
        pygame.draw.circle(surface, outline, (x, y), r, 2)
        # grab spokes
        for ang in (45, 135, 225, 315):
            ax = x + int((r + 6) * math.cos(math.radians(ang)))
            ay = y + int((r + 6) * math.sin(math.radians(ang)))
            bx = x + int((r - 4) * math.cos(math.radians(ang)))
            by = y + int((r - 4) * math.sin(math.radians(ang)))
            pygame.draw.line(surface, PINK, (bx, by), (ax, ay), 3)
    elif name == 'snake':
        # draw a small sine-like segment series
        segs = 6
        for i in range(segs):
            t = i / (segs - 1)
            px = x - r + int(2*r * t)
            py = y + int(math.sin(t * math.pi * 2) * (r * 0.4))
            pygame.draw.circle(surface, GREEN, (px, py), max(2, int(r*0.25)))
    elif name == 'shooter':
        # Use previous tank styling (heavy with rivets)
        rr = int(r * 1.1)
        pygame.draw.circle(surface, DARK_GRAY, (x, y), rr)
        pygame.draw.circle(surface, RED, (x, y), rr, 3)
        for ang in range(0, 360, 60):
            ax = x + int(rr * 0.7 * math.cos(math.radians(ang)))
            ay = y + int(rr * 0.7 * math.sin(math.radians(ang)))
            pygame.draw.circle(surface, GRAY, (ax, ay), 2)
    else:
        # Fallback
        pygame.draw.circle(surface, WHITE, (x, y), r, 2)

def draw_circle_types_section(game, start_y: int):
    """Draw a responsive grid showcasing all circle types with icons and labels"""
    margin_x = int(40 * game.scale_factor)
    box_width = max(300, game.screen_width - margin_x * 2)
    center_x = game.screen_width // 2
    section_left = center_x - box_width // 2

    # Data for types (ensure we cover all defined types)
    types = [
        'Normal', 'Fast', 'Teleporting', 'Shrinking', 'Small', 'Ghost',
        'Tank', 'Supertank', 'Hexagon', 'Cursor Grabber', 'Snake', 'Shooter'
    ]

    title_surface = game.font.render("🎯 CIRCLE TYPES", True, ORANGE)
    title_rect = title_surface.get_rect(center=(center_x, start_y))

    # Grid metrics
    cell_min_w = int(140 * game.scale_factor)
    cols = max(3, min(6, box_width // cell_min_w))
    cell_w = box_width // cols
    icon_r = max(10, int(18 * game.scale_factor))
    label_y_offset = int(26 * game.scale_factor)  # push labels further down

    rows = (len(types) + cols - 1) // cols
    cell_h = int(72 * game.scale_factor)  # taller to accommodate extra text
    grid_top = start_y + int(30 * game.scale_factor)
    box_height = int(20 * game.scale_factor) + rows * cell_h + int(20 * game.scale_factor)

    # Section rect (extend upwards a bit for nicer framing)
    top_extra = int(30 * game.scale_factor)
    bottom_extra = int(20 * game.scale_factor)
    section_rect = pygame.Rect(section_left, start_y - top_extra, box_width, box_height + top_extra + bottom_extra)
    draw_panel(game.screen, section_rect, (15, 15, 25), ORANGE, radius=12, border_width=2, with_shadow=True)

    # Title
    game.screen.blit(title_surface, title_rect)

    # Draw grid
    for idx, label in enumerate(types):
        row = idx // cols
        col = idx % cols
        cell_left = section_left + col * cell_w
        cx = cell_left + cell_w // 2
        cy = grid_top + row * cell_h + int(20 * game.scale_factor)

        # Icon
        draw_circle_type_icon(game.screen, cx, cy, icon_r, label)

        # Label (truncate if necessary)
        text_surface = game.small_font.render(label, True, WHITE)
        max_label_w = cell_w - int(16 * game.scale_factor)
        label_text = label
        if text_surface.get_width() > max_label_w:
            while text_surface.get_width() > max_label_w and len(label_text) > 3:
                label_text = label_text[:-1]
                text_surface = game.small_font.render(label_text + '…', True, WHITE)
            label_text = label_text + '…' if label_text != label else label_text
        label_surface = game.small_font.render(label_text, True, WHITE)
        label_rect = label_surface.get_rect(center=(cx, cy + label_y_offset))
        game.screen.blit(label_surface, label_rect)

        # Extra description line under each label
        descriptions = {
            'Normal': 'Basic target',
            'Fast': 'Moves quicker',
            'Teleporting': 'Blinks around',
            'Shrinking': 'Gets smaller',
            'Small': 'Tiny hitbox',
            'Ghost': 'Semi-transparent',
            'Tank': 'High health',
            'Supertank': 'Boss-tier tank',
            'Hexagon': 'Special shape',
            'Cursor Grabber': 'Grabs cursor',
            'Snake': 'Sinuous path',
            'Shooter': 'Fires projectiles'
        }
        desc = descriptions.get(label, '')
        if desc:
            desc_surface = game.small_font.render(desc, True, LIGHT_GRAY)
            desc_rect = desc_surface.get_rect(center=(cx, cy + label_y_offset + int(16 * game.scale_factor)))
            game.screen.blit(desc_surface, desc_rect)

def measure_menu_section(game, title, items, title_color):
    """Measure the menu section's width and height using the same rules as draw_menu_section."""
    available_column_width = (game.screen_width // 3) - int(40 * game.scale_factor)

    max_item_width = 0
    for item in items:
        if " - " in item:
            key_part, desc_part = item.split(" - ", 1)
            key_surface = game.small_font.render(key_part, True, title_color)
            desc_surface = game.small_font.render(f" - {desc_part}", True, WHITE)
            item_width = key_surface.get_width() + desc_surface.get_width()
        else:
            item_surface = game.small_font.render(item, True, WHITE)
            item_width = item_surface.get_width()
        max_item_width = max(max_item_width, item_width)

    title_surface = game.font.render(title, True, title_color)
    title_width = title_surface.get_width()

    content_width = max(max_item_width, title_width)
    section_width = min(content_width + int(40 * game.scale_factor), available_column_width)

    title_height = int(40 * game.scale_factor)
    items_height = len(items) * int(25 * game.scale_factor)
    bottom_margin = int(15 * game.scale_factor)
    section_height = title_height + items_height + bottom_margin

    return section_width, section_height

def draw_menu_section(game, title, items, center_x, start_y, title_color):
    """Draw a menu section with title and items"""
    # Calculate maximum available width per column (with margins)
    available_column_width = (game.screen_width // 3) - int(40 * game.scale_factor)  # Column width minus margins
    
    # Calculate proper section dimensions based on content and available space
    max_item_width = 0
    for item in items:
        if " - " in item:
            key_part, desc_part = item.split(" - ", 1)
            key_surface = game.small_font.render(key_part, True, title_color)
            desc_surface = game.small_font.render(f" - {desc_part}", True, WHITE)
            item_width = key_surface.get_width() + desc_surface.get_width()
        else:
            item_surface = game.small_font.render(item, True, WHITE)
            item_width = item_surface.get_width()
        max_item_width = max(max_item_width, item_width)
    
    # Title width
    title_surface = game.font.render(title, True, title_color)
    title_width = title_surface.get_width()
    
    # Section dimensions with proper padding - constrained to available space
    content_width = max(max_item_width, title_width)
    section_width = min(content_width + int(40 * game.scale_factor), available_column_width)  # Constrain to column width
    
    # Calculate proper height to contain all content with margins
    title_height = int(40 * game.scale_factor)  # Space for title
    items_height = len(items) * int(25 * game.scale_factor)  # Space for all items
    bottom_margin = int(15 * game.scale_factor)  # Bottom margin
    section_height = title_height + items_height + bottom_margin
    
    section_rect = pygame.Rect(center_x - section_width // 2, start_y - int(10 * game.scale_factor),
                               section_width, section_height)

    # Background with rounded corners and shadow
    panel_bg = (15, 15, 25)
    draw_panel(game.screen, section_rect, panel_bg, title_color, radius=12, border_width=2, with_shadow=True)
    
    # Section title - centered within the box (slight glow)
    draw_text_with_glow(
        game.screen,
        title,
        game.font,
        title_color,
        (title_color[0]//2, title_color[1]//2, title_color[2]//2),
        (center_x, start_y + int(20 * game.scale_factor)),
        glow_size=4,
        glow_alpha=50,
    )
    
    # Section items - positioned within the box bounds
    item_y = start_y + int(50 * game.scale_factor)  # Start below title with more spacing
    box_left = section_rect.left + int(20 * game.scale_factor)  # Left margin inside box
    box_right = section_rect.right - int(20 * game.scale_factor)  # Right margin inside box
    
    for item in items:
        # Check if item would extend beyond box bottom
        if item_y + int(20 * game.scale_factor) > section_rect.bottom:
            break  # Stop adding items if they would extend outside the box
        
        # Highlight key bindings
        if " - " in item:
            key_part, desc_part = item.split(" - ", 1)
            # Draw key in highlight color
            key_surface = game.small_font.render(key_part, True, title_color)
            desc_surface = game.small_font.render(f" - {desc_part}", True, WHITE)
            
            # Calculate positions for aligned text within box bounds
            total_width = key_surface.get_width() + desc_surface.get_width()
            available_width = box_right - box_left
            
            if total_width <= available_width:
                # Center if it fits
                start_x = center_x - total_width // 2
            else:
                # Left align if too wide and truncate description
                start_x = box_left
                available_desc_width = available_width - key_surface.get_width() - int(5 * game.scale_factor)  # Small buffer
                desc_text = f" - {desc_part}"
                
                # More aggressive truncation
                while desc_surface.get_width() > available_desc_width and len(desc_text) > 6:
                    desc_text = desc_text[:-5] + "..."
                    desc_surface = game.small_font.render(desc_text, True, WHITE)
                
                # If still too wide, truncate more aggressively
                if desc_surface.get_width() > available_desc_width:
                    desc_text = " - ..."
                    desc_surface = game.small_font.render(desc_text, True, WHITE)
            
            game.screen.blit(key_surface, (start_x, item_y))
            game.screen.blit(desc_surface, (start_x + key_surface.get_width(), item_y))
        else:
            # Regular item - center within box bounds
            item_surface = game.small_font.render(item, True, WHITE)
            available_width = box_right - box_left
            
            if item_surface.get_width() <= available_width:
                item_rect = item_surface.get_rect(center=(center_x, item_y))
            else:
                # Left align if too wide and truncate if necessary
                item_text = item
                buffer_width = int(5 * game.scale_factor)  # Small buffer
                
                # More aggressive truncation
                while item_surface.get_width() > (available_width - buffer_width) and len(item_text) > 5:
                    item_text = item_text[:-5] + "..."
                    item_surface = game.small_font.render(item_text, True, WHITE)
                
                # If still too wide, use minimal text
                if item_surface.get_width() > (available_width - buffer_width):
                    item_text = "..."
                    item_surface = game.small_font.render(item_text, True, WHITE)
                
                item_rect = item_surface.get_rect()
                item_rect.left = box_left
                item_rect.centery = item_y
            
            game.screen.blit(item_surface, item_rect)
        
        item_y += int(25 * game.scale_factor)

def draw_difficulty_select(game):
    # Background + vignette
    draw_background(game)
    if not getattr(game, 'fullscreen', False):
        draw_vignette(game.screen, intensity=100)

    # Title with glow
    draw_text_with_glow(
        game.screen,
        "Select Difficulty",
        game.big_font,
        WHITE,
        (120, 120, 160),
        (game.screen_width // 2, int(120 * game.scale_factor)),
        glow_size=8,
        glow_alpha=70,
    )

    # Buttons
    diffs = [game.difficulty.EASY, game.difficulty.MEDIUM, game.difficulty.HARD, game.difficulty.NIGHTMARE]
    labels = [f"{d.name.capitalize()} — {game.difficulty_settings[d]['description']}" for d in diffs]

    btn_w = int(520 * game.scale_factor)
    btn_h = int(58 * game.scale_factor)
    spacing = int(14 * game.scale_factor)
    start_y = int(game.screen_height * 0.35)
    x = game.screen_width // 2 - btn_w // 2

    y = start_y
    # Build clickable rects for mouse input
    game.difficulty_option_rects = []
    for d, label in zip(diffs, labels):
        rect = pygame.Rect(x, y, btn_w, btn_h)
        draw_menu_button(game, rect, label, hover=(d == game.difficulty))
        game.difficulty_option_rects.append((rect, d))
        y += btn_h + spacing

    # Current speed info
    current_mult = game.get_current_speed_multiplier()
    speed_info = f"Current Round Speed: {current_mult:.2f}x"
    speed_text = game.small_font.render(speed_info, True, YELLOW)
    game.screen.blit(speed_text, speed_text.get_rect(center=(game.screen_width // 2, y + int(10 * game.scale_factor))))

    # Instructions
    info_y = game.screen_height - int(80 * game.scale_factor)
    for i, t in enumerate(["UP/DOWN to choose • ENTER to continue", "ESC to return to main menu"]):
        text = game.small_font.render(t, True, LIGHT_GRAY)
        game.screen.blit(text, text.get_rect(center=(game.screen_width // 2, info_y + i * int(22 * game.scale_factor))))

def draw_time_select(game):
    # Background + vignette
    draw_background(game)
    if not getattr(game, 'fullscreen', False):
        draw_vignette(game.screen, intensity=100)

    # Title with glow
    draw_text_with_glow(
        game.screen,
        "Select Game Mode",
        game.big_font,
        WHITE,
        (120, 120, 160),
        (game.screen_width // 2, int(120 * game.scale_factor)),
        glow_size=8,
        glow_alpha=70,
    )

    # Buttons for modes
    btn_w = int(520 * game.scale_factor)
    btn_h = int(58 * game.scale_factor)
    spacing = int(14 * game.scale_factor)
    start_y = int(game.screen_height * 0.35)
    x = game.screen_width // 2 - btn_w // 2

    y = start_y
    endless_rect = pygame.Rect(x, y, btn_w, btn_h)
    draw_menu_button(game, endless_rect, "Endless Mode — Play until you quit", hover=(game.game_mode == GameMode.ENDLESS))
    y += btn_h + spacing
    timed_rect = pygame.Rect(x, y, btn_w, btn_h)
    draw_menu_button(game, timed_rect, f"Timed Mode — {game.time_limit}s race", hover=(game.game_mode == GameMode.TIMED))
    y += btn_h + spacing

    # Expose rects for mouse interactions
    game.mode_option_rects = [(endless_rect, GameMode.ENDLESS), (timed_rect, GameMode.TIMED)]

    # Timed config panel
    if game.game_mode == GameMode.TIMED:
        cfg_rect = pygame.Rect(x, y + int(10 * game.scale_factor), btn_w, int(60 * game.scale_factor))
        draw_panel(game.screen, cfg_rect, (18, 20, 32), YELLOW, radius=12, border_width=2, with_shadow=False)
        txt = game.font.render(f"Time Limit: {game.time_limit}s  (LEFT/RIGHT)", True, YELLOW)
        game.screen.blit(txt, txt.get_rect(center=cfg_rect.center))
        game.time_cfg_rect = cfg_rect
    else:
        # Remove the attribute if present to avoid stale rects
        if hasattr(game, 'time_cfg_rect'):
            delattr(game, 'time_cfg_rect')

    # Instructions
    info_y = game.screen_height - int(80 * game.scale_factor)
    for i, t in enumerate(["UP/DOWN to choose • LEFT/RIGHT to adjust time", "ENTER to start • ESC to go back"]):
        s = game.small_font.render(t, True, LIGHT_GRAY)
        game.screen.blit(s, s.get_rect(center=(game.screen_width // 2, info_y + i * int(22 * game.scale_factor))))

def draw_medal_icon(surface, cx, cy, size, medal_type):
    """Draw a medal icon with simple ribbons.
    medal_type: 'gold' | 'silver' | 'bronze'
    cx, cy are the center of the medal circle.
    """
    # Color palettes
    if medal_type == 'gold':
        base = (212, 175, 55)
        dark = (160, 120, 30)
        light = (255, 215, 100)
    elif medal_type == 'silver':
        base = (192, 192, 192)
        dark = (140, 140, 140)
        light = (230, 230, 230)
    else:  # bronze
        base = (205, 127, 50)
        dark = (150, 85, 30)
        light = (230, 160, 90)

    r = max(6, size // 2)
    # Ribbons removed per request

    # Medal outer ring and fill
    pygame.draw.circle(surface, dark, (int(cx), int(cy)), r)
    pygame.draw.circle(surface, base, (int(cx), int(cy)), max(1, r - 2))

    # Highlight arc (simple small lighter circle near top-left)
    highlight_r = max(2, r - 6)
    if highlight_r > 0:
        highlight_surf = pygame.Surface((highlight_r * 2 + 2, highlight_r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(highlight_surf, (*light, 140), (highlight_r + 1, highlight_r + 1), highlight_r)
        surface.blit(highlight_surf, (int(cx - r * 0.6), int(cy - r * 0.6)))

    # Simple center star imprint
    star_r_outer = max(2, r // 2)
    star_r_inner = max(1, star_r_outer // 2)
    points = []
    for k in range(10):
        angle = -math.pi / 2 + k * (math.pi / 5)
        rad = star_r_outer if k % 2 == 0 else star_r_inner
        px = cx + rad * math.cos(angle)
        py = cy + rad * math.sin(angle)
        points.append((px, py))
    pygame.draw.polygon(surface, light, [(int(px), int(py)) for px, py in points])

def draw_high_scores(game):
    # Background + vignette
    draw_background(game)
    draw_vignette(game.screen, intensity=100)

    # Title with glow
    draw_text_with_glow(
        game.screen,
        "High Scores",
        game.big_font,
        YELLOW,
        (160, 120, 30),
        (game.screen_width // 2, int(80 * game.scale_factor)),
        glow_size=8,
        glow_alpha=80,
    )

    # Subtitle
    subtitle = game.font.render("Top Players", True, WHITE)
    subtitle_rect = subtitle.get_rect(center=(game.screen_width // 2, int(130 * game.scale_factor)))
    game.screen.blit(subtitle, subtitle_rect)

    if game.high_scores:
        # Table background - responsive to current window size
        margin = int(40 * game.scale_factor)
        max_table_width = max(300, game.screen_width - margin * 2)
        table_width = min(int(1300 * game.scale_factor), max_table_width)
        table_height = int(400 * game.scale_factor)
        table_x = game.screen_width // 2 - table_width // 2
        table_y = int(170 * game.scale_factor)

        # Draw table background with rounded panel
        table_rect = pygame.Rect(table_x, table_y, table_width, table_height)
        draw_panel(game.screen, table_rect, DARK_GRAY, WHITE, radius=12, border_width=2, with_shadow=True)

        # Header row with background
        header_height = int(40 * game.scale_factor)
        header_rect = pygame.Rect(table_x, table_y, table_width, header_height)
        draw_panel(game.screen, header_rect, GRAY, WHITE, radius=12, border_width=2, with_shadow=False)
        # Add a soft gradient highlight to the header for depth
        header_overlay = pygame.Surface((table_width, header_height), pygame.SRCALPHA)
        for y in range(header_height):
            t = y / max(1, header_height - 1)
            alpha = int(30 * (1 - t))
            pygame.draw.line(header_overlay, (255, 255, 255, alpha), (0, y), (table_width, y))
        game.screen.blit(header_overlay, (table_x, table_y))

        # Column positions - responsive based on current table width
        base_table_width = int(1300 * game.scale_factor)
        ratio = table_width / base_table_width if base_table_width > 0 else 1.0
        sx = lambda px: int(px * game.scale_factor * ratio)

        rank_x = table_x + sx(25)
        name_x = table_x + sx(90)
        score_x = table_x + sx(240)
        round_x = table_x + sx(360)
        diff_x = table_x + sx(440)
        accessibility_x = table_x + sx(600)  # Base position

        # Give the Difficulty/Mode column more room (windowed and fullscreen)
        extra = int((220 if getattr(game, 'fullscreen', False) else 140) * game.scale_factor)
        min_access_col = int(160 * game.scale_factor)  # keep at least this width for Accessibility
        max_accessibility_x = (table_x + table_width) - min_access_col
        accessibility_x = min(accessibility_x + extra, max_accessibility_x)

        # Header text
        header_y = table_y + int(15 * game.scale_factor)
        headers = [
            ("RANK", rank_x, YELLOW),
            ("NAME", name_x, YELLOW),
            ("SCORE", score_x, YELLOW),
            ("ROUND", round_x, YELLOW),
            ("DIFFICULTY / MODE", diff_x, YELLOW),
            ("ACCESSIBILITY", accessibility_x, YELLOW)
        ]

        for header_text, x_pos, color in headers:
            header_surface = game.small_font.render(header_text, True, color)
            game.screen.blit(header_surface, (x_pos, header_y))

        # Subtle separators between columns
        sep_color = (80, 80, 80)
        for x_pos in (name_x - sx(20), score_x - sx(20), round_x - sx(20), diff_x - sx(20), accessibility_x - sx(20)):
            pygame.draw.line(game.screen, sep_color, (x_pos, table_y + header_height), (x_pos, table_y + table_height - 8))

        # Helper to draw rounded badges (difficulty/mode/accessibility)
        def draw_badge(target_surface, text, x, y, bg, fg, pad_x=8, pad_y=3, border=(200,200,200)):
            label = game.small_font.render(text, True, fg)
            w, h = label.get_width() + pad_x * 2, label.get_height() + pad_y * 2
            rect = pygame.Rect(x, y - 2, w, h)
            pygame.draw.rect(target_surface, bg, rect, border_radius=10)
            pygame.draw.rect(target_surface, border, rect, 1, border_radius=10)
            target_surface.blit(label, (x + pad_x, y + pad_y - 2))
            return w, h

        def measure_badge_width(text, pad_x=8, pad_y=3):
            label = game.small_font.render(text, True, WHITE)
            return label.get_width() + pad_x * 2

        # Score entries
        row_height = int(35 * game.scale_factor)
        for i, hs in enumerate(game.high_scores[:10]):
            row_y = table_y + header_height + (i * row_height) + int(8 * game.scale_factor)

            # Alternate row colors
            if i % 2 == 1:
                pygame.draw.rect(game.screen, (40, 40, 40),
                               (table_x + 2, table_y + header_height + (i * row_height),
                                table_width - 4, row_height))

            # Rank: draw real medal icons for top 3, numbers for the rest
            if i == 0 or i == 1 or i == 2:
                medal_type = 'gold' if i == 0 else ('silver' if i == 1 else 'bronze')
                medal_size = int(min(22 * game.scale_factor, row_height * 0.8))
                cx = rank_x + medal_size // 2
                # Center vertically within the row rectangle (avoid the +8 text offset)
                row_top = table_y + header_height + (i * row_height)
                cy = row_top + row_height // 2
                draw_medal_icon(game.screen, cx, cy, medal_size, medal_type)
            else:
                rank_text = game.small_font.render(f"{i+1}.", True, WHITE)
                game.screen.blit(rank_text, (rank_x, row_y))

            # Name (truncate if too long)
            display_name = hs.name[:12] if len(hs.name) > 12 else hs.name
            name_text = game.small_font.render(display_name, True, WHITE)
            game.screen.blit(name_text, (name_x, row_y))

            # Score with formatting
            formatted_score = f"{hs.score:,}"  # Add commas for thousands
            score_text = game.small_font.render(formatted_score, True, GREEN)
            game.screen.blit(score_text, (score_x, row_y))

            # Round
            round_text = game.small_font.render(str(hs.round_reached), True, BLUE)
            game.screen.blit(round_text, (round_x, row_y))

            # Difficulty and mode as compact badges
            diff_str = hs.difficulty if hasattr(hs, 'difficulty') else "Medium"
            base_diff = diff_str.split("(")[0].strip()
            mode_part = None
            if "(" in diff_str and ")" in diff_str:
                mode_part = diff_str.split("(")[1].split(")")[0]
                if "Timed" in mode_part:
                    mode_part = "Timed"
                elif "Endless" in mode_part:
                    mode_part = "Endless"

            diff_color_map = {
                "Easy": GREEN,
                "Medium": YELLOW,
                "Hard": ORANGE,
                "Nightmare": RED
            }
            dc = diff_color_map.get(base_diff, LIGHT_GRAY)
            bg = (max(0, dc[0] // 3), max(0, dc[1] // 3), max(0, dc[2] // 3))
            # Ensure badges do not overflow into the next column
            max_badge_span = max(40, (accessibility_x - diff_x) - int(12 * game.scale_factor))

            # Try full difficulty first, then abbreviate if needed
            diff_badge_w = measure_badge_width(base_diff)
            draw_diff_text = base_diff
            if diff_badge_w > max_badge_span:
                abbr_map = {"Easy": "E", "Medium": "M", "Hard": "H", "Nightmare": "N"}
                abbr = abbr_map.get(base_diff, base_diff[:1])
                if measure_badge_width(abbr) <= max_badge_span:
                    draw_diff_text = abbr
                    diff_badge_w = measure_badge_width(draw_diff_text)
                else:
                    # As a last resort, draw a tiny dash badge
                    draw_diff_text = "-"
                    diff_badge_w = measure_badge_width(draw_diff_text)

            # Clip drawing to the diff/mode column to prevent overflow
            row_top = table_y + header_height + (i * row_height)
            prev_clip = game.screen.get_clip()
            game.screen.set_clip(pygame.Rect(diff_x, row_top, max_badge_span, row_height))

            # Draw badges into a dedicated column surface to guarantee no overflow
            row_top = table_y + header_height + (i * row_height)
            col_w = max_badge_span
            col_h = row_height
            col_surf = pygame.Surface((col_w, col_h), pygame.SRCALPHA)
            y_rel = row_y - row_top

            used_w, _ = draw_badge(col_surf, draw_diff_text, 0, y_rel, bg, WHITE, border=dc)

            # Mode badge only if it fits within remaining space; try abbreviations if needed
            if mode_part:
                spacing = int(8 * game.scale_factor)
                desired_mode = mode_part
                mode_w = measure_badge_width(desired_mode)
                if used_w + spacing + mode_w > col_w:
                    # Try short forms
                    short_map = {"Endless": "End", "Timed": "Time"}
                    desired_mode = short_map.get(mode_part, mode_part[:3])
                    mode_w = measure_badge_width(desired_mode)
                if used_w + spacing + mode_w > col_w:
                    shorter_map = {"Endless": "E", "Timed": "T"}
                    desired_mode = shorter_map.get(mode_part, mode_part[:1])
                    mode_w = measure_badge_width(desired_mode)
                if used_w + spacing + mode_w <= col_w:
                    draw_badge(col_surf, desired_mode, used_w + spacing, y_rel, (30, 60, 100), LIGHT_BLUE, border=(120,180,255))

            # Blit column surface in-place
            game.screen.blit(col_surf, (diff_x, row_top))

            # Restore previous clip
            game.screen.set_clip(prev_clip)

            # Accessibility status - combine all accessibility features
            accessibility_features = []
            
            # Check for click radius helper
            if hasattr(hs, 'click_radius_helper') and hs.click_radius_helper:
                accessibility_features.append("Click Helper")
            
            # Check for disabled pipes
            if hasattr(hs, 'pipes_disabled') and hs.pipes_disabled:
                accessibility_features.append("No Pipes")
            
            # Check for disabled spinners
            if hasattr(hs, 'spinners_disabled') and hs.spinners_disabled:
                accessibility_features.append("No Spinners")
            
            if accessibility_features:
                max_w = max(80, (table_x + table_width) - accessibility_x - int(20 * game.scale_factor))
                cur_x = accessibility_x
                for feat in accessibility_features:
                    label = 'Click' if feat == 'Click Helper' else ('NoPipes' if feat == 'No Pipes' else ('NoSpinners' if feat == 'No Spinners' else feat))
                    w, _ = draw_badge(game.screen, label, cur_x, row_y, (35,35,35), LIGHT_BLUE, border=(120,120,160))
                    cur_x += w + int(6 * game.scale_factor)
                    if cur_x - accessibility_x > max_w:
                        break
            else:
                # Subtle placeholder badge
                draw_badge(game.screen, "-", accessibility_x, row_y, (30,30,30), GRAY, border=(90,90,90))

        # Statistics section
        stats_y = table_y + table_height + int(30 * game.scale_factor)
        total_scores = len(game.high_scores)
        highest_score = max(hs.score for hs in game.high_scores) if game.high_scores else 0
        highest_round = max(hs.round_reached for hs in game.high_scores) if game.high_scores else 0

        stats_text = f"Total Records: {total_scores} | Highest Score: {highest_score:,} | Highest Round: {highest_round}"
        stats_surface = game.small_font.render(stats_text, True, LIGHT_GRAY)
        stats_rect = stats_surface.get_rect(center=(game.screen_width // 2, stats_y))
        game.screen.blit(stats_surface, stats_rect)

        # Back hint
        hint = game.small_font.render("Press ESC to return", True, LIGHT_GRAY)
        hint_rect = hint.get_rect(center=(game.screen_width // 2, stats_y + int(26 * game.scale_factor)))
        game.screen.blit(hint, hint_rect)

    else:
        # No scores message with better styling
        no_scores_bg = pygame.Rect(game.screen_width // 2 - int(200 * game.scale_factor),
                                 int(280 * game.scale_factor),
                                 int(400 * game.scale_factor),
                                 int(80 * game.scale_factor))
        pygame.draw.rect(game.screen, DARK_GRAY, no_scores_bg)
        pygame.draw.rect(game.screen, WHITE, no_scores_bg, 2)

        no_scores = game.font.render("No high scores yet!", True, WHITE)
        no_scores_rect = no_scores.get_rect(center=(game.screen_width // 2, int(300 * game.scale_factor)))
        game.screen.blit(no_scores, no_scores_rect)

        hint = game.small_font.render("Press ESC to return", True, LIGHT_GRAY)
        hint_rect = hint.get_rect(center=(game.screen_width // 2, int(340 * game.scale_factor)))
        game.screen.blit(hint, hint_rect)

        encourage = game.small_font.render("Play a game to set your first record!", True, YELLOW)
        encourage_rect = encourage.get_rect(center=(game.screen_width // 2, int(330 * game.scale_factor)))
        game.screen.blit(encourage, encourage_rect)

    # Back instruction panel
    back_bg = pygame.Rect(game.screen_width // 2 - int(180 * game.scale_factor),
                         game.screen_height - int(80 * game.scale_factor),
                         int(360 * game.scale_factor),
                         int(36 * game.scale_factor))
    draw_panel(game.screen, back_bg, (20, 20, 40), GREEN, radius=10, border_width=2, with_shadow=True)
    back_text = game.small_font.render("ESC to return to main menu", True, GREEN)
    back_rect = back_text.get_rect(center=back_bg.center)
    game.screen.blit(back_text, back_rect)

def draw_game_over(game):
    game.screen.fill(BLACK)

    # Background decoration (static stars)
    import random
    random.seed(42)
    for i in range(20):
        x = random.randint(0, game.screen_width)
        y = random.randint(0, game.screen_height)
        size = random.randint(1, 3)
        alpha = random.randint(30, 100)
        star_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(star_surface, (*WHITE, alpha), (size, size), size)
        game.screen.blit(star_surface, (x, y))
    random.seed()

    # Game Over title with glow effect
    game_over = game.big_font.render("GAME OVER", True, RED)
    game_over_rect = game_over.get_rect(center=(game.screen_width // 2, int(80 * game.scale_factor)))

    # Glow effect for title
    for offset in [(2, 2), (-2, 2), (2, -2), (-2, -2), (0, 3), (0, -3), (3, 0), (-3, 0)]:
        glow_surface = game.big_font.render("GAME OVER", True, DARK_GRAY)
        glow_rect = glow_surface.get_rect(center=(game_over_rect.centerx + offset[0], game_over_rect.centery + offset[1]))
        game.screen.blit(glow_surface, glow_rect)

    game.screen.blit(game_over, game_over_rect)

    # Results panel
    panel_width = int(600 * game.scale_factor)
    panel_height = int(280 * game.scale_factor)
    panel_x = game.screen_width // 2 - panel_width // 2
    panel_y = int(140 * game.scale_factor)

    # Draw panel background with gradient effect
    pygame.draw.rect(game.screen, DARK_GRAY, (panel_x, panel_y, panel_width, panel_height))
    pygame.draw.rect(game.screen, YELLOW, (panel_x, panel_y, panel_width, panel_height), 3)

    # Panel header
    header_height = int(50 * game.scale_factor)
    pygame.draw.rect(game.screen, GRAY, (panel_x, panel_y, panel_width, header_height))
    pygame.draw.rect(game.screen, YELLOW, (panel_x, panel_y, panel_width, header_height), 3)

    header_text = game.font.render("FINAL RESULTS", True, YELLOW)
    header_rect = header_text.get_rect(center=(game.screen_width // 2, panel_y + header_height // 2))
    game.screen.blit(header_text, header_rect)

    # Results content
    content_y = panel_y + header_height + int(20 * game.scale_factor)
    line_spacing = int(35 * game.scale_factor)

    # Score (most prominent)
    score_text = game.big_font.render(f"SCORE: {game.score:,}", True, YELLOW)
    score_rect = score_text.get_rect(center=(game.screen_width // 2, content_y))
    game.screen.blit(score_text, score_rect)
    content_y += int(50 * game.scale_factor)

    # Game stats in two columns
    left_col_x = panel_x + int(80 * game.scale_factor)
    right_col_x = panel_x + int(320 * game.scale_factor)

    # Left column
    if game.game_mode.name == 'TIMED':
        time_text = game.font.render(f"Time Limit: {game.time_limit}s", True, WHITE)
        game.screen.blit(time_text, (left_col_x, content_y))

        mode_text = game.font.render("Mode: Timed", True, BLUE)
        game.screen.blit(mode_text, (left_col_x, content_y + line_spacing))
    else:
        round_text = game.font.render(f"Rounds: {game.round_num - 1}", True, WHITE)
        game.screen.blit(round_text, (left_col_x, content_y))

        mode_text = game.font.render("Mode: Endless", True, GREEN)
        game.screen.blit(mode_text, (left_col_x, content_y + line_spacing))

    # Right column
    difficulty_color = {
        1: GREEN,    # EASY
        2: YELLOW,   # MEDIUM
        3: ORANGE,   # HARD
        4: RED       # NIGHTMARE
    }.get(game.difficulty.value, WHITE)

    difficulty_text = game.font.render(f"Difficulty: {game.difficulty.name.capitalize()}", True, difficulty_color)
    game.screen.blit(difficulty_text, (right_col_x, content_y))

    final_speed = game.get_current_speed_multiplier()
    speed_text = game.font.render(f"Speed: {final_speed:.2f}x", True, PINK)
    game.screen.blit(speed_text, (right_col_x, content_y + line_spacing))

    # Performance evaluation
    eval_y = content_y + int(80 * game.scale_factor)

    # Calculate performance rating
    if game.game_mode.name == 'TIMED':
        performance_score = game.score / (game.time_limit * 10)
    else:
        performance_score = game.score / ((game.round_num - 1) * 100) if game.round_num > 1 else 0

    if performance_score > 3:
        rating = "LEGENDARY! 🌟"
        rating_color = YELLOW
    elif performance_score > 2:
        rating = "EXCELLENT! 🎯"
        rating_color = GREEN
    elif performance_score > 1:
        rating = "GOOD! 👍"
        rating_color = BLUE
    elif performance_score > 0.5:
        rating = "Not Bad! 😊"
        rating_color = WHITE
    else:
        rating = "Keep Trying! 💪"
        rating_color = GRAY

    rating_text = game.font.render(f"Performance: {rating}", True, rating_color)
    rating_rect = rating_text.get_rect(center=(game.screen_width // 2, eval_y))
    game.screen.blit(rating_text, rating_rect)

    # Name input section
    input_y = panel_y + panel_height + int(40 * game.scale_factor)

    # Name input label
    name_prompt = game.font.render("💾 Save Your Score", True, WHITE)
    name_rect = name_prompt.get_rect(center=(game.screen_width // 2, input_y))
    game.screen.blit(name_prompt, name_rect)

    # Name input box with better styling
    box_width = int(350 * game.scale_factor)
    box_height = int(45 * game.scale_factor)
    input_box = pygame.Rect(game.screen_width // 2 - box_width // 2, input_y + int(40 * game.scale_factor), box_width, box_height)

    # Input box with gradient effect
    if game.name_input_active:
        pygame.draw.rect(game.screen, WHITE, input_box)
        pygame.draw.rect(game.screen, GREEN, input_box, 3)
        # Animated border glow
        glow_alpha = int(128 + 127 * math.sin(pygame.time.get_ticks() * 0.01))
        glow_surface = pygame.Surface((box_width + 6, box_height + 6), pygame.SRCALPHA)
        pygame.draw.rect(glow_surface, (*GREEN, glow_alpha), (0, 0, box_width + 6, box_height + 6), 3)
        game.screen.blit(glow_surface, (input_box.x - 3, input_box.y - 3))
    else:
        pygame.draw.rect(game.screen, LIGHT_GRAY, input_box)
        pygame.draw.rect(game.screen, WHITE, input_box, 2)

    # Input text
    if game.player_name or game.name_input_active:
        display_text = game.player_name
        text_color = BLACK
    else:
        display_text = "Click here to enter name..."
        text_color = DARK_GRAY

    name_surface = game.font.render(display_text, True, text_color)
    text_y = input_box.y + (input_box.height - name_surface.get_height()) // 2
    game.screen.blit(name_surface, (input_box.x + 15, text_y))

    # Animated cursor
    if game.name_input_active:
        cursor_x = input_box.x + 15 + name_surface.get_width()
        cursor_y1 = input_box.y + 8
        cursor_y2 = input_box.y + input_box.height - 8
        if (pygame.time.get_ticks() // 400) % 2:
            pygame.draw.line(game.screen, BLACK, (cursor_x, cursor_y1), (cursor_x, cursor_y2), 3)

    # Instructions with icons
    instruction_y = input_box.y + box_height + int(30 * game.scale_factor)

    if game.player_name:
        submit_text = game.small_font.render("✅ Press ENTER to save score", True, GREEN)
    else:
        submit_text = game.small_font.render("👆 Click the box above and type your name", True, WHITE)
    submit_rect = submit_text.get_rect(center=(game.screen_width // 2, instruction_y))
    game.screen.blit(submit_text, submit_rect)

    menu_text = game.small_font.render("🏠 Press M to return to main menu", True, LIGHT_GRAY)
    menu_rect = menu_text.get_rect(center=(game.screen_width // 2, instruction_y + int(25 * game.scale_factor)))
    game.screen.blit(menu_text, menu_rect)

def draw_game(game):
    # Draw the game background with gradient and effects
    draw_background(game)
    
    # Handle screen flash effects if active
    flash_drawn = False
    
    # Handle hit flash effect (red)
    if hasattr(game, 'screen_flash_alpha') and game.screen_flash_alpha > 0:
        # Create a semi-transparent overlay for the flash effect
        flash_surface = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
        flash_color = game.screen_flash_color + (game.screen_flash_alpha,)
        flash_surface.fill(flash_color)
        game.screen.blit(flash_surface, (0, 0))
        
        # Decrease alpha for next frame to create fade effect
        game.screen_flash_alpha = max(0, game.screen_flash_alpha - 15)
        flash_drawn = True
    
    # Handle pipe warning flash effect (blue)
    if hasattr(game, 'pipe_warning_flash_alpha') and game.pipe_warning_flash_alpha > 0 and not flash_drawn:
        # Create a semi-transparent overlay for the pipe warning flash
        flash_surface = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
        flash_color = game.pipe_warning_flash_color + (game.pipe_warning_flash_alpha,)
        flash_surface.fill(flash_color)
        game.screen.blit(flash_surface, (0, 0))
        
        # Decrease alpha for next frame to create fade effect
        game.pipe_warning_flash_alpha = max(0, game.pipe_warning_flash_alpha - 10)
        flash_drawn = True
    
    # Handle explosion flash effect (orange/yellow) - has priority over other flashes
    if hasattr(game, 'explosion_flash_alpha') and game.explosion_flash_alpha > 0:
        # Create a semi-transparent overlay for the explosion flash
        flash_surface = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
        flash_color = game.explosion_flash_color + (game.explosion_flash_alpha,)
        flash_surface.fill(flash_color)
        game.screen.blit(flash_surface, (0, 0))
        
        # Decrease alpha for next frame to create fade effect (faster fade for dramatic effect)
        game.explosion_flash_alpha = max(0, game.explosion_flash_alpha - 20)
    
    # Draw obstacles
    for obs in getattr(game, 'obstacles', []):
        obs.draw(game.screen)
        
    # Draw pipe obstacles
    for pipe in getattr(game, 'pipe_obstacles', []):
        pipe.draw(game.screen)

    # Draw circles
    from circle_behavior import draw_circle
    for circle in game.circles:
        draw_circle(circle, game.screen)
    
    # Draw triangles
    for triangle in game.triangles:
        triangle.draw(game.screen)

    # Draw virtual cursor when grabbed and hide real cursor
    if hasattr(game, 'cursor_is_grabbed') and game.cursor_is_grabbed:
        pygame.mouse.set_visible(False)

        if hasattr(game, 'virtual_mouse_pos'):
            grabbed_pos = game.virtual_mouse_pos
            pygame.draw.circle(game.screen, (255, 255, 255), grabbed_pos, 12, 4)
            pygame.draw.circle(game.screen, (255, 255, 0), grabbed_pos, 8, 3)
            pygame.draw.circle(game.screen, (255, 0, 0), grabbed_pos, 4)
            font = pygame.font.Font(None, 24)
            text = font.render("GRABBED!", True, (255, 255, 255))
            text_rect = text.get_rect(center=(grabbed_pos[0], grabbed_pos[1] - 25))
            game.screen.blit(text, text_rect)
    elif hasattr(game, 'cursor_hidden') and game.cursor_hidden:
        # Cursor is hidden by triangle hit - keep it hidden
        pygame.mouse.set_visible(False)
    else:
        pygame.mouse.set_visible(True)
    
    # Draw click radius helper if enabled (but not when cursor is grabbed or hidden)
    if (game.accessibility.get('click_radius_helper', False) and 
        not (hasattr(game, 'cursor_is_grabbed') and game.cursor_is_grabbed) and
        not (hasattr(game, 'cursor_hidden') and game.cursor_hidden)):
        mouse_pos = pygame.mouse.get_pos()
        # Draw semi-transparent circle to show click area
        radius_surface = pygame.Surface((game.click_radius * 2, game.click_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(radius_surface, (255, 255, 255, 60), (game.click_radius, game.click_radius), game.click_radius, 2)
        pygame.draw.circle(radius_surface, (255, 255, 255, 30), (game.click_radius, game.click_radius), game.click_radius)
        
        # Center the circle on the mouse position
        radius_rect = radius_surface.get_rect(center=mouse_pos)
        game.screen.blit(radius_surface, radius_rect)

    margin = int(10 * game.scale_factor)
    
    # Draw heart-shaped lives counter
    heart_size = int(25 * game.scale_factor)
    spacing = int(8 * game.scale_factor)
    padding = int(8 * game.scale_factor)
    
    # Calculate total width and height needed
    total_hearts = 4
    total_width = (heart_size * total_hearts) + (spacing * (total_hearts - 1))
    total_height = heart_size
    
    # Create a surface for the hearts with exact size needed
    hearts_surface = pygame.Surface((total_width, total_height), pygame.SRCALPHA)
    
    # Draw hearts for each life
    for i in range(total_hearts):
        # Calculate position for this heart
        x = (heart_size + spacing) * i + (heart_size // 2)
        y = heart_size // 2
        
        # Heart color - red for lives, dark red for empty
        color = RED if i < game.lives else (100, 0, 0)
        
        # Draw heart shape using circles and triangles
        radius = heart_size // 2
        
        # Draw the two circles that form the top of the heart
        pygame.draw.circle(hearts_surface, color, 
                         (x - radius // 2, y - radius // 4), 
                         radius // 2)
        pygame.draw.circle(hearts_surface, color, 
                         (x + radius // 2, y - radius // 4), 
                         radius // 2)
        
        # Draw the triangle that forms the bottom of the heart
        points = [
            (x - radius, y - radius // 4),  # Left point
            (x + radius, y - radius // 4),  # Right point
            (x, y + radius * 0.9),          # Bottom point (slightly less than full radius)
        ]
        pygame.draw.polygon(hearts_surface, color, points)
    
    # Create background surface with exact padding
    bg_width = total_width + 2 * padding
    bg_height = total_height + 2 * padding
    bg_surface = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
    
    # Draw the background with rounded corners
    pygame.draw.rect(bg_surface, (0, 0, 0, 160), (0, 0, bg_width, bg_height), 
                    border_radius=int(5 * game.scale_factor))
    
    # Position the background container
    bg_rect = bg_surface.get_rect(topright=(game.screen_width - margin, margin))
    
    # Draw the background
    game.screen.blit(bg_surface, bg_rect)
    
    # Position the hearts in the center of the background
    hearts_rect = hearts_surface.get_rect(center=bg_rect.center)
    game.screen.blit(hearts_surface, hearts_rect)
    
    # Only draw rest of HUD if UI is visible
    if game.show_ui:
        # Score in top-left
        score_text = game.big_font.render(f"Score: {game.score}", True, YELLOW)
        game.screen.blit(score_text, (margin, margin))

        # Show time for timed mode, round for endless mode
        if game.game_mode.name == 'TIMED':
            time_color = RED if game.time_remaining <= 10 else YELLOW
            time_text = game.big_font.render(f"Time: {game.time_remaining:.1f}s", True, time_color)
            game.screen.blit(time_text, (margin, margin + int(50 * game.scale_factor)))

            mode_text = game.small_font.render("Timed Mode", True, YELLOW)
            game.screen.blit(mode_text, (margin, margin + int(100 * game.scale_factor)))
        else:
            round_text = game.font.render(f"Round: {game.round_num}", True, WHITE)
            game.screen.blit(round_text, (margin, margin + int(50 * game.scale_factor)))

            mode_text = game.small_font.render("Endless Mode", True, WHITE)
            game.screen.blit(mode_text, (margin, margin + int(80 * game.scale_factor)))

        difficulty_text = game.small_font.render(f"Difficulty: {game.difficulty.name.capitalize()}", True, WHITE)
        difficulty_y = int(130 * game.scale_factor) if game.game_mode.name == 'TIMED' else int(110 * game.scale_factor)
        game.screen.blit(difficulty_text, (margin, margin + difficulty_y))

        # Speed multiplier display
        current_speed = game.get_current_speed_multiplier()
        speed_text = game.small_font.render(f"Speed: {current_speed:.2f}x", True, YELLOW)
        speed_y = int(150 * game.scale_factor) if game.game_mode.name == 'TIMED' else int(130 * game.scale_factor)
        game.screen.blit(speed_text, (margin, margin + speed_y))
        
        # Quick pipe mode indicator
        if game.force_quick_pipes:
            quick_pipe_text = game.small_font.render("QUICK PIPE MODE", True, RED)
            quick_pipe_y = speed_y + int(20 * game.scale_factor)
            game.screen.blit(quick_pipe_text, (margin, margin + quick_pipe_y))

        circles_left = len([c for c in game.circles if not c.dying]) + game.circles_to_spawn
        circles_text = game.font.render(f"Circles Left: {circles_left}", True, WHITE)
        # Adjust position based on whether quick pipe mode is active
        base_circles_y = int(180 * game.scale_factor) if game.game_mode.name == 'TIMED' else int(160 * game.scale_factor)
        circles_y = base_circles_y + (int(20 * game.scale_factor) if game.force_quick_pipes else 0)
        game.screen.blit(circles_text, (margin, margin + circles_y))

        # Controls hint
        controls_text = game.small_font.render("ESC: End Game | TAB: Toggle UI | V: Volume Controls", True, LIGHT_GRAY)
        game.screen.blit(controls_text, (margin, game.screen_height - int(90 * game.scale_factor)))

        # Volume controls display
        if game.show_volume_help:
            volume_bg = pygame.Rect(margin, game.screen_height - int(300 * game.scale_factor), int(400 * game.scale_factor), int(150 * game.scale_factor))
            pygame.draw.rect(game.screen, (0, 0, 0, 180), volume_bg)
            pygame.draw.rect(game.screen, WHITE, volume_bg, 2)

            vol_y = game.screen_height - int(290 * game.scale_factor)
            vol_title = game.font.render("VOLUME CONTROLS", True, YELLOW)
            game.screen.blit(vol_title, (margin + 10, vol_y))

            vol_y += int(30 * game.scale_factor)
            master_text = game.small_font.render(f"Master: {game.master_volume:.1f} (UP/DOWN)", True, WHITE)
            game.screen.blit(master_text, (margin + 10, vol_y))

            vol_y += int(25 * game.scale_factor)
            tank_text = game.small_font.render(f"Tank: {game.tank_volume:.1f} (LEFT/RIGHT)", True, WHITE)
            game.screen.blit(tank_text, (margin + 10, vol_y))

            vol_y += int(25 * game.scale_factor)
            effects_text = game.small_font.render(f"Effects: {game.effects_volume:.1f}", True, WHITE)
            game.screen.blit(effects_text, (margin + 10, vol_y))

            vol_y += int(25 * game.scale_factor)
            help_text = game.small_font.render("Press V to close", True, LIGHT_GRAY)
            game.screen.blit(help_text, (margin + 10, vol_y))

        # FPS display
        current_fps = game.clock.get_fps()
        fps_text = game.small_font.render(f"FPS: {current_fps:.0f}/{game.target_fps}", True, LIGHT_GRAY)
        game.screen.blit(fps_text, (margin, game.screen_height - int(110 * game.scale_factor)))

        # Fullscreen indicator
        mode_text = game.small_font.render(f"Mode: {'Fullscreen' if game.fullscreen else 'Windowed'} (F11 to toggle)", True, WHITE)
        game.screen.blit(mode_text, (margin, game.screen_height - int(70 * game.scale_factor)))

        # Show speed increase notification for endless mode
        if game.game_mode.name == 'ENDLESS' and game.round_num > 1:
            speed_info = game.small_font.render("Speed increases each round!", True, YELLOW)
            game.screen.blit(speed_info, (margin, game.screen_height - int(50 * game.scale_factor)))
    else:
        # Show minimal UI toggle hint when UI is hidden
        hint_text = game.small_font.render("Press TAB to show UI", True, LIGHT_GRAY)
        hint_rect = hint_text.get_rect(center=(game.screen_width // 2, int(30 * game.scale_factor)))
        game.screen.blit(hint_text, hint_rect)

def draw_accessibility_menu(game):
    """Draw accessibility menu with new panel/button style and selection highlight."""
    # Background + vignette
    draw_background(game)
    draw_vignette(game.screen, intensity=100)

    # Title
    draw_text_with_glow(
        game.screen,
        "Accessibility Options",
        game.big_font,
        WHITE,
        (120, 120, 160),
        (game.screen_width // 2, int(100 * game.scale_factor)),
        glow_size=8,
        glow_alpha=70,
    )

    # Options
    options = [
        {"key": "pipe_warning_flash", "label": "Pipe Warning Flash", "description": "Flash before pipes spawn"},
        {"key": "dynamic_background", "label": "Dynamic Star Background", "description": "Animated stars background"},
        {"key": "click_radius_helper", "label": "Click Radius Helper", "description": "Show/adjust click radius (+/-)"},
        {"key": "disable_pipes", "label": "Disable Pipes", "description": "Turn off pipe obstacles"},
        {"key": "disable_spinners", "label": "Disable Spinners", "description": "Turn off spinner obstacles"},
        {"key": "music_enabled", "label": "Background Music", "description": "Toggle music on/off"},
    ]

    btn_w = int(720 * game.scale_factor)
    btn_h = int(56 * game.scale_factor)
    spacing = int(10 * game.scale_factor)
    start_y = int(180 * game.scale_factor)
    x = game.screen_width // 2 - btn_w // 2

    # Panel around options
    panel_h = len(options) * (btn_h + spacing) - spacing + int(24 * game.scale_factor)
    panel_rect = pygame.Rect(x - int(16 * game.scale_factor), start_y - int(12 * game.scale_factor), btn_w + int(32 * game.scale_factor), panel_h)
    draw_panel(game.screen, panel_rect, (18, 20, 32), LIGHT_BLUE, radius=14, border_width=2, with_shadow=True)

    # Build rect list and draw rows
    game.accessibility_option_rects = []
    y = start_y
    for idx, opt in enumerate(options):
        rect = pygame.Rect(x, y, btn_w, btn_h)
        raw_value = game.accessibility.get(opt["key"], False)
        is_selected = (idx == game.accessibility_menu_index)

        # Friendly label + state mapping
        label_text = opt['label']
        pill_text = "ON" if raw_value else "OFF"
        pill_color = GREEN if raw_value else RED

        if opt['key'] == 'disable_pipes':
            label_text = 'Pipes'
            # raw_value True means disabled
            pill_text = 'Disabled' if raw_value else 'Enabled'
            pill_color = RED if raw_value else GREEN
        elif opt['key'] == 'disable_spinners':
            label_text = 'Spinners'
            pill_text = 'Disabled' if raw_value else 'Enabled'
            pill_color = RED if raw_value else GREEN

        # Row background with friendly label
        draw_menu_button(game, rect, label_text, hover=is_selected)

        # Status pill on right
        pill_w = int(120 * game.scale_factor)
        pill_h = int(28 * game.scale_factor)
        pill_rect = pygame.Rect(rect.right - pill_w - int(12 * game.scale_factor), rect.centery - pill_h // 2, pill_w, pill_h)
        draw_panel(game.screen, pill_rect, pill_color, WHITE, radius=pill_h // 2, border_width=1, with_shadow=False)
        pill_label = game.small_font.render(pill_text, True, BLACK)
        game.screen.blit(pill_label, pill_label.get_rect(center=pill_rect.center))

        # Store for input hit testing
        game.accessibility_option_rects.append((rect, opt['key']))
        y += btn_h + spacing

    # Footer instructions
    # Single-line description for selected option (less clutter)
    sel = options[game.accessibility_menu_index % len(options)] if options else None
    if sel:
        desc_bg = pygame.Rect(panel_rect.left, panel_rect.bottom + int(10 * game.scale_factor), panel_rect.width, int(34 * game.scale_factor))
        draw_panel(game.screen, desc_bg, (20, 22, 34), LIGHT_BLUE, radius=10, border_width=1, with_shadow=False)
        desc_surf = game.small_font.render(sel['description'], True, LIGHT_GRAY)
        game.screen.blit(desc_surf, desc_surf.get_rect(center=desc_bg.center))

    footer_y = (desc_bg.bottom if sel else panel_rect.bottom) + int(18 * game.scale_factor)
    for line in ("UP/DOWN to navigate • ENTER/SPACE/CLICK to toggle", "ESC to return to menu"):
        surf = game.small_font.render(line, True, LIGHT_GRAY)
        game.screen.blit(surf, surf.get_rect(center=(game.screen_width // 2, footer_y)))
        footer_y += int(22 * game.scale_factor)

def draw_sandbox(game):
    """Draw sandbox mode interface with keybind instructions"""
    game.screen.fill(BLACK)
    
    # Handle screen flash effects if active (same as in draw_game)
    flash_drawn = False
    
    # Handle hit flash effect (red)
    if hasattr(game, 'screen_flash_alpha') and game.screen_flash_alpha > 0:
        flash_surface = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
        flash_color = game.screen_flash_color + (game.screen_flash_alpha,)
        flash_surface.fill(flash_color)
        game.screen.blit(flash_surface, (0, 0))
        game.screen_flash_alpha = max(0, game.screen_flash_alpha - 15)
        flash_drawn = True
    
    # Handle pipe warning flash effect (blue)
    if hasattr(game, 'pipe_warning_flash_alpha') and game.pipe_warning_flash_alpha > 0 and not flash_drawn:
        flash_surface = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
        flash_color = game.pipe_warning_flash_color + (game.pipe_warning_flash_alpha,)
        flash_surface.fill(flash_color)
        game.screen.blit(flash_surface, (0, 0))
        game.pipe_warning_flash_alpha = max(0, game.pipe_warning_flash_alpha - 10)
    
    # Handle explosion flash effect (orange/yellow) - has priority over other flashes
    if hasattr(game, 'explosion_flash_alpha') and game.explosion_flash_alpha > 0:
        # Create a semi-transparent overlay for the explosion flash
        flash_surface = pygame.Surface((game.screen_width, game.screen_height), pygame.SRCALPHA)
        flash_color = game.explosion_flash_color + (game.explosion_flash_alpha,)
        flash_surface.fill(flash_color)
        game.screen.blit(flash_surface, (0, 0))
        
        # Decrease alpha for next frame to create fade effect (faster fade for dramatic effect)
        game.explosion_flash_alpha = max(0, game.explosion_flash_alpha - 20)

    # Draw obstacles
    for obs in getattr(game, 'obstacles', []):
        obs.draw(game.screen)
        
    # Draw pipe obstacles
    for pipe in getattr(game, 'pipe_obstacles', []):
        pipe.draw(game.screen)

    # Draw circles first
    from circle_behavior import draw_circle
    for circle in game.circles:
        draw_circle(circle, game.screen)
    
    # Draw triangles
    for triangle in game.triangles:
        triangle.draw(game.screen)

    # Draw virtual cursor when grabbed
    if hasattr(game, 'cursor_is_grabbed') and game.cursor_is_grabbed:
        pygame.mouse.set_visible(False)

        if hasattr(game, 'virtual_mouse_pos'):
            grabbed_pos = game.virtual_mouse_pos
            pygame.draw.circle(game.screen, (255, 255, 255), grabbed_pos, 12, 4)
            pygame.draw.circle(game.screen, (255, 255, 0), grabbed_pos, 8, 3)
            pygame.draw.circle(game.screen, (255, 0, 0), grabbed_pos, 4)
            font = pygame.font.Font(None, 24)
            text = font.render("GRABBED!", True, (255, 255, 255))
            text_rect = text.get_rect(center=(grabbed_pos[0], grabbed_pos[1] - 25))
            game.screen.blit(text, text_rect)
    elif hasattr(game, 'cursor_hidden') and game.cursor_hidden:
        # Cursor is hidden by triangle hit - keep it hidden
        pygame.mouse.set_visible(False)
    else:
        pygame.mouse.set_visible(True)
    
    # Draw click radius helper if enabled (but not when cursor is grabbed or hidden)
    if (game.accessibility.get('click_radius_helper', False) and 
        not (hasattr(game, 'cursor_is_grabbed') and game.cursor_is_grabbed) and
        not (hasattr(game, 'cursor_hidden') and game.cursor_hidden)):
        mouse_pos = pygame.mouse.get_pos()
        # Draw semi-transparent circle to show click area
        radius_surface = pygame.Surface((game.click_radius * 2, game.click_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(radius_surface, (255, 255, 255, 60), (game.click_radius, game.click_radius), game.click_radius, 2)
        pygame.draw.circle(radius_surface, (255, 255, 255, 30), (game.click_radius, game.click_radius), game.click_radius)
        
        # Center the circle on the mouse position
        radius_rect = radius_surface.get_rect(center=mouse_pos)
        game.screen.blit(radius_surface, radius_rect)

    # Only draw UI if visible
    if game.show_ui:
        margin = int(10 * game.scale_factor)

        # Title
        title = game.big_font.render("SANDBOX MODE", True, YELLOW)
        game.screen.blit(title, (margin, margin))

        # Score (just for visual feedback)
        score_text = game.font.render(f"Score: {game.score}", True, WHITE)
        game.screen.blit(score_text, (margin, margin + int(50 * game.scale_factor)))
        
        # Quick pipe mode indicator
        if game.force_quick_pipes:
            quick_pipe_text = game.small_font.render("QUICK PIPE MODE", True, RED)
            game.screen.blit(quick_pipe_text, (margin, margin + int(75 * game.scale_factor)))

        # Spawn controls
        y = margin + int(100 * game.scale_factor) + (int(25 * game.scale_factor) if game.force_quick_pipes else 0)
        spawn_title = game.font.render("Spawn Circles:", True, YELLOW)
        game.screen.blit(spawn_title, (margin, y))

        y += int(30 * game.scale_factor)
        keybinds = [
            "1 - Normal (Red)",
            "2 - Fast (Blue)",
            "3 - Teleporting (Purple)",
            "4 - Shrinking (Orange)",
            "5 - Small (Yellow)",
            "6 - Ghost (Gray)",
            "7 - Tank (Dark Gray)",
            "8 - Supertank (Red Glow)",
            "9 - Hexagon (Magenta)",
            "0 - Cursor Grabber (Pink)",
            "S - Snake (Green)",
            "O - Spinning Obstacle (Red)",
            "P - Pipe Obstacle (Green)"
        ]

        for keybind in keybinds:
            text = game.small_font.render(keybind, True, WHITE)
            game.screen.blit(text, (margin, y))
            y += int(20 * game.scale_factor)

        # Controls
        y += int(20 * game.scale_factor)
        controls_title = game.font.render("Controls:", True, YELLOW)
        game.screen.blit(controls_title, (margin, y))

        y += int(30 * game.scale_factor)
        controls = [
            "C - Clear all (circles & obstacles)",
            "P/SPACE - Pause/Resume movement",
            "CTRL+Q - Toggle Quick Pipe Mode",
            "TAB - Toggle UI",
            "ESC - Return to main menu"
        ]
        
        # Add click radius controls if accessibility feature is enabled
        if game.accessibility.get('click_radius_helper', False):
            controls.insert(-2, "+/- - Adjust Click Radius")

        for control in controls:
            text = game.small_font.render(control, True, WHITE)
            game.screen.blit(text, (margin, y))
            y += int(20 * game.scale_factor)

        # Circle count and pause status
        circle_count = len([c for c in game.circles if not c.dying])
        count_text = game.font.render(f"Active Circles: {circle_count}", True, GREEN)
        game.screen.blit(count_text, (margin, game.screen_height - int(120 * game.scale_factor)))

        # Pause status indicator
        pause_status = "PAUSED" if game.sandbox_paused else "RUNNING"
        pause_color = RED if game.sandbox_paused else GREEN
        pause_text = game.font.render(f"Status: {pause_status}", True, pause_color)
        game.screen.blit(pause_text, (margin, game.screen_height - int(100 * game.scale_factor)))

        # Instructions
        instructions = game.small_font.render("Click circles to destroy them!", True, LIGHT_GRAY)
        game.screen.blit(instructions, (margin, game.screen_height - int(60 * game.scale_factor)))
    else:
        # Show minimal UI toggle hint when UI is hidden
        hint_text = game.small_font.render("Press TAB to show controls", True, LIGHT_GRAY)
        hint_rect = hint_text.get_rect(center=(game.screen_width // 2, int(30 * game.scale_factor)))
        game.screen.blit(hint_text, hint_rect)

        # Always show sandbox mode indicator
        mode_text = game.font.render("SANDBOX MODE", True, YELLOW)
        mode_rect = mode_text.get_rect(center=(game.screen_width // 2, int(60 * game.scale_factor)))
        game.screen.blit(mode_text, mode_rect)

    # Always show pause status when paused (even with UI hidden)
    if game.sandbox_paused:
        pause_overlay = game.big_font.render("PAUSED", True, RED)
        pause_rect = pause_overlay.get_rect(center=(game.screen_width // 2, game.screen_height // 2))

        # Add background for better visibility
        bg_width = pause_rect.width + int(40 * game.scale_factor)
        bg_height = pause_rect.height + int(20 * game.scale_factor)
        bg_rect = pygame.Rect(pause_rect.centerx - bg_width // 2, pause_rect.centery - bg_height // 2, bg_width, bg_height)
        pygame.draw.rect(game.screen, (0, 0, 0, 180), bg_rect)
        pygame.draw.rect(game.screen, RED, bg_rect, 3)

        game.screen.blit(pause_overlay, pause_rect)

        # Show pause controls
        controls_text = game.small_font.render("Press P or SPACE to resume", True, WHITE)
        controls_rect = controls_text.get_rect(center=(game.screen_width // 2, pause_rect.bottom + int(30 * game.scale_factor)))
        game.screen.blit(controls_text, controls_rect)

def draw_click_radius_tutorial_popup(game):
    """Draw the click radius helper tutorial popup"""
    if not game.show_click_radius_tutorial:
        return
    
    # Create full black overlay
    overlay = pygame.Surface((game.screen_width, game.screen_height))
    overlay.set_alpha(220)  # More opaque for better contrast
    overlay.fill(BLACK)
    game.screen.blit(overlay, (0, 0))
    
    # Tutorial popup dimensions - made larger to fit content properly
    popup_width = int(700 * game.scale_factor)
    popup_height = int(400 * game.scale_factor)
    popup_x = game.screen_width // 2 - popup_width // 2
    popup_y = game.screen_height // 2 - popup_height // 2
    
    # Draw popup background with border
    pygame.draw.rect(game.screen, DARK_GRAY, (popup_x, popup_y, popup_width, popup_height))
    pygame.draw.rect(game.screen, LIGHT_BLUE, (popup_x, popup_y, popup_width, popup_height), 3)
    
    # Title
    title_text = game.big_font.render("Click Radius Helper Enabled!", True, LIGHT_BLUE)
    title_rect = title_text.get_rect(center=(game.screen_width // 2, popup_y + int(35 * game.scale_factor)))
    game.screen.blit(title_text, title_rect)
    
    # Tutorial content - positioned within the popup bounds
    content_start_y = popup_y + int(75 * game.scale_factor)
    line_height = int(28 * game.scale_factor)  # Reduced line height to fit better
    content_x = popup_x + int(30 * game.scale_factor)  # Left margin inside popup
    
    tutorial_lines = [
        "How to use the Click Radius Helper:",
        "• A semi-transparent circle shows around your cursor",
        "• This circle shows your effective click area",
        "• You can click circles when they touch this area",
        "",
        "Controls:",
        "• Press + (equals key) to increase radius",
        "• Press - (minus key) to decrease radius",
        "• Radius ranges from 10px to 100px"
    ]
    
    current_y = content_start_y
    for line in tutorial_lines:
        if line == "":
            current_y += int(10 * game.scale_factor)  # Small gap for empty lines
            continue
        
        # Use different colors and positioning for different types of content
        if line.startswith("How to use") or line.startswith("Controls:"):
            color = YELLOW
            font = game.font
            x_pos = content_x
        elif line.startswith("•"):
            color = WHITE
            font = game.small_font
            x_pos = content_x + int(20 * game.scale_factor)  # Indent bullet points
        else:
            color = LIGHT_GRAY
            font = game.small_font
            x_pos = content_x
        
        text = font.render(line, True, color)
        game.screen.blit(text, (x_pos, current_y))
        current_y += line_height
    
    # Instructions and countdown timer - positioned at bottom of popup
    remaining_time = game.click_radius_tutorial_duration - (time.time() - game.click_radius_tutorial_start_time)
    remaining_time = max(0, remaining_time)
    
    # Instructions to close
    close_text = game.small_font.render("Press any key to close this popup", True, LIGHT_BLUE)
    close_rect = close_text.get_rect(center=(game.screen_width // 2, popup_y + popup_height - int(45 * game.scale_factor)))
    game.screen.blit(close_text, close_rect)
    
    # Countdown timer
    timer_text = game.small_font.render(f"Auto-close in {remaining_time:.1f} seconds", True, GRAY)
    timer_rect = timer_text.get_rect(center=(game.screen_width // 2, popup_y + popup_height - int(25 * game.scale_factor)))
    game.screen.blit(timer_text, timer_rect)
