"""ORBITAL” a small Pygame gravity arcade game for Hack Club Snek."""

import math
import sys
from array import array
from pathlib import Path

import pygame


WIDTH, HEIGHT = 1280, 720
FPS = 60
SHIP_RADIUS = 12
THRUST = 390.0
GRAVITY = 9000.0
MAX_SPEED = 620.0
FUEL_DRAIN = 14.0

LEVELS = [
    {
        "spawn": (160, 535),
        "planets": [((600, 360), 82, "#805ad5")],
        "cores": [(700, 185), (940, 380)],
        "gate": (1100, 550),
    },
    {
        "spawn": (145, 565),
        "planets": [((470, 450), 66, "#e76f51"), ((820, 255), 98, "#457b9d")],
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
    def __init__(self) -> None:
        pygame.mixer.pre_init(22_050, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption("ORBITAL")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 28)
        self.title_font = pygame.font.Font(None, 44)
        self.small_font = pygame.font.Font(None, 22)
        self.stars = [
            ((i * 179) % 1260 + 10, (i * 83) % 690 + 10, 1 + i % 3)
            for i in range(90)
        ]
        self.asset_folder = Path(__file__).resolve().parent / "assets"
        ship_path = self.asset_folder / "ship.png"
        if not ship_path.is_file():
            raise FileNotFoundError(
                f"Missing ship sprite: {ship_path}. "
                "Save a ship PNG from the asset pack as assets/ship.png."
            )
        self.ship_sprite = pygame.image.load(str(ship_path)).convert_alpha()
        self.ship_sprite = pygame.transform.smoothscale(self.ship_sprite, (42, 30))
        self.music_tracks = self.load_music_tracks()
        self.music_channels: list[pygame.mixer.Channel | None] = []
        self.level_index = 0
        self.load_level()

    def load_music_tracks(self) -> list[pygame.mixer.Sound]:
        """Load the three music layers from the assets folder."""
        if not pygame.mixer.get_init():
            return []

        music_folder = self.asset_folder / "music"
        tracks = []
        for filename in ("ambient.ogg", "bass.ogg", "melody.ogg"):
            path = music_folder / filename
            if not path.is_file():
                print(f"Music layer not found: {path}")
                return []
            try:
                tracks.append(pygame.mixer.Sound(str(path)))
            except pygame.error as error:
                print(f"Could not load music {path}: {error}")
                return []
        return tracks
    def play_music_for_level(self) -> None:
        # Keep all layers running so they stay in time between sectors.
        if not self.music_channels:
            for track in self.music_tracks:
                self.music_channels.append(track.play(loops=-1))
        volumes = [0.45, 0.0, 0.0]
        if self.level_index >= 1:
            volumes[1] = 0.35
        if self.level_index >= 2:
            volumes[2] = 0.30
        for index, channel in enumerate(self.music_channels):
            if channel:
                channel.set_volume(volumes[index])
    def load_level(self) -> None:
        self.play_music_for_level()
        level = LEVELS[self.level_index]
        self.ship_position = pygame.Vector2(level["spawn"])
        self.ship_velocity = pygame.Vector2()
        self.ship_angle = 0.0
        self.planets = [
            (pygame.Vector2(position), radius, pygame.Color(colour))
            for position, radius, colour in level["planets"]
        ]
        self.cores = [pygame.Vector2(core) for core in level["cores"]]
        self.total_cores = len(self.cores)
        self.gate = pygame.Vector2(level["gate"])
        self.fuel = 100.0
        self.message = "Collect every energy core, then reach the gate."
        self.dead = False
        self.won = False
        self.game_complete = False

    def update(self, delta: float) -> None:
        if self.dead or self.won:
            return

        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            - int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            int(keys[pygame.K_s] or keys[pygame.K_DOWN])
            - int(keys[pygame.K_w] or keys[pygame.K_UP]),
        )
        if direction.length_squared() and self.fuel > 0:
            direction = direction.normalize()
            self.ship_velocity += direction * THRUST * delta
            # A small side-thruster assist removes the frustrating sideways slide
            # while still leaving enough momentum for orbital routes.
            sideways_velocity = self.ship_velocity - direction * self.ship_velocity.dot(direction)
            self.ship_velocity -= sideways_velocity * min(0.75 * delta, 0.12)
            self.fuel = max(0.0, self.fuel - FUEL_DRAIN * delta)

        # Light stabilisers make the ship much easier to steer while preserving
        # the momentum needed for satisfying gravity slingshots.
        self.ship_velocity *= 0.993 ** (delta * 60)

        for planet_position, radius, _colour in self.planets:
            offset = planet_position - self.ship_position
            distance_squared = max(offset.length_squared(), 2500.0)
            self.ship_velocity += (
                offset.normalize() * GRAVITY * radius / distance_squared * delta
            )
            if offset.length() < radius + SHIP_RADIUS:
                self.die("Your ship was pulled into a planet. Press Enter to retry.")
                return

        if self.ship_velocity.length() > MAX_SPEED:
            self.ship_velocity.scale_to_length(MAX_SPEED)
        if self.ship_velocity.length() > 12:
            target_angle = -math.degrees(math.atan2(self.ship_velocity.y, self.ship_velocity.x))
            angle_difference = (target_angle - self.ship_angle + 180) % 360 - 180
            self.ship_angle += angle_difference * min(9.0 * delta, 1.0)
        self.ship_position += self.ship_velocity * delta

        if not (-30 < self.ship_position.x < WIDTH + 30 and -30 < self.ship_position.y < HEIGHT + 30):
            self.die("You drifted into deep space. Press Enter to retry.")
            return

        for core in self.cores[:]:
            if self.ship_position.distance_to(core) < 28:
                self.cores.remove(core)
                self.fuel = min(100.0, self.fuel + 18.0)
                self.message = "Core collected. Fuel restored."

        if not self.cores and self.ship_position.distance_to(self.gate) < 42:
            self.won = True
            if self.level_index == len(LEVELS) - 1:
                self.game_complete = True
                self.message = "Transmission complete."
            else:
                self.message = "Jump successful. Press Enter for the next sector."

    def die(self, message: str) -> None:
        self.dead = True
        self.message = message

    def draw_text(self, text: str, position: tuple[int, int], colour: str | pygame.Color, *, small: bool = False, title: bool = False, center: bool = False) -> None:
        font = self.title_font if title else self.small_font if small else self.font
        surface = font.render(text, True, colour)
        rect = surface.get_rect(center=position) if center else surface.get_rect(topleft=position)
        self.screen.blit(surface, rect)

    def draw(self) -> None:
        self.screen.fill("#07111f")
        for x, y, radius in self.stars:
            pygame.draw.rect(self.screen, "#9bb9d5", (x, y, max(1, radius // 2), max(1, radius // 2)))

        for planet_number, (position, radius, colour) in enumerate(self.planets):
            self.draw_planet(position, radius, colour, (planet_number + self.level_index) % 3)

        for core in self.cores:
            self.draw_wobbly_circle(core, 16, pygame.Color("#ffdf6c"), 37, outline=4)
            self.draw_wobbly_circle(core - pygame.Vector2(3, 4), 7, pygame.Color("#fff5bf"), 38)

        gate_colour = pygame.Color("#69f0ae") if not self.cores else pygame.Color("#536475")
        self.draw_wobbly_circle(self.gate, 28, gate_colour, 17, outline=5, fill=False)
        self.draw_wobbly_circle(self.gate, 38, pygame.Color(*gate_colour[:3], 65), 18, outline=3, fill=False)

        rotated_ship = pygame.transform.rotate(self.ship_sprite, self.ship_angle)
        ship_rect = rotated_ship.get_rect(center=(int(self.ship_position.x), int(self.ship_position.y)))
        self.screen.blit(rotated_ship, ship_rect)

        self.draw_text("ORBITAL", (34, 24), "#d9edff", title=True)
        self.draw_text(f"SECTOR {self.level_index + 1} / {len(LEVELS)}", (35, 70), "#86a4bd", small=True)
        self.draw_text(f"CORES {self.total_cores - len(self.cores)} / {self.total_cores}", (1030, 32), "#ffdf6c", small=True)
        self.draw_text("FUEL", (34, 642), "#d9edff", small=True)
        pygame.draw.rect(self.screen, "#1c3248", (94, 625, 220, 18), border_radius=5)
        pygame.draw.rect(self.screen, "#5fe1a8", (94, 625, int(220 * self.fuel / 100), 18), border_radius=5)
        self.draw_text("WASD / ARROWS: THRUST     ESC: RESTART", (34, 681), "#86a4bd", small=True)
        self.draw_text(self.message, (640, 671), "#fff3cf", small=True, center=True)

        if self.game_complete:
            self.draw_win_screen()
        elif self.dead or self.won:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 115))
            self.screen.blit(overlay, (0, 0))
            headline = "SIGNAL LOST" if self.dead else "SECTOR COMPLETE"
            self.draw_text(headline, (640, 315), "#ffffff", title=True, center=True)
            self.draw_text("Press Enter to continue", (640, 355), "#d9edff", small=True, center=True)

        pygame.display.flip()

    def draw_wobbly_circle(self, position: pygame.Vector2, radius: float, colour: pygame.Color, seed: int, *, outline: int = 0, fill: bool = True) -> None:
        points = []
        for index in range(18):
            angle = math.tau * index / 18
            wobble = math.sin(index * 2.17 + seed) * 0.07 + math.sin(index * 4.3 + seed) * 0.035
            distance = radius * (1 + wobble)
            points.append((int(position.x + math.cos(angle) * distance), int(position.y + math.sin(angle) * distance)))
        if fill:
            pygame.draw.polygon(self.screen, colour, points)
        if outline:
            pygame.draw.lines(self.screen, "#302c2c", True, points, outline)

    def draw_planet(self, position: pygame.Vector2, radius: int, colour: pygame.Color, style: int) -> None:
        glow = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*colour[:3], 28), (radius * 1.5, radius * 1.5), radius + 18)
        self.screen.blit(glow, (position.x - radius * 1.5, position.y - radius * 1.5))
        self.draw_wobbly_circle(position, radius, colour, style + radius, outline=6)
        light = colour.lerp(pygame.Color("#ffffff"), 0.24)
        dark = colour.lerp(pygame.Color("#302c2c"), 0.24)

        if style == 0:
            for offset, size in [((-0.25, -0.28), 0.17), ((0.27, 0.11), 0.12), ((-0.1, 0.32), 0.09)]:
                centre = position + pygame.Vector2(offset[0] * radius, offset[1] * radius)
                self.draw_wobbly_circle(centre, radius * size, light, int(radius * size), outline=3)
                self.draw_wobbly_circle(centre + pygame.Vector2(2, 3), radius * size * .42, dark, int(radius * size + 1), outline=2)
        elif style == 1:
            for line in (-.35, -.1, .16, .4):
                y = position.y + line * radius
                pygame.draw.line(self.screen, dark, (position.x - radius * .72, y), (position.x + radius * .72, y - radius * .14), 7)
                pygame.draw.line(self.screen, "#302c2c", (position.x - radius * .72, y), (position.x + radius * .72, y - radius * .14), 2)
        else:
            ring_rect = pygame.Rect(int(position.x - radius * 1.33), int(position.y - radius * .43), int(radius * 2.66), int(radius * .86))
            pygame.draw.ellipse(self.screen, "#302c2c", ring_rect, 7)
            pygame.draw.ellipse(self.screen, light, ring_rect, 3)
            for offset in ((-.27, -.18), (.22, .24), (.33, -.13)):
                centre = position + pygame.Vector2(offset[0] * radius, offset[1] * radius)
                self.draw_wobbly_circle(centre, radius * .13, dark, int(radius * 3 + offset[0] * 10), outline=2)

    def draw_win_screen(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 11, 28, 218))
        self.screen.blit(overlay, (0, 0))
        self.draw_text("WELCOME HOME, PILOT!", (640, 104), "#fff6d9", title=True, center=True)
        self.draw_text("Earth celebrates your return from Sector Three.", (640, 145), "#bde1e8", small=True, center=True)

        # A hand-drawn Earth behind the homecoming ceremony.
        earth = pygame.Vector2(1030, 228)
        self.draw_wobbly_circle(earth, 86, pygame.Color("#70bfe1"), 91, outline=6)
        for offset, size in [((-.28, -.13), .23), ((.19, .11), .19), ((-.03, .35), .16)]:
            self.draw_wobbly_circle(earth + pygame.Vector2(offset[0] * 86, offset[1] * 86), 86 * size, pygame.Color("#91c879"), 93 + int(size * 10), outline=2)

        # The crowd: wobbly, bright, and visibly clapping around the pilot.
        for index in range(8):
            x = 135 + index * 112 if index < 4 else 795 + (index - 4) * 102
            y = 398 + int(math.sin(index * 2.4) * 12)
            body = pygame.Color(["#f19c9c", "#bd94e5", "#9bd681", "#f1c279"][index % 4])
            self.draw_wobbly_circle(pygame.Vector2(x, y - 42), 17, pygame.Color("#f3f0e8"), index + 70, outline=4)
            pygame.draw.circle(self.screen, "#302c2c", (x - 5, y - 44), 3)
            pygame.draw.circle(self.screen, "#302c2c", (x + 6, y - 44), 3)
            body_rect = pygame.Rect(x - 21, y - 20, 42, 51)
            pygame.draw.rect(self.screen, "#302c2c", body_rect, border_radius=5)
            pygame.draw.rect(self.screen, body, body_rect.inflate(-8, -8), border_radius=4)
            pygame.draw.line(self.screen, "#302c2c", (x - 18, y - 8), (x - 36, y - 37), 5)
            pygame.draw.line(self.screen, "#302c2c", (x + 18, y - 8), (x + 36, y - 37), 5)
            pygame.draw.line(self.screen, "#302c2c", (x - 11, y + 27), (x - 15, y + 45), 5)
            pygame.draw.line(self.screen, "#302c2c", (x + 11, y + 27), (x + 15, y + 45), 5)

        # Pilot on a podium with a gold medal. This uses the same chunky outline style.
        pygame.draw.polygon(self.screen, "#302c2c", [(518, 520), (762, 520), (724, 586), (556, 586)])
        pygame.draw.polygon(self.screen, "#e5b96c", [(527, 524), (753, 524), (717, 578), (563, 578)])
        self.draw_wobbly_circle(pygame.Vector2(640, 302), 37, pygame.Color("#f3f0e8"), 119, outline=6)
        pygame.draw.circle(self.screen, "#302c2c", (628, 300), 5)
        pygame.draw.circle(self.screen, "#302c2c", (652, 300), 5)
        pygame.draw.rect(self.screen, "#302c2c", (594, 337, 92, 142), border_radius=12)
        pygame.draw.rect(self.screen, "#e7edf2", (602, 345, 76, 126), border_radius=9)
        pygame.draw.rect(self.screen, "#77a8c7", (615, 360, 50, 34), border_radius=4)
        pygame.draw.line(self.screen, "#302c2c", (620, 468), (611, 519), 8)
        pygame.draw.line(self.screen, "#302c2c", (660, 468), (669, 519), 8)
        pygame.draw.line(self.screen, "#d44956", (621, 340), (640, 393), 6)
        pygame.draw.line(self.screen, "#4776c5", (659, 340), (640, 393), 6)
        self.draw_wobbly_circle(pygame.Vector2(640, 402), 16, pygame.Color("#f4c64e"), 120, outline=4)
        self.draw_text("MEDAL OF ORBIT", (640, 628), "#fff6d9", small=True, center=True)
        self.draw_text("Press Enter to fly again", (640, 676), "#fff6d9", small=True, center=True)

    def run(self) -> None:
        while True:
            delta = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.load_level()
                    if event.key == pygame.K_m and self.music_tracks:
                        if pygame.mixer.get_busy():
                            pygame.mixer.pause()
                        else:
                            pygame.mixer.unpause()
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.game_complete:
                        self.level_index = 0
                        self.load_level()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE) and (self.dead or self.won):
                        if self.won and self.level_index < len(LEVELS) - 1:
                            self.level_index += 1
                        self.load_level()
            self.update(delta)
            self.draw()


if __name__ == "__main__":
    Orbital().run()
