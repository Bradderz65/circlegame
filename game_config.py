import pygame
import math
import numpy as np
import os
import subprocess

# Try to import system cursor control libraries
try:
    import ctypes
    from ctypes import wintypes
    WINDOWS_CURSOR_CONTROL = True
except ImportError:
    WINDOWS_CURSOR_CONTROL = False

try:
    import subprocess
    LINUX_CURSOR_CONTROL = True
except ImportError:
    LINUX_CURSOR_CONTROL = False

# Initialize Pygame
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Base resolution for scaling calculations
BASE_WIDTH = 1200
BASE_HEIGHT = 800

# Default window size (can be changed)
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 800
TARGET_FPS = 165  # Target FPS, will be adjusted based on monitor capability

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
PINK = (255, 192, 203)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (64, 64, 64)
LIGHT_BLUE = (173, 216, 230)

# Background gradient colors
DARK_BLUE = (8, 24, 58)
DEEP_PURPLE = (16, 6, 54)
NAVY_BLUE = (4, 14, 35)
MIDNIGHT_BLUE = (2, 6, 23)

# Advanced Sound generation functions (inspired by Web Audio API)
def generate_advanced_sound(sound_type, duration=0.2, sample_rate=22050, volume=0.1):
    """Generate advanced sound effects with frequency ramping like Web Audio API"""
    frames = int(duration * sample_rate)
    arr = np.zeros((frames, 2), dtype=np.int16)

    for i in range(frames):
        t = i / sample_rate
        progress = i / frames

        # Different sound types with frequency ramping
        if sound_type == 'coin':
            # Coin: 1000Hz -> 2000Hz -> 1500Hz (like the website)
            if progress < 0.5:
                freq = 1000 + (1000 * progress * 2)  # 1000 to 2000
            else:
                freq = 2000 - (500 * (progress - 0.5) * 2)  # 2000 to 1500
            wave_type = 'square'
        elif sound_type == 'button':
            # Button: 800Hz -> 400Hz (like the website)
            freq = 800 - (400 * progress)
            wave_type = 'square'
        elif sound_type == 'powerup':
            # Powerup: 200Hz -> 800Hz (like the website)
            freq = 200 + (600 * progress)
            wave_type = 'square'
        elif sound_type == 'laser':
            # Laser: 1500Hz -> 100Hz (like the website)
            freq = 1500 - (1400 * progress)
            wave_type = 'square'
        elif sound_type == 'explosion':
            # Explosion: 300Hz -> 50Hz with sawtooth (like the website)
            freq = 300 - (250 * progress)
            wave_type = 'sawtooth'
        elif sound_type == 'tank_hit':
            # Tank hit: Menacing low-mid range with pulsing effect
            base_freq = 120 + (180 * math.sin(progress * 8))  # Pulsing 120-300Hz
            freq = base_freq * (1 + 0.3 * math.sin(progress * 16))  # Double pulse
            wave_type = 'sawtooth'
        elif sound_type == 'supertank_hit':
            # Supertank hit: Even more aggressive with deeper bass
            base_freq = 80 + (220 * math.sin(progress * 10))  # Pulsing 80-300Hz
            freq = base_freq * (1 + 0.5 * math.sin(progress * 20))  # Intense pulse
            wave_type = 'sawtooth'
        elif sound_type == 'tank_death':
            # Tank death: Dramatic descending roar
            freq = 400 - (350 * progress) + (50 * math.sin(progress * 12))
            wave_type = 'sawtooth'
        elif sound_type == 'supertank_death':
            # Supertank death: Epic bass rumble with chaotic elements
            base_freq = 500 - (450 * progress)  # 500Hz to 50Hz
            chaos = 30 * math.sin(progress * 25) * math.sin(progress * 37)  # Chaotic harmonics
            freq = base_freq + chaos
            wave_type = 'sawtooth'
        elif sound_type == 'tank_hum':
            # Tank whump: Rhythmic pulsing bass like an engine
            freq = 120  # 120Hz bass tone
            wave_type = 'sine'
        elif sound_type == 'supertank_hum':
            # Supertank whump: Deeper rhythmic pulsing bass
            freq = 90   # 90Hz deeper bass tone
            wave_type = 'sine'
        elif sound_type == 'hit':
            # Hit sound: Quick, sharp impact
            freq = 800 - (700 * progress)  # 800Hz to 100Hz
            wave_type = 'square'
        elif sound_type == 'explosion':
            # Explosion: Deep, rumbling explosion
            base_freq = 150 - (130 * progress)  # 150Hz to 20Hz
            freq = base_freq * (1 + 0.2 * math.sin(progress * 30))  # Add some rumble
            wave_type = 'sawtooth'
        elif sound_type == 'beep':
            # Beep: Clean, sharp warning tone
            freq = 1200  # High-pitched 1200Hz tone
            wave_type = 'sine'
        else:
            freq = 440
            wave_type = 'square'

        # Generate waveform
        if wave_type == 'square':
            wave = 1 if math.sin(freq * 2 * math.pi * t) > 0 else -1
        elif wave_type == 'sawtooth':
            wave = 2 * (freq * t - math.floor(freq * t + 0.5))
        else:  # sine
            wave = math.sin(freq * 2 * math.pi * t)

        # Apply volume envelope (exponential decay like Web Audio API)
        # Special case for tank whump sounds - rhythmic pulsing
        if sound_type in ['tank_hum', 'supertank_hum']:
            # Create a whump effect: quiet -> louder -> quiet in cycles
            pulse_frequency = 1.2 if sound_type == 'tank_hum' else 0.8  # Different pulse rates
            pulse_cycle = (t * pulse_frequency) % 1.0  # 0 to 1 cycle

            # Create whump shape: starts quiet, peaks in middle, goes quiet
            if pulse_cycle < 0.3:
                # Rising phase: quiet to loud
                whump_intensity = pulse_cycle / 0.3
            elif pulse_cycle < 0.7:
                # Peak phase: loud
                whump_intensity = 1.0
            else:
                # Falling phase: loud to quiet
                whump_intensity = 1.0 - ((pulse_cycle - 0.7) / 0.3)

            # Apply smooth curve and minimum volume
            min_volume = 0.5  # Never completely silent - higher minimum
            whump_intensity = min_volume + (1.0 - min_volume) * (whump_intensity ** 2)
            envelope = volume * whump_intensity
        else:
            envelope = math.exp(-progress * 3) * volume
        amplitude = int(4096 * wave * envelope)
        arr[i] = [amplitude, amplitude]

    sound = pygame.sndarray.make_sound(arr)
    return sound

