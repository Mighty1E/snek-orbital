# ORBITAL - A small space game made with Pygame.

import math
import sys
from pathlib import Path

import pygame


# Game settings
WIDTH = 1280
HEIGHT = 720
FPS = 60

SHIP_RADIUS = 12
THRUST = 390.0
GRAVITY = 9000.0
MAX_SPEED = 620.0
FUEL_DRAIN = 14.0


# Level layouts, including the ship spawn, planets, cores and exit gate.
LEVELS = [
    {
        "spawn": (160, 535),
        "planets": [((600, 360), 82, "#805ad5")],
        "cores": [(700, 185), (940, 380)],
        "gate": (1100, 550),
    },
    {
        "spawn": (145, 565),
        "planets": [
            ((470, 450), 66, "#e76f51"),
            ((820, 255), 98, "#457b9d"),
        ],
        "cores": [(380, 160), (710, 550), (1050, 185)],
        "gate": (1120, 565),
    },
    {
        "spawn": (145, 360),
        "planets": [
            ((410, 245), 64, "#ffb703"),
            ((700, 500), 100, "#219ebc"),
            ((1005, 220), 72, "#8338ec"),
        ],
        "cores": [(305, 560), (655, 165), (965, 500), (1125, 360)],
        "gate": (1160, 600),
    },
]


