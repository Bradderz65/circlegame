#!/usr/bin/env python3
"""
Circle Clicker Game - Main Entry Point

A dynamic circle-clicking game with multiple enemy types, difficulty levels,
and special effects. Split into organized modules for better maintainability.

Author: Split from original monolithic design
"""

import pygame
import random
import time
from game_state import Game, GameState, GameMode
from game_config import *
from circle import CircleType
from ui_renderer import *
from game_state import GameState

def handle_game_over_input(game, event):
    """Handle input during game over screen"""
    if event.type == pygame.KEYDOWN:
        if game.name_input_active:
            if event.key == pygame.K_RETURN:
                if game.player_name.strip():
                    game.add_high_score(game.player_name.strip(), game.score, game.round_num - 1)
                    game.player_name = ""
                    game.name_input_active = False
                    game.state = GameState.MAIN_MENU
            elif event.key == pygame.K_BACKSPACE:
                game.player_name = game.player_name[:-1]
            elif event.key == pygame.K_ESCAPE:
                game.name_input_active = False
            else:
                if len(game.player_name) < 20 and event.unicode.isprintable():
                    game.player_name += event.unicode
        else:
            if event.key == pygame.K_m:
                game.state = GameState.MAIN_MENU
            elif event.key == pygame.K_ESCAPE:
                game.state = GameState.MAIN_MENU

    elif event.type == pygame.MOUSEBUTTONDOWN:
        # Check if clicked on input box - scaled
        box_width = int(350 * game.scale_factor)
        box_height = int(45 * game.scale_factor)
        input_y = int(320 * game.scale_factor)  # Approximate position
        # Match the actual drawn position: input_y + 40 * scale_factor
        input_box = pygame.Rect(game.screen_width // 2 - box_width // 2, input_y + int(40 * game.scale_factor), box_width, box_height)
        if input_box.collidepoint(event.pos):
            game.name_input_active = True
        else:
            game.name_input_active = False

def main():
    """Main game loop"""
    game = Game()
    running = True
    show_high_scores = False

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                # Close tutorial popup on any keypress
                if game.show_click_radius_tutorial:
                    game.show_click_radius_tutorial = False
                    continue  # Don't process other key events when closing tutorial
                
                # Global F11 toggle for fullscreen
                if event.key == pygame.K_F11:
                    game.toggle_fullscreen()

                # Global Ctrl+Plus to increase level by 1 (works on any difficulty)
                elif (event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS) and (event.mod & pygame.KMOD_CTRL):
                    if game.state == GameState.PLAYING or game.state == GameState.SANDBOX:
                        game.next_round()
                
                # Global Ctrl+Q to toggle quick pipe spawning mode
                elif event.key == pygame.K_q and (event.mod & pygame.KMOD_CTRL):
                    if game.state == GameState.PLAYING or game.state == GameState.SANDBOX:
                        game.force_quick_pipes = not game.force_quick_pipes
                        # Show a brief message about the toggle
                        status = "ON" if game.force_quick_pipes else "OFF"
                        print(f"Quick Pipe Mode: {status}")

                elif game.state == GameState.MAIN_MENU:
                    if show_high_scores:
                        if event.key == pygame.K_ESCAPE:
                            show_high_scores = False
                    else:
                        if event.key == pygame.K_SPACE:
                            game.state = GameState.DIFFICULTY_SELECT
                        elif event.key == pygame.K_s:
                            game.start_sandbox_mode()
                        elif event.key == pygame.K_h:
                            show_high_scores = True
                        elif event.key == pygame.K_a:
                            game.show_accessibility_menu = True
                        elif event.key == pygame.K_q:
                            running = False
                    
                    # Handle accessibility menu input
                    if game.show_accessibility_menu:
                        option_count = max(1, len(getattr(game, 'accessibility_option_rects', [])))
                        if event.key == pygame.K_ESCAPE:
                            game.show_accessibility_menu = False
                        elif event.key in (pygame.K_UP, pygame.K_w):
                            game.accessibility_menu_index = (game.accessibility_menu_index - 1) % option_count
                        elif event.key in (pygame.K_DOWN, pygame.K_s):
                            game.accessibility_menu_index = (game.accessibility_menu_index + 1) % option_count
                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            # Toggle selected option
                            if game.accessibility_menu_index < option_count:
                                _, key = game.accessibility_option_rects[game.accessibility_menu_index]
                                old_value = game.accessibility[key]
                                game.accessibility[key] = not game.accessibility[key]
                                game.save_accessibility_settings()
                                
                                # Show tutorial popup if click radius helper was just enabled
                                if key == 'click_radius_helper' and not old_value and game.accessibility[key]:
                                    game.show_click_radius_tutorial = True
                                    game.click_radius_tutorial_start_time = time.time()

                elif game.state == GameState.DIFFICULTY_SELECT:
                    if event.key == pygame.K_UP:
                        difficulties = list(game.difficulty.__class__)
                        current_index = difficulties.index(game.difficulty)
                        game.difficulty = difficulties[(current_index - 1) % len(difficulties)]
                    elif event.key == pygame.K_DOWN:
                        difficulties = list(game.difficulty.__class__)
                        current_index = difficulties.index(game.difficulty)
                        game.difficulty = difficulties[(current_index + 1) % len(difficulties)]
                    elif event.key == pygame.K_RETURN:
                        game.state = GameState.TIME_SELECT
                    elif event.key == pygame.K_ESCAPE:
                        game.state = GameState.MAIN_MENU

                elif game.state == GameState.TIME_SELECT:
                    if event.key == pygame.K_UP:
                        modes = list(GameMode)
                        current_index = modes.index(game.game_mode)
                        game.game_mode = modes[(current_index - 1) % len(modes)]
                    elif event.key == pygame.K_DOWN:
                        modes = list(GameMode)
                        current_index = modes.index(game.game_mode)
                        game.game_mode = modes[(current_index + 1) % len(modes)]
                    elif event.key == pygame.K_LEFT and game.game_mode == GameMode.TIMED:
                        game.time_limit = max(30, game.time_limit - 30)
                    elif event.key == pygame.K_RIGHT and game.game_mode == GameMode.TIMED:
                        game.time_limit = min(300, game.time_limit + 30)
                    elif event.key == pygame.K_RETURN:
                        game.start_new_game()
                    elif event.key == pygame.K_ESCAPE:
                        game.state = GameState.DIFFICULTY_SELECT

                elif game.state == GameState.PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        game.state = GameState.GAME_OVER
                        game.name_input_active = True
                        play_sound(GAME_OVER_SOUND)
                    elif event.key == pygame.K_TAB:
                        game.show_ui = not game.show_ui
                    elif event.key == pygame.K_v:
                        game.show_volume_help = not game.show_volume_help
                    # Volume controls
                    elif event.key == pygame.K_UP:
                        game.master_volume = min(2.0, game.master_volume + 0.1)
                        game.update_tank_volumes()
                    elif event.key == pygame.K_DOWN:
                        game.master_volume = max(0.0, game.master_volume - 0.1)
                        game.update_tank_volumes()
                    elif event.key == pygame.K_LEFT:
                        game.tank_volume = max(0.0, game.tank_volume - 0.1)
                        game.update_tank_volumes()
                    elif event.key == pygame.K_RIGHT:
                        game.tank_volume = min(3.0, game.tank_volume + 0.1)
                        game.update_tank_volumes()
                    # Click radius controls (only when accessibility feature is enabled)
                    elif event.key == pygame.K_EQUALS:  # + key (= key, shift for +)
                        if game.accessibility.get('click_radius_helper', False):
                            game.click_radius = min(game.max_click_radius, game.click_radius + 5)
                            game.save_accessibility_settings()
                            print(f"Click radius increased to {game.click_radius}px")
                    elif event.key == pygame.K_MINUS:  # - key
                        if game.accessibility.get('click_radius_helper', False):
                            game.click_radius = max(game.min_click_radius, game.click_radius - 5)
                            game.save_accessibility_settings()
                            print(f"Click radius decreased to {game.click_radius}px")

                elif game.state == GameState.SANDBOX:
                    if event.key == pygame.K_ESCAPE:
                        game.state = GameState.MAIN_MENU
                    elif event.key == pygame.K_TAB:
                        game.show_ui = not game.show_ui
                    elif event.key == pygame.K_v:
                        game.show_volume_help = not game.show_volume_help
                    # Volume controls
                    elif event.key == pygame.K_UP:
                        game.master_volume = min(2.0, game.master_volume + 0.1)
                        game.update_tank_volumes()
                    elif event.key == pygame.K_DOWN:
                        game.master_volume = max(0.0, game.master_volume - 0.1)
                        game.update_tank_volumes()
                    elif event.key == pygame.K_LEFT:
                        game.tank_volume = max(0.0, game.tank_volume - 0.1)
                        game.update_tank_volumes()
                    elif event.key == pygame.K_RIGHT:
                        game.tank_volume = min(3.0, game.tank_volume + 0.1)
                        game.update_tank_volumes()
                    # Click radius controls (only when accessibility feature is enabled)
                    elif event.key == pygame.K_EQUALS:  # + key (= key, shift for +)
                        if game.accessibility.get('click_radius_helper', False):
                            game.click_radius = min(game.max_click_radius, game.click_radius + 5)
                            game.save_accessibility_settings()
                            print(f"Click radius increased to {game.click_radius}px")
                    elif event.key == pygame.K_MINUS:  # - key
                        if game.accessibility.get('click_radius_helper', False):
                            game.click_radius = max(game.min_click_radius, game.click_radius - 5)
                            game.save_accessibility_settings()
                            print(f"Click radius decreased to {game.click_radius}px")
                    elif event.key == pygame.K_1:
                        game.spawn_sandbox_circle(CircleType.NORMAL)
                    elif event.key == pygame.K_2:
                        game.spawn_sandbox_circle(CircleType.FAST)
                    elif event.key == pygame.K_3:
                        game.spawn_sandbox_circle(CircleType.TELEPORTING)
                    elif event.key == pygame.K_4:
                        game.spawn_sandbox_circle(CircleType.SHRINKING)
                    elif event.key == pygame.K_5:
                        game.spawn_sandbox_circle(CircleType.SMALL)
                    elif event.key == pygame.K_6:
                        game.spawn_sandbox_circle(CircleType.GHOST)
                    elif event.key == pygame.K_7:
                        game.spawn_sandbox_circle(CircleType.TANK)
                    elif event.key == pygame.K_8:
                        game.spawn_sandbox_circle(CircleType.SUPERTANK)
                    elif event.key == pygame.K_9:
                        game.spawn_sandbox_circle(CircleType.HEXAGON)
                    elif event.key == pygame.K_0:
                        game.spawn_sandbox_circle(CircleType.CURSOR_GRABBER)
                    elif event.key == pygame.K_s:
                        game.spawn_sandbox_circle(CircleType.SNAKE)
                    elif event.key == pygame.K_r:
                        game.spawn_sandbox_circle(CircleType.SHOOTER)
                    elif event.key == pygame.K_o:
                        # Spawn spinning obstacle (unless disabled)
                        if not game.accessibility.get('disable_spinners', False):
                            game.spawn_sandbox_obstacle()  # Spawn spinning obstacle
                    elif event.key == pygame.K_c:
                        # Clean up all tank hum sounds before clearing
                        for circle in game.circles:
                            circle.cleanup_sounds()
                        game.circles.clear()  # Clear all circles
                        game.obstacles.clear()  # Clear spinning obstacles
                        game.pipe_obstacles.clear()  # Clear pipe obstacles
                    elif event.key == pygame.K_p:
                        # Spawn a new pipe obstacle in sandbox mode with warning flash (unless disabled)
                        if not game.accessibility.get('disable_pipes', False):
                            if game.accessibility.get('pipe_warning_flash', True):
                                # Show warning flash before spawning pipe
                                game.pipe_warning_flash_alpha = 100
                                # Use a timer to spawn the pipe after the flash
                                pygame.time.set_timer(pygame.USEREVENT + 1, 500)  # 500ms delay
                            else:
                                # Spawn immediately if flash is disabled
                                from pipe_obstacle import PipeObstacle

                                pipe_settings = game.difficulty_settings[game.difficulty]["pipe_settings"]
                                pipe = PipeObstacle(game.screen_width, game.screen_height, game.scale_factor)

                                # Randomize gap height (±20%)
                                gap_height_base = pipe_settings["gap_height"] * game.scale_factor
                                pipe.gap_height = random.uniform(0.8 * gap_height_base, 1.2 * gap_height_base)

                                # Randomize width/thickness
                                min_width = 40 * game.scale_factor
                                max_width = 80 * game.scale_factor
                                pipe.width = random.uniform(min_width, max_width)
                                pipe.x = -pipe.width  # Start fully off-screen

                                # Apply speed multipliers and vertical speed variability
                                pipe.speed *= pipe_settings["speed_multiplier"]
                                min_vert_speed, max_vert_speed = pipe_settings["vertical_speed_range"]
                                pipe.vertical_speed = random.uniform(min_vert_speed, max_vert_speed)

                                game.pipe_obstacles.append(pipe)
                                
                                # If quick pipe mode is enabled, trigger automatic next spawn
                                if game.force_quick_pipes:
                                    game.pending_pipe_spawn = True
                                    game.schedule_next_pipe_spawn()
                    elif event.key == pygame.K_SPACE:
                        game.sandbox_paused = not game.sandbox_paused  # Toggle pause

                elif game.state == GameState.GAME_OVER:
                    handle_game_over_input(game, event)

            elif event.type == pygame.USEREVENT + 1:
                # Timer event for delayed pipe spawn in sandbox mode
                pygame.time.set_timer(pygame.USEREVENT + 1, 0)  # Clear the timer
                
                # Check if pipes are disabled before spawning
                if not game.accessibility.get('disable_pipes', False):
                    from pipe_obstacle import PipeObstacle

                    pipe_settings = game.difficulty_settings[game.difficulty]["pipe_settings"]
                    pipe = PipeObstacle(game.screen_width, game.screen_height, game.scale_factor)

                    gap_height_base = pipe_settings["gap_height"] * game.scale_factor
                    pipe.gap_height = random.uniform(0.8 * gap_height_base, 1.2 * gap_height_base)

                    min_width = 40 * game.scale_factor
                    max_width = 80 * game.scale_factor
                    pipe.width = random.uniform(min_width, max_width)
                    pipe.x = -pipe.width

                    pipe.speed *= pipe_settings["speed_multiplier"]
                    min_vert_speed, max_vert_speed = pipe_settings["vertical_speed_range"]
                    pipe.vertical_speed = random.uniform(min_vert_speed, max_vert_speed)

                    game.pipe_obstacles.append(pipe)
                    
                    # If quick pipe mode is enabled, trigger automatic next spawn
                    if game.force_quick_pipes:
                        game.pending_pipe_spawn = True
                        game.schedule_next_pipe_spawn()
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if game.show_accessibility_menu:
                    # Toggle option if clicked
                    for idx, (rect, key) in enumerate(getattr(game, 'accessibility_option_rects', [])):
                        if rect.collidepoint(event.pos):
                            old_value = game.accessibility[key]
                            game.accessibility[key] = not game.accessibility[key]
                            game.accessibility_menu_index = idx
                            game.save_accessibility_settings()
                            
                            # Show tutorial popup if click radius helper was just enabled
                            if key == 'click_radius_helper' and not old_value and game.accessibility[key]:
                                game.show_click_radius_tutorial = True
                                game.click_radius_tutorial_start_time = time.time()
                            break
                elif game.state == GameState.PLAYING or game.state == GameState.SANDBOX:
                    game.handle_click(event.pos)
                elif game.state == GameState.GAME_OVER:
                    handle_game_over_input(game, event)

        # Update game state
        game.update()
        
        # Update tutorial popup timer
        if game.show_click_radius_tutorial:
            if time.time() - game.click_radius_tutorial_start_time >= game.click_radius_tutorial_duration:
                game.show_click_radius_tutorial = False

        # Render appropriate screen
        if game.state == GameState.MAIN_MENU:
            if show_high_scores:
                draw_high_scores(game)
            elif game.show_accessibility_menu:
                draw_accessibility_menu(game)
            else:
                draw_main_menu(game)
        elif game.state == GameState.DIFFICULTY_SELECT:
            draw_difficulty_select(game)
        elif game.state == GameState.TIME_SELECT:
            draw_time_select(game)
        elif game.state == GameState.PLAYING:
            draw_game(game)
        elif game.state == GameState.SANDBOX:
            draw_sandbox(game)
        elif game.state == GameState.GAME_OVER:
            draw_game_over(game)
        
        # Draw tutorial popup on top of everything if active
        if game.show_click_radius_tutorial:
            draw_click_radius_tutorial_popup(game)

        pygame.display.flip()
        game.clock.tick(game.target_fps)

    pygame.quit()

if __name__ == "__main__":
    main()