def generate_collision_sound():
    """Generate a collision sound effect (button style)"""
    return generate_advanced_sound('button', 0.1, volume=0.15)

def generate_spawn_sound():
    """Generate a spawn sound effect (powerup style)"""
    return generate_advanced_sound('powerup', 0.2, volume=0.1)

def generate_death_sound():
    """Generate a death/explosion sound effect"""
    return generate_advanced_sound('explosion', 0.3, volume=0.12)

def generate_game_over_sound():
    """Generate a game over sound effect (laser style)"""
    return generate_advanced_sound('laser', 0.5, volume=0.15)

def generate_coin_sound():
    """Generate a coin insert sound effect"""
    return generate_advanced_sound('coin', 0.3, volume=0.2)

def generate_tank_hit_sound():
    """Generate a menacing tank hit sound with pulsing effect"""
    return generate_advanced_sound('tank_hit', 0.15, volume=0.18)

def generate_supertank_hit_sound():
    """Generate an even more menacing supertank hit sound"""
    return generate_advanced_sound('supertank_hit', 0.2, volume=0.2)

def generate_tank_death_sound():
    """Generate a dramatic tank death sound"""
    return generate_advanced_sound('tank_death', 0.4, volume=0.16)

def generate_supertank_death_sound():
    """Generate an epic supertank death sound"""
    return generate_advanced_sound('supertank_death', 0.6, volume=0.35)

def generate_tank_hum_sound():
    """Generate a continuous deep humming sound for tanks"""
    return generate_advanced_sound('tank_hum', 2.0, volume=0.6)

def generate_supertank_hum_sound():
    """Generate a more intense continuous humming sound for supertanks"""
    return generate_advanced_sound('supertank_hum', duration=0.5, volume=0.4)