class Orbital:
    def __init__(self):
        # Start Pygame and set up the game window.
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()

        pygame.display.set_caption("ORBITAL")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        # Fonts used for the different bits of text.
        self.font = pygame.font.Font(None, 28)
        self.title_font = pygame.font.Font(None, 44)
        self.small_font = pygame.font.Font(None, 22)

        # Make some stars for the background.
        self.stars = [
            (
                (i * 179) % 1260 + 10,
                (i * 83) % 690 + 10,
                1 + i % 3,
            )
            for i in range(90)
        ]

        # Load imported audio files from the project's assets folder.
        self.ship_sprite = self.create_ship_sprite()
        self.music_folder = Path(__file__).parent / "assets" / "music"
        self.music_files = [
            self.music_folder / "level1.wav",
            self.music_folder / "level2.wav",
            self.music_folder / "level3.wav",
        ]
        # Use the pack's dedicated title-screen track, separate from level one.
        self.title_music_file = self.music_folder / "title.wav"
        self.title_music_playing = False
        self.victory_sound = self.load_sound(self.music_folder / "ending.wav")
        self.music_available = pygame.mixer.get_init() is not None

        # Menu, difficulty and tutorial state.
        self.level_index = 0
        self.screen_state = "title"
        self.tutorial_flag = Path(__file__).parent / ".orbital_tutorial_seen"
        self.tutorial_seen = self.tutorial_flag.exists()
        self.fuel_setting = 100
        self.planet_scale = 1.0
        self.timer_setting = 0  # Zero means no timer.
        self.music_volume = 0.45
        self.settings_return = "title"
        self.menu_buttons = {}
        self.load_level()
        pygame.mixer.music.stop()

    def load_sound(self, path):
        """Load an imported sound file if it exists; never synthesize audio."""
        if not pygame.mixer.get_init() or not path.is_file():
            return None
        try:
            return pygame.mixer.Sound(str(path))
        except pygame.error as error:
            print(f"Could not load audio {path.name}: {error}")
            return None

    def stop_victory_music(self):
        """Stop the ending sound so it cannot overlap restarted gameplay."""
        if self.victory_sound:
            self.victory_sound.stop()

    def play_music_for_level(self):
        """Stop the ending sound and play the current sector's loop."""
        self.stop_victory_music()
        if not pygame.mixer.get_init():
            return
        music_path = self.music_files[self.level_index]
        if not music_path.is_file():
            pygame.mixer.music.stop()
            print(f"Missing soundtrack: {music_path}. Add the audio file to enable music.")
            return
        try:
            pygame.mixer.music.fadeout(500)
            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1, fade_ms=700)
        except pygame.error as error:
            print(f"Could not play soundtrack {music_path.name}: {error}")

    def play_title_music(self):
        """Loop the title theme without overlapping game or victory audio."""
        if not pygame.mixer.get_init() or not self.title_music_file.is_file():
            return
        try:
            if self.title_music_playing and pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume(self.music_volume)
                return
            self.stop_victory_music()
            pygame.mixer.music.stop()
            pygame.mixer.music.load(str(self.title_music_file))
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1, fade_ms=500)
            self.title_music_playing = True
        except pygame.error as error:
            self.title_music_playing = False
            print(f"Could not play title soundtrack: {error}")

    def create_ship_sprite(self):
        """Small diagonal pixel rocket based closely on the supplied reference."""
        # Build the art on a tiny pixel canvas, then enlarge with nearest-neighbour
        # scaling so the outline stays crisp instead of turning into a white blob.
        cell = 2
        art = pygame.Surface((24, 24), pygame.SRCALPHA)
        ink = "#292a35"
        hull = "#eeeaf8"
        shade = "#b8bce5"
        shade_dark = "#858bb9"
        orange = "#ed765b"
        yellow = "#f4c95d"

        # Exhaust trails down-left; the nose points up-right.
        pygame.draw.polygon(art, ink, [(3, 16), (6, 12), (12, 5), (17, 3),
                                       (21, 5), (22, 9), (20, 13), (13, 19),
                                       (9, 21), (5, 19)])
        pygame.draw.polygon(art, hull, [(5, 16), (8, 12), (13, 6), (17, 5),
                                        (19, 6), (20, 9), (18, 12), (12, 18),
                                        (9, 19), (6, 18)])
        # Cool shadow along the lower edge gives it the game's illustrated depth.
        pygame.draw.polygon(art, shade, [(8, 16), (12, 17), (18, 11), (19, 9),
                                         (18, 12), (12, 18), (9, 19), (7, 18)])
        pygame.draw.polygon(art, shade_dark, [(13, 7), (16, 6), (18, 7),
                                              (18, 9), (16, 11), (14, 9)])
        pygame.draw.polygon(art, "#d8dcf6", [(13, 7), (16, 6), (17, 7),
                                              (15, 8), (14, 10)])
        # Tail nozzle and the distinct orange/yellow flame from the reference.
        pygame.draw.polygon(art, ink, [(5, 16), (8, 17), (9, 20), (6, 22),
                                       (2, 20), (2, 18)])
        pygame.draw.polygon(art, orange, [(5, 17), (7, 18), (8, 20),
                                          (6, 21), (3, 20), (3, 18)])
        pygame.draw.polygon(art, yellow, [(5, 18), (7, 19), (6, 20), (4, 19)])
        # Keep all edges hard and pixel-aligned when bringing it to game size.
        return pygame.transform.scale(art, (48, 48))

    def load_level(self):
        # Load the level's starting positions and objects.
        self.play_music_for_level()
        level = LEVELS[self.level_index]

        self.ship_position = pygame.Vector2(level["spawn"])
        self.ship_velocity = pygame.Vector2()
        self.ship_angle = 0.0

        # Turn the planet data into Pygame objects.
        self.planets = [
            (
                pygame.Vector2(position),
                max(12, int(radius * self.planet_scale)),
                pygame.Color(colour),
            )
            for position, radius, colour in level["planets"]
        ]

        self.cores = [
            pygame.Vector2(core)
            for core in level["cores"]
        ]

        self.total_cores = len(self.cores)
        self.gate = pygame.Vector2(level["gate"])

        # Reset the player's progress and game state.
        self.fuel = float(self.fuel_setting)
        self.message = "Collect every energy core, then reach the gate."
        self.dead = False
        self.won = False
        self.game_complete = False
        self.time_left = float(self.timer_setting) if self.timer_setting else None

    def update(self, delta):
        # Only simulate the ship while gameplay is active.
        if self.screen_state != "game" or self.dead or self.won:
            return

        if self.time_left is not None:
            self.time_left = max(0.0, self.time_left - delta)
            if self.time_left <= 0:
                self.die("Time is up. Press Enter to retry.")
                return

        keys = pygame.key.get_pressed()

        # Get the movement direction from the keyboard.
        direction = pygame.Vector2(
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            int(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - int(keys[pygame.K_w] or keys[pygame.K_UP]),
        )

        # Move the ship if the player has fuel.
        if direction.length_squared() and self.fuel > 0:
            direction = direction.normalize()
            self.ship_velocity += direction * THRUST * delta

            # Reduce sideways sliding when steering.
            sideways_velocity = (
                self.ship_velocity
                - direction * self.ship_velocity.dot(direction)
            )
            self.ship_velocity -= sideways_velocity * min(
                0.75 * delta, 0.12
            )

            self.fuel = max(
                0.0,
                self.fuel - FUEL_DRAIN * delta,
            )

        # Slowly reduce the ship's speed over time.
        self.ship_velocity *= 0.993 ** (delta * 60)

        # Pull the ship towards every planet.
        for planet_position, radius, _colour in self.planets:
            offset = planet_position - self.ship_position
            distance_squared = max(offset.length_squared(), 2500.0)

            self.ship_velocity += (
                offset.normalize()
                * GRAVITY
                * radius
                / distance_squared
                * delta
            )

            # End the level if the ship hits a planet.
            if offset.length() < radius + SHIP_RADIUS:
                self.die(
                    "You hit a planet. Press Enter to retry."
                )
                return

        # Stop the ship from moving too quickly.
        if self.ship_velocity.length() > MAX_SPEED:
            self.ship_velocity.scale_to_length(MAX_SPEED)

        # Turn the ship to face the direction it is moving.
        if self.ship_velocity.length() > 12:
            # Artwork points upward by default. Convert velocity's direction
            # into Pygame's counter-clockwise rotation from that upward nose.
            # This artwork's nose starts at 45 degrees above the rightward axis.
            # Offset the velocity angle by 45 degrees so the nose, not the tail,
            # points along the direction of travel.
            target_angle = -math.degrees(
                math.atan2(
                    self.ship_velocity.y,
                    self.ship_velocity.x,
                )
            ) - 45

            angle_difference = (
                target_angle - self.ship_angle + 180
            ) % 360 - 180

            self.ship_angle += angle_difference * min(
                9.0 * delta, 1.0
            )

        # Update the ship's position.
        self.ship_position += self.ship_velocity * delta

        # Retry if the ship flies off the screen.
        if not (
            -30 < self.ship_position.x < WIDTH + 30
            and -30 < self.ship_position.y < HEIGHT + 30
        ):
            self.die(
                "You drifted into space. Press Enter to retry."
            )
            return

        # Collect energy cores and restore some fuel.
        for core in self.cores[:]:
            if self.ship_position.distance_to(core) < 28:
                self.cores.remove(core)
                self.fuel = min(100.0, self.fuel + 18.0)
                self.message = "Core collected. Fuel restored."

        # Finish the level when all cores have been collected.
        if not self.cores and self.ship_position.distance_to(self.gate) < 42:
            self.won = True

            if self.level_index == len(LEVELS) - 1:
                self.game_complete = True
                self.message = "Transmission complete."
                # Stop the sector loop before playing the ending track.
                pygame.mixer.music.stop()
                if self.victory_sound:
                    self.victory_sound.play()
            else:
                self.message = "Jump successful. Press Enter for the next sector."

    def die(self, message):
        # Store the message and stop the player from moving.
        self.dead = True
        self.message = message

    def draw_text(
        self,
        text,
        position,
        colour,
        small=False,
        title=False,
        center=False,
    ):
        # Choose the right font for the text.
        if title:
            font = self.title_font
        elif small:
            font = self.small_font
        else:
            font = self.font

        surface = font.render(text, True, colour)

        # Position the text by its centre or top-left corner.
        if center:
            rect = surface.get_rect(center=position)
        else:
            rect = surface.get_rect(topleft=position)

        self.screen.blit(surface, rect)

    def draw(self):
        # Menu screens share the starfield but do not draw active gameplay.
        if self.screen_state != "game":
            self.draw_menu_screen()
            pygame.display.flip()
            return

        # Draw the background and stars.
        self.screen.fill("#07111f")

        for x, y, radius in self.stars:
            pygame.draw.rect(
                self.screen,
                "#9bb9d5",
                (x, y, max(1, radius // 2), max(1, radius // 2)),
            )

        # Draw the planets.
        for planet_number, (position, radius, colour) in enumerate(self.planets):
            style = (planet_number + self.level_index) % 3
            self.draw_planet(position, radius, colour, style)

        # Draw the energy cores.
        for core in self.cores:
            self.draw_wobbly_circle(
                core, 16, pygame.Color("#ffdf6c"), 37, outline=4
            )
            self.draw_wobbly_circle(
                core - pygame.Vector2(3, 4),
                7,
                pygame.Color("#fff5bf"),
                38,
            )

        # The gate changes colour when all cores are collected.
        if not self.cores:
            gate_colour = pygame.Color("#69f0ae")
        else:
            gate_colour = pygame.Color("#536475")

        self.draw_wobbly_circle(
            self.gate, 28, gate_colour, 17, outline=5, fill=False
        )
        self.draw_wobbly_circle(
            self.gate,
            38,
            pygame.Color(*gate_colour[:3], 65),
            18,
            outline=3,
            fill=False,
        )

        # Rotate the ship image to match its direction.
        compact_ship = pygame.transform.scale_by(self.ship_sprite, 0.58)
        rotated_ship = pygame.transform.rotate(
            compact_ship, self.ship_angle
        )
        ship_rect = rotated_ship.get_rect(
            center=(
                int(self.ship_position.x),
                int(self.ship_position.y),
            )
        )
        self.screen.blit(rotated_ship, ship_rect)

        # Show the level, cores and fuel.
        self.draw_text("ORBITAL", (34, 24), "#d9edff", title=True)
        self.draw_text(
            f"SECTOR {self.level_index + 1} / {len(LEVELS)}",
            (35, 70),
            "#86a4bd",
            small=True,
        )
        self.draw_text(
            f"CORES {self.total_cores - len(self.cores)} / {self.total_cores}",
            (1030, 32),
            "#ffdf6c",
            small=True,
        )
        if self.time_left is not None:
            self.draw_text(
                f"TIME {int(self.time_left):02d}s",
                (1030, 58),
                "#ffdf6c" if self.time_left > 15 else "#ff8c8c",
                small=True,
            )

        # Draw the fuel bar.
        self.draw_text("FUEL", (34, 642), "#d9edff", small=True)

        pygame.draw.rect(
            self.screen,
            "#1c3248",
            (94, 625, 220, 18),
            border_radius=5,
        )
        pygame.draw.rect(
            self.screen,
            "#5fe1a8",
            (94, 625, int(220 * self.fuel / 100), 18),
            border_radius=5,
        )

        # Display the controls and current message.
        self.draw_text(
            "WASD / ARROWS: THRUST     ESC: RESTART",
            (34, 681),
            "#86a4bd",
            small=True,
        )
        self.draw_text(
            self.message,
            (640, 671),
            "#fff3cf",
            small=True,
            center=True,
        )

        # Show the correct screen when the level ends.
        if self.game_complete:
            self.draw_win_screen()

        elif self.dead or self.won:
            overlay = pygame.Surface(
                (WIDTH, HEIGHT), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 115))
            self.screen.blit(overlay, (0, 0))

            if self.dead:
                headline = "SIGNAL LOST"
            else:
                headline = "SECTOR COMPLETE"

            self.draw_text(
                headline,
                (640, 315),
                "#ffffff",
                title=True,
                center=True,
            )
            self.draw_text(
                "Press Enter to continue",
                (640, 355),
                "#d9edff",
                small=True,
                center=True,
            )

        pygame.display.flip()

    def draw_menu_button(self, label, rect, key, selected=False):
        rect = pygame.Rect(rect)
        self.menu_buttons[key] = rect
        fill = "#21415a" if selected else "#12283b"
        border = "#75d7e8" if selected else "#38566d"
        pygame.draw.rect(self.screen, fill, rect, border_radius=10)
        pygame.draw.rect(self.screen, border, rect, width=2, border_radius=10)
        self.draw_text(label, rect.center, "#edf8ff", center=True)

    def draw_menu_screen(self):
        self.screen.fill("#07111f")
        for x, y, radius in self.stars:
            pygame.draw.circle(self.screen, "#9bb9d5", (x, y), max(1, radius // 2))
        self.menu_buttons = {}

        if self.screen_state == "title":
            self.play_title_music()
            self.draw_text("ORBITAL", (640, 185), "#e7f4ff", title=True, center=True)
            self.draw_text("By Mighty1E :)", (640, 231), "#91b8d2", center=True)
            self.draw_menu_button("START GAME", (490, 315, 300, 58), "start", True)
            self.draw_menu_button("SETTINGS", (490, 390, 300, 54), "settings")
            self.draw_menu_button("QUIT", (490, 460, 300, 50), "quit")
            self.draw_text(
            "A journey through gravity, fuel and the stars.",
            (640, 570),
            "#7898b1",
            small=True,
            center=True,
        )

        elif self.screen_state == "settings":
            self.draw_text("SETTINGS", (640, 95), "#e7f4ff", title=True, center=True)
            self.draw_text("Difficulty", (640, 157), "#91b8d2", center=True)
            self.draw_text(
            f"Starting fuel: {self.fuel_setting}%",
            (640, 207),
            "#edf8ff",
            center=True,
        )
            self.draw_menu_button("-", (405, 230, 70, 42), "fuel_down")
            self.draw_menu_button("+", (805, 230, 70, 42), "fuel_up")
            scale_label = {
            0.8: "Small",
            1.0: "Normal",
            1.2: "Large",
        }.get(self.planet_scale, "Normal")
            self.draw_text(f"Planet size: {scale_label}", (640, 296), "#edf8ff", center=True)
            self.draw_menu_button("<", (405, 319, 70, 42), "planet_down")
            self.draw_menu_button(">", (805, 319, 70, 42), "planet_up")
            timer_label = "Off" if not self.timer_setting else f"{self.timer_setting} seconds"
            self.draw_text(f"Level timer: {timer_label}", (640, 385), "#edf8ff", center=True)
            self.draw_menu_button("<", (405, 408, 70, 42), "timer_down")
            self.draw_menu_button(">", (805, 408, 70, 42), "timer_up")
            self.draw_text(
            f"Music volume: {round(self.music_volume * 100)}%",
            (640, 474),
            "#edf8ff",
            center=True,
        )
            self.draw_menu_button("-", (405, 497, 70, 42), "volume_down")
            self.draw_menu_button("+", (805, 497, 70, 42), "volume_up")
            self.draw_menu_button("CREDITS", (490, 560, 145, 48), "credits")
            self.draw_menu_button("BACK", (645, 560, 145, 48), "back")
            self.draw_text(
            "Changes apply when you start or restart a sector.",
            (640, 635),
            "#7898b1",
            small=True,
            center=True,
        )

        elif self.screen_state == "credits":
            self.draw_text("CREDITS", (640, 180), "#e7f4ff", title=True, center=True)
            self.draw_text("Music: Juhani Junkala", (640, 280), "#edf8ff", center=True)
            self.draw_text(
            "Retro Game Music Pack (CC0)",
            (640, 315),
            "#91b8d2",
            small=True,
            center=True,
        )
            self.draw_text("Game by Mighty1E", (640, 355), "#edf8ff", center=True)
            self.draw_menu_button("BACK TO SETTINGS", (490, 435, 300, 54), "credits_back", True)

        elif self.screen_state == "tutorial":
            self.draw_text("YOUR MISSION", (640, 105), "#e7f4ff", title=True, center=True)
            self.draw_text(
            "Collect every glowing energy core in the sector.",
            (640, 205),
            "#edf8ff",
            center=True,
        )
            self.draw_text(
            "Then fly into the gate to reach the next sector.",
            (640, 245),
            "#edf8ff",
            center=True,
        )
            self.draw_text(
            "Avoid planets and stay inside the screen.",
            (640, 285),
            "#edf8ff",
            center=True,
        )
            self.draw_text("WASD or arrow keys: thrust / steer", (640, 365), "#91dce8", center=True)
            self.draw_text(
            "M: mute or unmute music     ESC: restart sector",
            (640, 405),
            "#91dce8",
            center=True,
        )
            self.draw_text(
            "Collecting a core restores some fuel.",
            (640, 455),
            "#edf8ff",
            center=True,
        )
            self.draw_menu_button("LET'S FLY", (490, 525, 300, 56), "tutorial_start", True)

    def handle_menu_click(self, position):
        for key, rect in self.menu_buttons.items():
            if rect.collidepoint(position):
                if key == "start":
                    self.level_index = 0
                    self.load_level()
                    pygame.mixer.music.set_volume(self.music_volume)
                    self.screen_state = "tutorial" if not self.tutorial_seen else "game"
                elif key == "settings":
                    self.settings_return = self.screen_state
                    self.screen_state = "settings"
                elif key == "quit":
                    pygame.quit()
                    sys.exit()
                elif key == "back":
                    self.screen_state = self.settings_return
                elif key == "credits":
                    self.screen_state = "credits"
                elif key == "credits_back":
                    self.screen_state = "settings"
                elif key == "tutorial_start":
                    self.tutorial_seen = True
                    self.tutorial_flag.touch(exist_ok=True)
                    self.screen_state = "game"
                elif key == "fuel_down":
                    self.fuel_setting = max(25, self.fuel_setting - 25)
                elif key == "fuel_up":
                    self.fuel_setting = min(200, self.fuel_setting + 25)
                elif key == "planet_down":
                    self.planet_scale = max(0.8, round(self.planet_scale - 0.2, 1))
                elif key == "planet_up":
                    self.planet_scale = min(1.2, round(self.planet_scale + 0.2, 1))
                elif key == "timer_down":
                    options = [0, 60, 90, 120, 180]
                    self.timer_setting = options[max(0, options.index(self.timer_setting) - 1)]
                elif key == "timer_up":
                    options = [0, 60, 90, 120, 180]
                    self.timer_setting = options[min(len(options) - 1, options.index(self.timer_setting) + 1)]
                elif key == "volume_down":
                    self.music_volume = max(0.0, round(self.music_volume - 0.1, 2))
                    pygame.mixer.music.set_volume(self.music_volume)
                elif key == "volume_up":
                    self.music_volume = min(1.0, round(self.music_volume + 0.1, 2))
                    pygame.mixer.music.set_volume(self.music_volume)
                return

    def draw_wobbly_circle(
        self,
        position,
        radius,
        colour,
        seed,
        outline=0,
        fill=True,
    ):
        # Make a slightly uneven circle for a hand-drawn look.
        points = []

        for index in range(18):
            angle = math.tau * index / 18

            wobble = (
                math.sin(index * 2.17 + seed) * 0.07
                + math.sin(index * 4.3 + seed) * 0.035
            )

            distance = radius * (1 + wobble)

            points.append(
                (
                    int(position.x + math.cos(angle) * distance),
                    int(position.y + math.sin(angle) * distance),
                )
            )

        # Fill the shape and draw its outline if needed.
        if fill:
            pygame.draw.polygon(self.screen, colour, points)

        if outline:
            pygame.draw.lines(
                self.screen,
                "#302c2c",
                True,
                points,
                outline,
            )

    def draw_planet(self, position, radius, colour, style):
        # Add a faint glow around the planet.
        glow = pygame.Surface(
            (radius * 3, radius * 3), pygame.SRCALPHA
        )

        pygame.draw.circle(
            glow,
            (*colour[:3], 28),
            (int(radius * 1.5), int(radius * 1.5)),
            radius + 18,
        )

        self.screen.blit(
            glow,
            (position.x - radius * 1.5, position.y - radius * 1.5),
        )

        # Draw the main planet.
        self.draw_wobbly_circle(
            position, radius, colour, style + radius, outline=6
        )

        light = colour.lerp(pygame.Color("#ffffff"), 0.24)
        dark = colour.lerp(pygame.Color("#302c2c"), 0.24)

        # Give each planet a different appearance.
        if style == 0:
            # Small craters on the planet's surface.
            for offset, size in [
                ((-0.25, -0.28), 0.17),
                ((0.27, 0.11), 0.12),
                ((-0.1, 0.32), 0.09),
            ]:
                centre = position + pygame.Vector2(
                    offset[0] * radius,
                    offset[1] * radius,
                )

                self.draw_wobbly_circle(
                    centre,
                    radius * size,
                    light,
                    int(radius * size),
                    outline=3,
                )

                self.draw_wobbly_circle(
                    centre + pygame.Vector2(2, 3),
                    radius * size * 0.42,
                    dark,
                    int(radius * size + 1),
                    outline=2,
                )

        elif style == 1:
            # Horizontal stripes across the planet.
            for line in (-0.35, -0.1, 0.16, 0.4):
                y = position.y + line * radius

                pygame.draw.line(
                    self.screen,
                    dark,
                    (position.x - radius * 0.72, y),
                    (position.x + radius * 0.72, y - radius * 0.14),
                    7,
                )

                pygame.draw.line(
                    self.screen,
                    "#302c2c",
                    (position.x - radius * 0.72, y),
                    (position.x + radius * 0.72, y - radius * 0.14),
                    2,
                )

        else:
            # Draw a ring around the planet.
            ring_rect = pygame.Rect(
                int(position.x - radius * 1.33),
                int(position.y - radius * 0.43),
                int(radius * 2.66),
                int(radius * 0.86),
            )

            pygame.draw.ellipse(
                self.screen, "#302c2c", ring_rect, 7
            )
            pygame.draw.ellipse(
                self.screen, light, ring_rect, 3
            )

            # Add a few craters as well.
            for offset in [
                (-0.27, -0.18),
                (0.22, 0.24),
                (0.33, -0.13),
            ]:
                centre = position + pygame.Vector2(
                    offset[0] * radius,
                    offset[1] * radius,
                )

                self.draw_wobbly_circle(
                    centre,
                    radius * 0.13,
                    dark,
                    int(radius * 3 + offset[0] * 10),
                    outline=2,
                )

    def draw_win_screen(self):
        # Darken the screen for the ending scene.
        overlay = pygame.Surface(
            (WIDTH, HEIGHT), pygame.SRCALPHA
        )
        overlay.fill((8, 11, 28, 218))
        self.screen.blit(overlay, (0, 0))

        self.draw_text(
            "WELCOME HOME, PILOT!",
            (640, 104),
            "#fff6d9",
            title=True,
            center=True,
        )
        self.draw_text(
            "Earth celebrates your return from Sector Three.",
            (640, 145),
            "#bde1e8",
            small=True,
            center=True,
        )

        # Draw Earth in the background.
        earth = pygame.Vector2(1030, 228)

        self.draw_wobbly_circle(
            earth, 86, pygame.Color("#70bfe1"), 91, outline=6
        )

        for offset, size in [
            ((-0.28, -0.13), 0.23),
            ((0.19, 0.11), 0.19),
            ((-0.03, 0.35), 0.16),
        ]:
            self.draw_wobbly_circle(
                earth + pygame.Vector2(
                    offset[0] * 86,
                    offset[1] * 86,
                ),
                86 * size,
                pygame.Color("#91c879"),
                93 + int(size * 10),
                outline=2,
            )

        # Draw the people celebrating the player's return.
        crowd_colours = [
            "#f19c9c",
            "#bd94e5",
            "#9bd681",
            "#f1c279",
        ]

        for index in range(8):
            if index < 4:
                x = 135 + index * 112
            else:
                x = 795 + (index - 4) * 102

            y = 398 + int(math.sin(index * 2.4) * 12)
            body_colour = pygame.Color(
                crowd_colours[index % 4]
            )

            # Head and eyes.
            self.draw_wobbly_circle(
                pygame.Vector2(x, y - 42),
                17,
                pygame.Color("#f3f0e8"),
                index + 70,
                outline=4,
            )

            pygame.draw.circle(
                self.screen, "#302c2c", (x - 5, y - 44), 3
            )
            pygame.draw.circle(
                self.screen, "#302c2c", (x + 6, y - 44), 3
            )

            # Body and clothes.
            body_rect = pygame.Rect(x - 21, y - 20, 42, 51)

            pygame.draw.rect(
                self.screen, "#302c2c", body_rect, border_radius=5
            )
            pygame.draw.rect(
                self.screen,
                body_colour,
                body_rect.inflate(-8, -8),
                border_radius=4,
            )

            # Arms and legs.
            pygame.draw.line(
                self.screen,
                "#302c2c",
                (x - 18, y - 8),
                (x - 36, y - 37),
                5,
            )
            pygame.draw.line(
                self.screen,
                "#302c2c",
                (x + 18, y - 8),
                (x + 36, y - 37),
                5,
            )
            pygame.draw.line(
                self.screen,
                "#302c2c",
                (x - 11, y + 27),
                (x - 15, y + 45),
                5,
            )
            pygame.draw.line(
                self.screen,
                "#302c2c",
                (x + 11, y + 27),
                (x + 15, y + 45),
                5,
            )

        # Draw the podium.
        pygame.draw.polygon(
            self.screen,
            "#302c2c",
            [(518, 520), (762, 520), (724, 586), (556, 586)],
        )
        pygame.draw.polygon(
            self.screen,
            "#e5b96c",
            [(527, 524), (753, 524), (717, 578), (563, 578)],
        )

        # Draw the pilot.
        self.draw_wobbly_circle(
            pygame.Vector2(640, 302),
            37,
            pygame.Color("#f3f0e8"),
            119,
            outline=6,
        )

        pygame.draw.circle(
            self.screen, "#302c2c", (628, 300), 5
        )
        pygame.draw.circle(
            self.screen, "#302c2c", (652, 300), 5
        )

        pygame.draw.rect(
            self.screen,
            "#302c2c",
            (594, 337, 92, 142),
            border_radius=12,
        )
        pygame.draw.rect(
            self.screen,
            "#e7edf2",
            (602, 345, 76, 126),
            border_radius=9,
        )
        pygame.draw.rect(
            self.screen,
            "#77a8c7",
            (615, 360, 50, 34),
            border_radius=4,
        )

        # Legs and medal ribbons.
        pygame.draw.line(
            self.screen, "#302c2c", (620, 468), (611, 519), 8
        )
        pygame.draw.line(
            self.screen, "#302c2c", (660, 468), (669, 519), 8
        )
        pygame.draw.line(
            self.screen, "#d44956", (621, 340), (640, 393), 6
        )
        pygame.draw.line(
            self.screen, "#4776c5", (659, 340), (640, 393), 6
        )

        # The medal and the final message.
        self.draw_wobbly_circle(
            pygame.Vector2(640, 402),
            16,
            pygame.Color("#f4c64e"),
            120,
            outline=4,
        )

        self.draw_text(
            "MEDAL OF ORBIT",
            (640, 628),
            "#fff6d9",
            small=True,
            center=True,
        )
        self.draw_text(
            "Press Enter to fly again",
            (640, 676),
            "#fff6d9",
            small=True,
            center=True,
        )

    def run(self):
        # Keep the game running until the player closes it.
        while True:
            delta = self.clock.tick(FPS) / 1000.0

            # Check for keyboard input and window events.
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.screen_state != "game":
                        self.handle_menu_click(event.pos)

                if event.type == pygame.KEYDOWN:
                    if self.screen_state == "title":
                        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            self.level_index = 0
                            self.load_level()
                            pygame.mixer.music.set_volume(self.music_volume)
                            self.screen_state = "tutorial" if not self.tutorial_seen else "game"
                        elif event.key == pygame.K_s:
                            self.settings_return = "title"
                            self.screen_state = "settings"
                        elif event.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()
                    elif self.screen_state == "settings":
                        if event.key == pygame.K_ESCAPE:
                            self.screen_state = self.settings_return
                        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                            volume_step = 0.05 if event.key == pygame.K_RIGHT else -0.05
                            self.music_volume = min(
                                1.0, max(0.0, self.music_volume + volume_step)
                            )
                            pygame.mixer.music.set_volume(self.music_volume)
                    elif self.screen_state == "credits":
                        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                            self.screen_state = "settings"
                    elif self.screen_state == "tutorial":
                        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            self.tutorial_seen = True
                            self.screen_state = "game"
                    else:
                        # Restart the current sector.
                        if event.key == pygame.K_ESCAPE:
                            self.load_level()

                        # Toggle the background music.
                        if event.key == pygame.K_m and self.music_available:
                            if pygame.mixer.music.get_busy():
                                pygame.mixer.music.pause()
                            else:
                                pygame.mixer.music.unpause()

                        # Restart the game after the final sector.
                        if event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.game_complete:
                            # Stop the ending track and return to the title screen.
                            self.stop_victory_music()
                            pygame.mixer.music.stop()
                            self.title_music_playing = False
                            self.level_index = 0
                            self.load_level()
                            self.screen_state = "title"

                        # Move to the next sector or retry after losing.
                        elif (
                            event.key in (pygame.K_RETURN, pygame.K_SPACE)
                            and (self.dead or self.won)
                        ):
                            if self.won and self.level_index < len(LEVELS) - 1:
                                self.level_index += 1
                            self.load_level()

            # Update the game and draw the next frame.
            self.update(delta)
            self.draw()


# Start the game.
if __name__ == "__main__":
    Orbital().run()
