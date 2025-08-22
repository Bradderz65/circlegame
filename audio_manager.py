import os
import random
import pygame
import math

class AudioManager:
    def __init__(self, game):
        self.game = game
        self.music_volume = 0.15  # Target volume (0.0 to 1.0)
        self.current_volume = 0.0  # Current actual volume (for fading)
        self.fade_speed = 0.1  # How fast to fade in/out (volume units per second)
        self.fade_target_volume = 0.0  # Volume we're fading to
        self.fading_out = False  # Whether we're currently fading out
        self.next_track = None  # Next track to play after fade out
        self.next_track_loop = False  # Whether to loop the next track
        
        # Music state
        self.current_track = None
        self.game_tracks = []
        self.current_track_index = 0
        self.is_playing_menu_music = False
        
        # Initialize pygame mixer with higher buffer for smoother playback
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        
        # Load music tracks
        self.load_music()
    
    def load_music(self):
        """Load all music files from the assets folder"""
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        
        # Menu music (first track)
        self.menu_track = os.path.join(assets_dir, 'Neon Stillness.mp3')
        
        # Game music tracks (other tracks)
        self.game_tracks = [
            os.path.join(assets_dir, 'Echoes in the Void.mp3'),
            os.path.join(assets_dir, 'Neon Currents.mp3')
        ]
        
        # Shuffle the game tracks for random order
        random.shuffle(self.game_tracks)
        self.current_track_index = 0
    
    def play_menu_music(self):
        """Play the menu music with a smooth fade-in"""
        # Check if music is disabled in accessibility settings
        if not self.game.accessibility.get('music_enabled', True):
            # Stop any currently playing music
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            return
            
        if not self.is_playing_menu_music or self.current_track != self.menu_track:
            # If we're already playing something, fade it out first
            if pygame.mixer.music.get_busy() and not self.fading_out:
                self.fade_out(self.menu_track, -1)
            else:
                # Otherwise just start the menu music
                self._play_track(self.menu_track, -1)
                self.fade_in()
            self.is_playing_menu_music = True
    
    def play_game_music(self):
        """Start playing game music with a smooth transition"""
        # Check if music is disabled in accessibility settings
        if not self.game.accessibility.get('music_enabled', True):
            # Stop any currently playing music
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            return
            
        self.is_playing_menu_music = False
        
        # If we're already playing a game track, don't restart it
        if not self.is_playing_menu_music and self.current_track in self.game_tracks:
            return
            
        # Otherwise, start the next game track with a fade
        if pygame.mixer.music.get_busy() and not self.fading_out:
            # Fade out current track first
            self.fade_out()
            # Queue up the next track to play after fade out
            self.next_track = self.game_tracks[self.current_track_index]
            self.next_track_loop = False  # We'll handle the looping ourselves
        else:
            # No music playing, just start the game music
            self._play_next_game_track()
            self.fade_in()
    
    def _play_track(self, track, loops=0):
        """Internal method to play a track with the specified loop count"""
        pygame.mixer.music.load(track)
        pygame.mixer.music.set_volume(self.current_volume)
        pygame.mixer.music.play(loops)
        self.current_track = track
        
        # Set up an event to trigger when this track ends (only for non-looping)
        if loops == 0:
            pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
        else:
            pygame.mixer.music.set_endevent()
    
    def _play_next_game_track(self):
        """Play the next game track in the shuffled list"""
        if not self.game_tracks:
            return
            
        track = self.game_tracks[self.current_track_index]
        self._play_track(track)
        
    def fade_out(self, next_track=None, next_loops=0):
        """Start fading out the current track"""
        self.fading_out = True
        self.fade_target_volume = 0.0
        self.next_track = next_track
        self.next_track_loop = next_loops
        
    def fade_in(self):
        """Start fading in the current track"""
        self.fading_out = False
        self.fade_target_volume = self.music_volume
        self.current_volume = 0.0
        pygame.mixer.music.set_volume(0.0)
    
    def update(self, events):
        """Update music state and handle events"""
        # Handle volume fading
        if self.fading_out:
            # Fade out current track
            self.current_volume = max(0.0, self.current_volume - self.fade_speed * self.game.clock.get_time() / 1000.0)
            pygame.mixer.music.set_volume(self.current_volume)
            
            # If we've faded out completely, play the next track if there is one
            if self.current_volume <= 0.0:
                if self.next_track:
                    self._play_track(self.next_track, self.next_track_loop)
                    self.fade_in()
                    self.next_track = None
                self.fading_out = False
        elif self.current_volume < self.fade_target_volume:
            # Fade in current track
            self.current_volume = min(self.music_volume, 
                                    self.current_volume + self.fade_speed * self.game.clock.get_time() / 1000.0)
            pygame.mixer.music.set_volume(self.current_volume)
        
        # Handle track end events
        for event in events:
            if event.type == pygame.USEREVENT + 1:  # Music ended
                if not self.is_playing_menu_music and not self.fading_out:
                    # Move to next track (or loop back to start)
                    self.current_track_index = (self.current_track_index + 1) % len(self.game_tracks)
                    self._play_next_game_track()
                    self.fade_in()
    
    def set_volume(self, volume):
        """Set music volume (0.0 to 1.0)"""
        self.music_volume = max(0.0, min(1.0, volume))
        if not self.fading_out and self.current_volume > 0:
            # If we're not in the middle of a fade, update current volume immediately
            self.current_volume = self.music_volume
            pygame.mixer.music.set_volume(self.current_volume)
    
    def stop(self):
        """Stop all music playback"""
        pygame.mixer.music.stop()
        self.is_playing_menu_music = False
        self.fading_out = False
        self.next_track = None
        self.current_volume = 0.0
