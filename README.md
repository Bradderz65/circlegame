# Circle Clicker Game 🎯

A dynamic circle-clicking game with multiple enemy types, difficulty levels, special effects, and comprehensive accessibility features. Built with Python and Pygame.

![Game Status](https://img.shields.io/badge/Status-Active-green)
![Python](https://img.shields.io/badge/Python-3.7+-blue)
![Pygame](https://img.shields.io/badge/Pygame-2.0+-red)

## 🎮 Game Features

### Core Gameplay
- **Multiple Circle Types**: Normal, Fast, Teleporting, and special circles with unique behaviors
- **Dynamic Difficulty**: Easy, Medium, Hard, and Nightmare modes with adaptive gameplay
- **Game Modes**: 
  - Timed Mode (30-300 seconds)
  - Endless Mode (play until you lose)
  - Sandbox Mode (practice and experiment)
- **Obstacle System**: Pipes and spinners that add challenge and strategy
- **High Score System**: Track your best performances with persistent leaderboards

### Visual & Audio
- **Dynamic Background**: Animated star system with movement and effects
- **Background Music**: Multiple tracks with smooth transitions and fade effects
- **Sound Effects**: Immersive audio feedback for all game actions
- **Fullscreen Support**: Press F11 to toggle fullscreen mode
- **Smooth Animations**: Fade effects, projectile trails, and visual polish

### Accessibility Features
- **Music Control**: Enable/disable background music
- **Click Radius Helper**: Visual aid showing clickable area around cursor
- **Pipe Warning Flash**: Blue flash warning before pipe obstacles spawn
- **Obstacle Toggles**: Disable pipes or spinners individually
- **Dynamic Background Toggle**: Reduce visual complexity if needed
- **Volume Controls**: Adjust master and effect volumes independently

## 🚀 Getting Started

### Prerequisites
- Python 3.7 or higher
- Pygame 2.0 or higher

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Bradderz65/circlegame.git
   cd circlegame
   ```

2. Install dependencies:
   ```bash
   pip install pygame
   ```

3. Run the game:
   ```bash
   python main.py
   ```

## 🎯 How to Play

### Basic Controls
- **Mouse**: Click on circles to destroy them and earn points
- **Space**: Start game from main menu
- **S**: Enter sandbox mode
- **H**: View high scores
- **A**: Open accessibility settings
- **Q**: Quit game
- **F11**: Toggle fullscreen
- **Tab**: Toggle UI visibility (during gameplay)
- **Escape**: Return to previous menu/exit game

### Gameplay Controls (During Game)
- **V**: Show/hide volume help
- **↑/↓**: Adjust master volume
- **←/→**: Adjust sound effect volume
- **+/-**: Adjust click radius (when accessibility feature enabled)
- **Ctrl+Plus**: Skip to next level (debug feature)
- **Ctrl+Q**: Toggle quick pipe spawning mode

### Sandbox Mode Controls
- **1-9**: Spawn different circle types
- **Space**: Pause/unpause
- **Escape**: Return to main menu

## 🏗️ Project Structure

The game is built with a modular architecture for maintainability:

```
├── main.py              # Main game loop and input handling
├── game_state.py        # Core game logic and state management
├── audio_manager.py     # Music and sound effect management
├── ui_renderer.py       # All UI rendering and visual effects
├── game_config.py       # Game constants and configuration
├── circle.py           # Circle entities and behaviors
├── assets/             # Music and audio files
├── CHANGELOG.md        # Version history and changes
└── README.md          # This file
```

## 🎵 Audio System

The game features a sophisticated audio system with:
- **Background Music**: Multiple tracks that smoothly transition between menu and gameplay
- **Fade Transitions**: 1.5-second smooth fades between tracks
- **Volume Control**: Independent master and effect volume controls
- **Accessibility**: Complete music disable option for audio-sensitive players
- **Persistent Settings**: Audio preferences saved between sessions

## ♿ Accessibility

We're committed to making the game accessible to all players:

- **Visual Aids**: Click radius helper for players with motor difficulties
- **Audio Options**: Complete music disable for audio-sensitive players
- **Obstacle Control**: Disable challenging elements like pipes or spinners
- **Warning Systems**: Visual warnings before obstacles appear
- **Customizable Settings**: All accessibility options are persistent

## 🔧 Configuration

Game settings are automatically saved to JSON files:
- `accessibility_settings.json` - Accessibility preferences and click radius
- `high_scores.json` - High score leaderboards

## 🎨 Recent Updates

### Version 2025-08-22
- ✅ Added music accessibility setting with enable/disable option
- ✅ Fixed music transition bug when returning from game over screen
- ✅ Reduced music volume for better audio balance (30% → 15%)
- ✅ Enhanced fade transitions for smoother audio experience (0.5s → 1.5s)
- ✅ All music preferences now save and restore between sessions

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

## 🤝 Contributing

This is a personal project, but suggestions and feedback are welcome! Feel free to:
- Report bugs via GitHub issues
- Suggest new features or accessibility improvements
- Share your high scores and gameplay experiences

## 📝 License

This project is open source. Feel free to learn from the code and adapt it for your own projects.

## 🎯 High Score Challenge

Think you can master all difficulty levels? The game tracks your best performances across:
- Different difficulty settings (Easy, Medium, Hard, Nightmare)
- Various game modes (Timed vs Endless)
- Round progression and total scores

Challenge yourself to reach the leaderboard!

---

**Enjoy the game and happy clicking!** 🎮✨
