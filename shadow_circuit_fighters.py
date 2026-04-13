import pygame
import sys
import math
import random
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 50, 50)
BLUE = (50, 100, 220)
GREEN = (50, 200, 100)
YELLOW = (255, 215, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
PURPLE = (147, 0, 211)
ORANGE = (255, 140, 0)

# Game States
class GameState(Enum):
    MENU = 1
    CHARACTER_SELECT = 2
    FIGHTING = 3
    PAUSED = 4
    VICTORY = 5
    STORY = 6

# Fighter States
class FighterState(Enum):
    IDLE = 1
    WALKING = 2
    JUMPING = 3
    ATTACKING = 4
    BLOCKING = 5
    HIT = 6
    KNOCKDOWN = 7
    SPECIAL = 8

@dataclass
class CharacterInfo:
    name: str
    title: str
    backstory: str
    motivation: str
    special_move: str
    color: Tuple[int, int, int]
    speed: float
    health: int
    damage_mult: float
    # Character Database
CHARACTERS = {
    "kira": CharacterInfo(
        name="Kira Vance",
        title="The Cyber-Sentinel",
        backstory="Former corporate security chief who discovered her employer was running illegal experiments on homeless populations. After blowing the whistle, she was targeted by assassins. Now she fights in underground circuits to fund her investigation into the conspiracy that destroyed her career.",
        motivation="Expose the truth and protect the innocent from corporate exploitation.",
        special_move="Neural Overload - Disables opponent's controls temporarily",
        color=BLUE,
        speed=6.5,
        health=100,
        damage_mult=1.0
    ),
    "magnus": CharacterInfo(
        name="Magnus Thorne",
        title="The Iron Judge",
        backstory="A disbarred prosecutor who discovered that the justice system he served was rigged. When he tried to expose judicial corruption, he was framed and imprisoned. He broke out during a prison transfer and now fights to gather evidence against the corrupt officials who ruined his life.",
        motivation="Restore integrity to the system he once believed in.",
        special_move="Verdict - Heavy armor break that stuns opponents",
        color=RED,
        speed=5.0,
        health=120,
        damage_mult=1.2
    ),
    "zara": CharacterInfo(
        name="Zara Chen",
        title="The Phantom Broker",
        backstory="An investigative journalist who uncovered a human trafficking ring connected to powerful figures. When authorities refused to act on her evidence, she went underground, using her fighting skills—honed from years of parkour and self-defense training—to disrupt operations and rescue victims.",
        motivation="Give voice to the voiceless and dismantle criminal networks.",
        special_move="Shadow Step - Teleports behind opponent for guaranteed hit",
        color=PURPLE,
        speed=8.0,
        health=85,
        damage_mult=0.9
    ),
    "rocco": CharacterInfo(
        name='Rocco "Bull" Marchetti',
        title="The Reformed Enforcer",
        backstory="Former debt collector for organized crime who had a crisis of conscience after accidentally injuring an innocent family. He turned state's witness, entered witness protection, but the program failed him. Now he fights to stay alive while trying to make amends for his past.",
        motivation="Redemption and protecting those who can't protect themselves.",
        special_move="Bull Rush - Unstoppable charging tackle",
        color=ORANGE,
        speed=4.5,
        health=130,
        damage_mult=1.3
    )
}
class Fighter:
    def __init__(self, char_key: str, x: float, y: float, facing_right: bool):
        self.char_info = CHARACTERS[char_key]
        self.x = x
        self.y = y
        self.width = 60
        self.height = 100
        self.facing_right = facing_right

        # Physics
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = True
        self.gravity = 0.8
        self.jump_strength = -15

        # Combat stats
        self.max_health = self.char_info.health
        self.health = self.max_health
        self.speed = self.char_info.speed
        self.damage_mult = self.char_info.damage_mult

        # State
        self.state = FighterState.IDLE
        self.state_timer = 0
        self.attack_cooldown = 0
        self.hitstun = 0
        self.blocking = False

        # Animation
        self.anim_frame = 0
        self.anim_timer = 0

        # Special meter
        self.special_meter = 0
        self.max_special = 100

        # Combo system
        self.combo_count = 0
        self.combo_timer = 0

        # Visual effects
        self.flash_timer = 0
        self.particles: List[dict] = []

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - self.width//2, self.y - self.height, self.width, self.height)

    def get_hitbox(self) -> Optional[pygame.Rect]:
        if self.state != FighterState.ATTACKING:
            return None

        # Attack hitbox extends in facing direction
        attack_range = 80
        if self.facing_right:
            return pygame.Rect(self.x + self.width//2, self.y - self.height + 20, attack_range, 60)
        else:
            return pygame.Rect(self.x - self.width//2 - attack_range, self.y - self.height + 20, attack_range, 60)

    def move(self, direction: int):
        if self.state in [FighterState.HIT, FighterState.KNOCKDOWN, FighterState.ATTACKING]:
            return

        self.vel_x = direction * self.speed
        if direction != 0:
            self.facing_right = direction > 0
            if self.on_ground:
                self.state = FighterState.WALKING
        elif self.on_ground:
            self.state = FighterState.IDLE

    def jump(self):
        if self.on_ground and self.state not in [FighterState.HIT, FighterState.KNOCKDOWN]:
            self.vel_y = self.jump_strength
            self.on_ground = False
            self.state = FighterState.JUMPING

    def attack(self):
        if self.state not in [FighterState.HIT, FighterState.KNOCKDOWN, FighterState.ATTACKING] and self.attack_cooldown <= 0:
            self.state = FighterState.ATTACKING
            self.state_timer = 15  # Attack duration
            self.attack_cooldown = 25
            self.vel_x = 0

    def block(self, blocking: bool):
        if self.on_ground and self.state not in [FighterState.HIT, FighterState.KNOCKDOWN, FighterState.ATTACKING]:
            self.blocking = blocking
            if blocking:
                self.state = FighterState.BLOCKING
                self.vel_x = 0
            else:
                self.state = FighterState.IDLE

    def use_special(self) -> bool:
        if self.special_meter >= self.max_special and self.state not in [FighterState.HIT, FighterState.KNOCKDOWN]:
            self.special_meter = 0
            self.state = FighterState.SPECIAL
            self.state_timer = 40
            return True
        return False
    def take_damage(self, damage: int, knockback: float = 5):
        if self.blocking:
            damage = int(damage * 0.3)
            knockback = knockback * 0.5
            self.special_meter = min(self.max_special, self.special_meter + 10)

        self.health = max(0, self.health - damage)
        self.flash_timer = 10

        # Create hit particles
        for _ in range(5):
            self.particles.append({
                'x': self.x,
                'y': self.y - self.height//2,
                'vx': random.uniform(-3, 3),
                'vy': random.uniform(-5, -2),
                'life': 20,
                'color': RED
            })

        if damage > 20:
            self.state = FighterState.HIT
            self.state_timer = 20
            self.hitstun = 20
            self.vel_x = -knockback if self.facing_right else knockback
            self.vel_y = -5
        else:
            self.hitstun = 10

    def update(self):
        # Physics
        self.vel_y += self.gravity
        self.x += self.vel_x
        self.y += self.vel_y

        # Ground collision
        ground_y = SCREEN_HEIGHT - 100
        if self.y >= ground_y:
            self.y = ground_y
            self.vel_y = 0
            self.on_ground = True
            if self.state == FighterState.JUMPING:
                self.state = FighterState.IDLE
        else:
            self.on_ground = False

        # Screen boundaries
        self.x = max(self.width//2, min(SCREEN_WIDTH - self.width//2, self.x))

        # Friction
        if self.state not in [FighterState.WALKING, FighterState.HIT]:
            self.vel_x *= 0.8

        # State management
        if self.state_timer > 0:
            self.state_timer -= 1
            if self.state_timer <= 0:
                if self.state in [FighterState.ATTACKING, FighterState.HIT, FighterState.SPECIAL]:
                    self.state = FighterState.IDLE

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.hitstun > 0:
            self.hitstun -= 1

        if self.flash_timer > 0:
            self.flash_timer -= 1

        # Combo timer
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer <= 0:
                self.combo_count = 0

        # Special meter regeneration
        if self.special_meter < self.max_special:
            self.special_meter = min(self.max_special, self.special_meter + 0.1)

        # Update particles
        for p in self.particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.5
            p['life'] -= 1
            if p['life'] <= 0:
                self.particles.remove(p)
def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        # Flash effect when hit
        if self.flash_timer > 0 and self.flash_timer % 2 == 0:
            color = WHITE
        else:
            color = self.char_info.color

        # Body
        rect = self.get_rect()
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, BLACK, rect, 2)

        # Head
        head_radius = 20
        head_y = self.y - self.height - head_radius + 10
        pygame.draw.circle(screen, (255, 220, 177), (int(self.x), int(head_y)), head_radius)
        pygame.draw.circle(screen, BLACK, (int(self.x), int(head_y)), head_radius, 2)

        # Eyes (direction)
        eye_offset = 8 if self.facing_right else -8
        pygame.draw.circle(screen, BLACK, (int(self.x + eye_offset), int(head_y - 2)), 3)
        pygame.draw.circle(screen, BLACK, (int(self.x + eye_offset), int(head_y + 5)), 3)

        # Attack visual
        if self.state == FighterState.ATTACKING:
            hitbox = self.get_hitbox()
            if hitbox:
                pygame.draw.rect(screen, YELLOW, hitbox, 3)
                # Swipe effect
                points = []
                if self.facing_right:
                    for i in range(5):
                        points.append((hitbox.x + i*15, hitbox.centery + random.randint(-10, 10)))
                else:
                    for i in range(5):
                        points.append((hitbox.right - i*15, hitbox.centery + random.randint(-10, 10)))
                if len(points) > 1:
                    pygame.draw.lines(screen, YELLOW, False, points, 3)

        # Special effect
        if self.state == FighterState.SPECIAL:
            pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y - self.height//2)), 60, 3)
            for angle in range(0, 360, 30):
                rad = math.radians(angle + pygame.time.get_ticks() // 10)
                px = self.x + math.cos(rad) * 70
                py = self.y - self.height//2 + math.sin(rad) * 70
                pygame.draw.circle(screen, YELLOW, (int(px), int(py)), 5)

        # Block shield
        if self.blocking:
            shield_rect = pygame.Rect(self.x - 50, self.y - self.height - 10, 100, 120)
            shield_surf = pygame.Surface((100, 120), pygame.SRCALPHA)
            pygame.draw.ellipse(shield_surf, (100, 200, 255, 128), shield_surf.get_rect())
            screen.blit(shield_surf, shield_rect)

        # Particles
        for p in self.particles:
            pygame.draw.circle(screen, p['color'], (int(p['x']), int(p['y'])), 3)

        # Health bar
        bar_width = 100
        bar_height = 10
        health_pct = self.health / self.max_health
        bar_x = self.x - bar_width//2
        bar_y = self.y - self.height - 50

        pygame.draw.rect(screen, DARK_GRAY, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, GREEN if health_pct > 0.5 else RED, 
                        (bar_x, bar_y, bar_width * health_pct, bar_height))
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)

        # Special meter
        special_pct = self.special_meter / self.max_special
        pygame.draw.rect(screen, DARK_GRAY, (bar_x, bar_y + 15, bar_width, 6))
        pygame.draw.rect(screen, YELLOW, (bar_x, bar_y + 15, bar_width * special_pct, 6))

        # Name
        name_surf = font.render(self.char_info.name, True, WHITE)
        screen.blit(name_surf, (self.x - name_surf.get_width()//2, bar_y - 25))
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Shadow Circuit Fighters")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 72)
        self.small_font = pygame.font.Font(None, 24)

        self.state = GameState.MENU
        self.selected_chars = [None, None]
        self.current_selector = 0
        self.selection_index = [0, 0]  # Current selection for each player

        self.fighter1: Optional[Fighter] = None
        self.fighter2: Optional[Fighter] = None

        self.round_time = 99
        self.round_timer = 0

        self.camera_shake = 0
        self.slow_motion = 0

        # Menu animation
        self.menu_particles = []
        for _ in range(50):
            self.menu_particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'vx': random.uniform(-1, 1),
                'vy': random.uniform(-1, 1),
                'size': random.randint(2, 5)
            })

    def check_collisions(self):
        if not self.fighter1 or not self.fighter2:
            return

        # Check hitboxes
        h1 = self.fighter1.get_hitbox()
        h2 = self.fighter2.get_hitbox()
        r1 = self.fighter1.get_rect()
        r2 = self.fighter2.get_rect()

        # Fighter 1 hits Fighter 2
        if h1 and h1.colliderect(r2) and self.fighter2.hitstun <= 0:
            base_damage = 12
            if self.fighter1.state == FighterState.SPECIAL:
                base_damage = 25
                self.camera_shake = 20
                self.slow_motion = 30

            damage = int(base_damage * self.fighter1.damage_mult)
            self.fighter2.take_damage(damage, 8)
            self.fighter1.special_meter = min(100, self.fighter1.special_meter + 15)

            if self.fighter1.combo_timer > 0:
                self.fighter1.combo_count += 1
            else:
                self.fighter1.combo_count = 1
            self.fighter1.combo_timer = 60

            # Screen shake
            if not self.fighter2.blocking:
                self.camera_shake = 10

        # Fighter 2 hits Fighter 1
        if h2 and h2.colliderect(r1) and self.fighter1.hitstun <= 0:
            base_damage = 12
            if self.fighter2.state == FighterState.SPECIAL:
                base_damage = 25
                self.camera_shake = 20
                self.slow_motion = 30

            damage = int(base_damage * self.fighter2.damage_mult)
            self.fighter1.take_damage(damage, 8)
            self.fighter2.special_meter = min(100, self.fighter2.special_meter + 15)

            if self.fighter2.combo_timer > 0:
                self.fighter2.combo_count += 1
            else:
                self.fighter2.combo_count = 1
            self.fighter2.combo_timer = 60

            if not self.fighter1.blocking:
                self.camera_shake = 10

    def update(self):
        # Camera shake decay
        if self.camera_shake > 0:
            self.camera_shake -= 1

        # Slow motion
        if self.slow_motion > 0:
            self.slow_motion -= 1
            if self.slow_motion % 2 == 0:
                return

        if self.state == GameState.FIGHTING:
            self.round_timer += 1
            if self.round_timer >= 60:
                self.round_timer = 0
                self.round_time = max(0, self.round_time - 1)

            if self.fighter1:
                self.fighter1.update()
            if self.fighter2:
                self.fighter2.update()

            self.check_collisions()

            # Check victory
            if self.fighter1 and self.fighter2:
                if self.fighter1.health <= 0 or self.fighter2.health <= 0 or self.round_time <= 0:
                    self.state = GameState.VICTORY

        # Menu particles
        for p in self.menu_particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            if p['x'] < 0 or p['x'] > SCREEN_WIDTH:
                p['vx'] *= -1
            if p['y'] < 0 or p['y'] > SCREEN_HEIGHT:
                p['vy'] *= -1
def draw_menu(self):
        # Background
        self.screen.fill(DARK_GRAY)

        # Animated particles
        for p in self.menu_particles:
            alpha = int(128 + 127 * math.sin(pygame.time.get_ticks() / 1000 + p['x']))
            color = (alpha, alpha, alpha)
            pygame.draw.circle(self.screen, color, (int(p['x']), int(p['y'])), p['size'])

        # Title
        title = self.title_font.render("SHADOW CIRCUIT", True, YELLOW)
        subtitle = self.font.render("UNDERGROUND FIGHTING CHAMPIONSHIP", True, WHITE)

        # Glow effect
        glow = int(10 * math.sin(pygame.time.get_ticks() / 200))
        title_rect = title.get_rect(center=(SCREEN_WIDTH//2, 200))

        for i in range(3):
            offset = glow + i * 2
            pygame.draw.rect(self.screen, (255, 215, 0, 50), 
                           title_rect.inflate(offset*2, offset*2), border_radius=10)

        self.screen.blit(title, title_rect)
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH//2, 280)))

        # Menu options
        options = ["Press ENTER to Start", "Press I for Instructions"]
        for i, opt in enumerate(options):
            color = YELLOW if i == 0 else GRAY
            text = self.font.render(opt, True, color)
            y = 400 + i * 50
            self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH//2, y)))

        # Character preview
        y_offset = 500
        self.screen.blit(self.small_font.render("Available Fighters:", True, WHITE), 
                        (50, y_offset))

        for i, (key, char) in enumerate(CHARACTERS.items()):
            x = 50 + i * 300
            pygame.draw.rect(self.screen, char.color, (x, y_offset + 30, 40, 60))
            self.screen.blit(self.small_font.render(char.name, True, WHITE), (x, y_offset + 100))

    def draw_character_select(self):
        self.screen.fill(DARK_GRAY)

        # Title
        title = self.title_font.render("SELECT FIGHTER", True, YELLOW)
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 80)))

        # Draw character cards
        char_list = list(CHARACTERS.items())
        card_width = 250
        card_height = 400
        start_x = (SCREEN_WIDTH - len(char_list) * (card_width + 30)) // 2 + card_width//2

        for i, (key, char) in enumerate(char_list):
            x = start_x + i * (card_width + 30)
            y = 300

            # Card background
            is_selected = (self.selected_chars[0] == key or self.selected_chars[1] == key)
            is_current = (self.current_selector == 0 and self.selected_chars[0] is None and i == self.selection_index[0]) or \
                        (self.current_selector == 1 and self.selected_chars[0] is not None and self.selected_chars[1] is None and i == self.selection_index[1])

            if is_selected:
                color = GREEN if self.selected_chars[0] == key else RED
                border_width = 4
            elif is_current:
                color = YELLOW
                border_width = 3
            else:
                color = GRAY
                border_width = 2

            rect = pygame.Rect(x - card_width//2, y - card_height//2, card_width, card_height)
            pygame.draw.rect(self.screen, DARK_GRAY, rect)
            pygame.draw.rect(self.screen, color, rect, border_width)

            # Character color preview
            pygame.draw.rect(self.screen, char.color, (x - 40, y - 150, 80, 120))
            pygame.draw.rect(self.screen, BLACK, (x - 40, y - 150, 80, 120), 2)

            # Character info
            name_surf = self.font.render(char.name, True, WHITE)
            self.screen.blit(name_surf, name_surf.get_rect(center=(x, y + 20)))

            title_surf = self.small_font.render(char.title, True, YELLOW)
            self.screen.blit(title_surf, title_surf.get_rect(center=(x, y + 50)))

            # Stats
            stats_y = y + 80
            stats = [
                f"Speed: {'★' * int(char.speed/2)}",
                f"Health: {char.health}",
                f"Power: {'★' * int(char.damage_mult * 3)}"
            ]
            for j, stat in enumerate(stats):
                self.screen.blit(self.small_font.render(stat, True, WHITE), 
                               (x - card_width//2 + 20, stats_y + j * 25))

            # Selection indicators
            if self.selected_chars[0] == key:
                self.screen.blit(self.font.render("P1", True, GREEN), (x - 20, y - 180))
            if self.selected_chars[1] == key:
                self.screen.blit(self.font.render("P2", True, RED), (x + 20, y - 180))

        # Instructions
        if self.selected_chars[0] is None:
            inst = self.font.render("Player 1: Use A/D to select, SPACE to confirm", True, WHITE)
        elif self.selected_chars[1] is None:
            inst = self.font.render("Player 2: Use LEFT/RIGHT to select, ENTER to confirm", True, WHITE)
        else:
            inst = self.font.render("Press SPACE to fight!", True, YELLOW)

        self.screen.blit(inst, inst.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 100)))

        # Story preview
        if self.current_selector == 0 and self.selected_chars[0] is None:
            preview_key = char_list[self.selection_index[0]][0]
        elif self.selected_chars[0] is not None and self.selected_chars[1] is None:
            preview_key = char_list[self.selection_index[1]][0]
        else:
            preview_key = None

        if preview_key:
            char = CHARACTERS[preview_key]
            story = self.small_font.render(char.backstory[:80] + "...", True, GRAY)
            self.screen.blit(story, story.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 50)))
def draw_story(self):
        self.screen.fill(BLACK)

        if self.fighter1 and self.fighter2:
            # Display both character backstories
            fighters = [self.fighter1, self.fighter2]
            positions = [(SCREEN_WIDTH//4, SCREEN_HEIGHT//2), (3*SCREEN_WIDTH//4, SCREEN_HEIGHT//2)]
            colors = [BLUE, RED]

            for fighter, pos, color in zip(fighters, positions, colors):
                info = fighter.char_info

                # Character portrait area
                pygame.draw.rect(self.screen, color, (pos[0] - 150, pos[1] - 200, 300, 400), 2)

                # Name and title
                name = self.title_font.render(info.name, True, color)
                self.screen.blit(name, name.get_rect(center=(pos[0], pos[1] - 180)))

                title = self.font.render(info.title, True, YELLOW)
                self.screen.blit(title, title.get_rect(center=(pos[0], pos[1] - 140)))

                # Backstory (wrapped text)
                words = info.backstory.split()
                lines = []
                current_line = []
                for word in words:
                    current_line.append(word)
                    test = ' '.join(current_line)
                    if self.small_font.size(test)[0] > 280:
                        current_line.pop()
                        lines.append(' '.join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(' '.join(current_line))

                y_offset = pos[1] - 100
                for line in lines[:8]:  # Limit lines
                    surf = self.small_font.render(line, True, WHITE)
                    self.screen.blit(surf, surf.get_rect(center=(pos[0], y_offset)))
                    y_offset += 25

                # Motivation
                motive = self.small_font.render(f"Goal: {info.motivation}", True, GREEN)
                self.screen.blit(motive, motive.get_rect(center=(pos[0], pos[1] + 120)))

                # Special
                special = self.small_font.render(f"Special: {info.special_move}", True, YELLOW)
                self.screen.blit(special, special.get_rect(center=(pos[0], pos[1] + 150)))

        # Continue prompt
        prompt = self.font.render("Press SPACE to begin combat", True, YELLOW)
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 80)))
def draw_fighting(self):
        # Camera shake offset
        shake_x = random.randint(-self.camera_shake, self.camera_shake) if self.camera_shake > 0 else 0
        shake_y = random.randint(-self.camera_shake, self.camera_shake) if self.camera_shake > 0 else 0

        # Background
        self.screen.fill((40, 40, 50))

        # Arena floor
        floor_y = SCREEN_HEIGHT - 100
        pygame.draw.rect(self.screen, (60, 60, 70), (0, floor_y, SCREEN_WIDTH, 100))
        pygame.draw.line(self.screen, WHITE, (0, floor_y), (SCREEN_WIDTH, floor_y), 2)

        # Grid pattern on floor
        for i in range(0, SCREEN_WIDTH, 100):
            pygame.draw.line(self.screen, (80, 80, 90), (i, floor_y), (i - 200, SCREEN_HEIGHT), 1)

        # Draw fighters with shake
        if self.fighter1 and self.fighter2:
            # Save original positions
            f1_x, f1_y = self.fighter1.x, self.fighter1.y
            f2_x, f2_y = self.fighter2.x, self.fighter2.y

            # Apply shake
            self.fighter1.x += shake_x
            self.fighter1.y += shake_y
            self.fighter2.x += shake_x
            self.fighter2.y += shake_y

            self.fighter1.draw(self.screen, self.font)
            self.fighter2.draw(self.screen, self.font)

            # Restore positions
            self.fighter1.x, self.fighter1.y = f1_x, f1_y
            self.fighter2.x, self.fighter2.y = f2_x, f2_y

        # UI - Timer
        timer_text = self.title_font.render(str(self.round_time), True, WHITE)
        self.screen.blit(timer_text, timer_text.get_rect(center=(SCREEN_WIDTH//2, 50)))

        # UI - Combo displays
        if self.fighter1 and self.fighter1.combo_count > 1:
            combo = self.font.render(f"{self.fighter1.combo_count} HIT COMBO!", True, YELLOW)
            self.screen.blit(combo, (50, 150))

        if self.fighter2 and self.fighter2.combo_count > 1:
            combo = self.font.render(f"{self.fighter2.combo_count} HIT COMBO!", True, YELLOW)
            self.screen.blit(combo, (SCREEN_WIDTH - 250, 150))

        # Controls reminder
        controls = self.small_font.render("P1: WASD + G(Attack) + H(Special) | P2: Arrows + L(Attack) + K(Special)", True, GRAY)
        self.screen.blit(controls, controls.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 30)))

    def draw_victory(self):
        self.draw_fighting()

        # Darken screen
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))

        # Determine winner
        winner = None
        if self.fighter1 and self.fighter2:
            if self.fighter1.health > self.fighter2.health:
                winner = self.fighter1
                color = BLUE
            elif self.fighter2.health > self.fighter1.health:
                winner = self.fighter2
                color = RED
            else:
                text = self.title_font.render("DRAW!", True, WHITE)
                self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))

                restart = self.font.render("Press R to rematch, ESC for menu", True, YELLOW)
                self.screen.blit(restart, restart.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 100)))
                return

        if winner:
            text = self.title_font.render(f"{winner.char_info.name} WINS!", True, color)
            self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50)))

            # Victory quote
            quote = self.font.render(f'"{winner.char_info.motivation}"', True, WHITE)
            self.screen.blit(quote, quote.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50)))

        restart = self.font.render("Press R to rematch, ESC for menu", True, YELLOW)
        self.screen.blit(restart, restart.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 150)))