def generate_hit_sound():
    """Generate a sound for when the player is hit by an obstacle"""
    return generate_advanced_sound('hit', duration=0.3, volume=0.5)

def generate_explosion_sound():
    """Generate an explosion sound for when an obstacle is destroyed"""
    return generate_advanced_sound('explosion', duration=0.4, volume=0.7)

def generate_beep_sound():
    """Generate a beep sound for supertank self-destruct warning"""
    return generate_advanced_sound('beep', duration=0.1, volume=0.3)

def set_system_cursor_pos(x, y):
    """Set cursor position using system-level calls for more reliable control"""
    try:
        # First try pygame method
        pygame.mouse.set_pos(int(x), int(y))

        # Try Windows-specific cursor control
        if WINDOWS_CURSOR_CONTROL and os.name == 'nt':
            try:
                # Get screen coordinates (pygame uses window coordinates)
                window_rect = pygame.display.get_surface().get_rect()
                window_pos = pygame.display.get_wm_info()

                # Convert to screen coordinates
                screen_x = int(x + (window_pos.get('window', {}).get('x', 0) if window_pos else 0))
                screen_y = int(y + (window_pos.get('window', {}).get('y', 0) if window_pos else 0))

                # Use Windows API to set cursor position
                ctypes.windll.user32.SetCursorPos(screen_x, screen_y)
                return True
            except:
                pass

        # Try Linux-specific cursor control
        elif LINUX_CURSOR_CONTROL and os.name == 'posix':
            try:
                # Use xdotool to move cursor (if available)
                subprocess.run(['xdotool', 'mousemove', str(int(x)), str(int(y))],
                             check=True, capture_output=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    # Alternative: use xinput if available
                    subprocess.run(['xinput', 'set-prop', 'pointer:', 'Coordinate Transformation Matrix',
                                  '1', '0', str(int(x)), '0', '1', str(int(y)), '0', '0', '1'],
                                 check=True, capture_output=True)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
    except Exception as e:
        print(f"Cursor control failed: {e}")

    return False

# Initialize sounds
try:
    COLLISION_SOUND = generate_collision_sound()
    SPAWN_SOUND = generate_spawn_sound()
    DEATH_SOUND = generate_death_sound()
    GAME_OVER_SOUND = generate_game_over_sound()
    COIN_SOUND = generate_coin_sound()
    TANK_HIT_SOUND = generate_tank_hit_sound()
    SUPERTANK_HIT_SOUND = generate_supertank_hit_sound()
    TANK_DEATH_SOUND = generate_tank_death_sound()
    SUPERTANK_DEATH_SOUND = generate_supertank_death_sound()
    TANK_HUM_SOUND = generate_tank_hum_sound()
    SUPERTANK_HUM_SOUND = generate_supertank_hum_sound()
    HIT_SOUND = generate_hit_sound()
    EXPLOSION_SOUND = generate_explosion_sound()
    BEEP_SOUND = generate_beep_sound()
except:
    # Fallback if sound generation fails
    COLLISION_SOUND = None
    SPAWN_SOUND = None
    DEATH_SOUND = None
    GAME_OVER_SOUND = None
    COIN_SOUND = None
    TANK_HIT_SOUND = None
    SUPERTANK_HIT_SOUND = None
    TANK_DEATH_SOUND = None
    SUPERTANK_DEATH_SOUND = None
    TANK_HUM_SOUND = None
    SUPERTANK_HUM_SOUND = None
    HIT_SOUND = None
    EXPLOSION_SOUND = None
    BEEP_SOUND = None

# Global game instance for volume control
GAME_INSTANCE = None

def play_sound(sound, sound_type='effects', game=None):
    """Safely play a sound with volume control"""
    if sound:
        try:
            # Use provided game instance or global instance
            game_ref = game or GAME_INSTANCE

            if game_ref:
                # Calculate final volume based on type and master volume
                if sound_type == 'tank':
                    volume = game_ref.master_volume * game_ref.tank_volume
                else:
                    volume = game_ref.master_volume * game_ref.effects_volume

                # Set volume and play
                sound.set_volume(volume)

            sound.play()
        except:
            pass