"""
Controller.py: turns BCI input (or, in principle, any input source with a
`.poll_direction()` method) into player movement on the maze grid.

This is a good file to read if you want to understand *when* a move is
accepted, but most usability tweaks (arrow layout, colors, sizes) belong in
UI.py and Config.py instead.
"""
import pygame as pg
from Config import VEC, WALK_SPEED_PX_S, MOVE_COOLDOWN_S, FEEDBACK_DURATION_S


class Controller:
    """
    Owns the player's position/heading and applies incoming BCI directions
    to it, one grid cell at a time.

    `bci` is any object exposing `poll_direction() -> 'N'|'E'|'S'|'W'|''`.
    Main.py passes in a real `BCIListener`; tests or a keyboard-driven demo
    could pass in something else that implements the same method.
    """

    def __init__(self, maze, cell_px=48, walk_speed_px_s=WALK_SPEED_PX_S, bci=None):
        self.maze = maze
        self.cell_px = cell_px
        self.walk_speed = walk_speed_px_s
        self.pos_rc = maze.start
        self.heading = "E"
        self.armed_dir = None
        self.bci = bci
        self.paused = True
        self.control_mode = "keyboard"

        # --- move debouncing -------------------------------------------------
        # After a successful step we ignore new directions for
        # `_move_cooldown` seconds. This stops a single sustained BCI
        # detection from being read as many rapid-fire moves.
        self._move_cooldown = MOVE_COOLDOWN_S
        self._cd_left = 0.0

        self.step_count = 0
        self.elapsed_time = 0.0

        self.feedback_dir = None
        self.feedback_status = None
        self.feedback_timer = 0.0


        if not pg.mixer.get_init():
            pg.mixer.init()

        try:
            self.sound_step = pg.mixer.Sound("step.wav")
            self.sound_wall = pg.mixer.Sound("wall.wav")
            print("sound files loaded")
        except Exception as e:
            print("Could not load sound:", e)
            self.sound_step = None
            self.sound_wall = None


    def _try_step(self, d):
        """
        Attempt to move one cell in direction `d`.
        Returns True and updates position/heading if that cell is walkable,
        otherwise returns False and leaves the player where it was.
        """
        dr, dc = VEC[d] 
        nxt = (self.pos_rc[0] + dr, self.pos_rc[1] + dc)
        if self.maze.is_path(nxt):
            self.pos_rc = nxt
            self.heading = d
            self.step_count += 1
            return True
        return False

    def handle_bci(self, dt):
        """Poll the BCI source (if any) and apply a move if one is ready."""
        if self.paused:
            return
        if not self.bci:
            return
        if self._cd_left > 0:
            return

        d = self.bci.poll_direction()  # 'N', 'E', 'S', 'W', or '' (nothing detected)
        if not d:
            return

        self.feedback_dir = d
        self.feedback_timer = FEEDBACK_DURATION_S

        if self._try_step(d):
             self.feedback_status = "SUCCESS"
        if self.sound_step:
            self.sound_step.play()  
            self._cd_left = self._move_cooldown
        
        else:
            self.feedback_status = "BLOCKED"
            if self.sound_wall:
                self.sound_wall.play()   
            self._cd_left = self._move_cooldown * 0.8



    

    def handle_keyboard(self, direction):
        """Apply one keyboard press immediately."""
        if self.paused or self.control_mode != "keyboard" or direction not in VEC:
            return

        self.armed_dir = direction
        self._try_step(direction)

    def update(self, dt):
        """Advance game state by `dt` seconds. Call once per frame from Main.py."""
        if self.paused:
            return
        self.elapsed_time += dt
        if self.feedback_timer > 0:
            self.feedback_timer -= dt
        if self.feedback_timer <= 0:
            self.feedback_dir = None
            self.feedback_status = None

        # Cooldown is shared by keyboard and BCI input.
        self._cd_left = max(0.0, self._cd_left - dt)

        if self.control_mode == "bci":
            self.handle_bci(dt)

    def toggle_pause(self):
        if self.paused:
            self.paused = False
        else:
            self.paused = True

    