def draw(self):
        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.CHARACTER_SELECT:
            self.draw_character_select()
        elif self.state == GameState.STORY:
            self.draw_story()
        elif self.state == GameState.FIGHTING:
            self.draw_fighting()
        elif self.state == GameState.VICTORY:
            self.draw_victory()

        pygame.display.flip()

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                # Global
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.MENU:
                        return False
                    else:
                        self.state = GameState.MENU
                        self.selected_chars = [None, None]
                        self.current_selector = 0

                # Menu state
                if self.state == GameState.MENU:
                    if event.key == pygame.K_RETURN:
                        self.state = GameState.CHARACTER_SELECT
                    elif event.key == pygame.K_i:
                        pass  # Could show instructions

                # Character select
                elif self.state == GameState.CHARACTER_SELECT:
                    char_keys = list(CHARACTERS.keys())

                    if self.current_selector == 0:  # Player 1
                        if event.key == pygame.K_a:
                            self.selection_index[0] = (self.selection_index[0] - 1) % len(char_keys)
                        elif event.key == pygame.K_d:
                            self.selection_index[0] = (self.selection_index[0] + 1) % len(char_keys)
                        elif event.key == pygame.K_SPACE:
                            if self.selected_chars[0] is None:
                                self.selected_chars[0] = char_keys[self.selection_index[0]]
                                self.current_selector = 1
                            elif self.selected_chars[0] is not None and self.selected_chars[1] is not None:
                                # Start game
                                self.fighter1 = Fighter(self.selected_chars[0], 300, SCREEN_HEIGHT - 100, True)
                                self.fighter2 = Fighter(self.selected_chars[1], SCREEN_WIDTH - 300, SCREEN_HEIGHT - 100, False)
                                self.state = GameState.STORY

                    else:  # Player 2
                        if event.key == pygame.K_LEFT:
                            self.selection_index[1] = (self.selection_index[1] - 1) % len(char_keys)
                        elif event.key == pygame.K_RIGHT:
                            self.selection_index[1] = (self.selection_index[1] + 1) % len(char_keys)
                        elif event.key == pygame.K_RETURN:
                            if self.selected_chars[1] is None:
                                selected_key = char_keys[self.selection_index[1]]
                                if selected_key != self.selected_chars[0]:  # Can't select same character
                                    self.selected_chars[1] = selected_key

                # Story screen
                elif self.state == GameState.STORY:
                    if event.key == pygame.K_SPACE:
                        self.state = GameState.FIGHTING
                        self.round_time = 99
                        self.round_timer = 0

                # Fighting controls
                elif self.state == GameState.FIGHTING:
                    if event.key == pygame.K_g and self.fighter1:
                        self.fighter1.attack()
                    elif event.key == pygame.K_h and self.fighter1:
                        self.fighter1.use_special()
                    elif event.key == pygame.K_l and self.fighter2:
                        self.fighter2.attack()
                    elif event.key == pygame.K_k and self.fighter2:
                        self.fighter2.use_special()

                # Victory
                elif self.state == GameState.VICTORY:
                    if event.key == pygame.K_r:
                        # Rematch
                        self.fighter1 = Fighter(self.selected_chars[0], 300, SCREEN_HEIGHT - 100, True)
                        self.fighter2 = Fighter(self.selected_chars[1], SCREEN_WIDTH - 300, SCREEN_HEIGHT - 100, False)
                        self.state = GameState.FIGHTING
                        self.round_time = 99
                        self.round_timer = 0

        # Continuous input (movement)
        keys = pygame.key.get_pressed()

        if self.state == GameState.FIGHTING:
            # Player 1
            if self.fighter1 and self.fighter1.hitstun <= 0:
                if keys[pygame.K_w]:
                    self.fighter1.jump()

                move = 0
                if keys[pygame.K_a]:
                    move = -1
                elif keys[pygame.K_d]:
                    move = 1

                self.fighter1.move(move)
                self.fighter1.block(keys[pygame.K_s])

            # Player 2
            if self.fighter2 and self.fighter2.hitstun <= 0:
                if keys[pygame.K_UP]:
                    self.fighter2.jump()

                move = 0
                if keys[pygame.K_LEFT]:
                    move = -1
                elif keys[pygame.K_RIGHT]:
                    move = 1

                self.fighter2.move(move)
                self.fighter2.block(keys[pygame.K_DOWN])

        return True

    def run(self):
        running = True
        while running:
            running = self.handle_input()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()

# Main entry point
if __name__ == "__main__":
    game = Game()
    game.run()