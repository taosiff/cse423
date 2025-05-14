import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import os
from PIL import Image

# Constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FOV = 60
NEAR_CLIP = 0.1
FAR_CLIP = 1000.0

# Game Constants
PLAYER_SPEED = 0.15
LASER_SPEED = 1.5
ENEMY_SPAWN_RATE = 0.01
MAX_ENEMIES = 10
SCORE_PER_HIT = 100
LIVES = 3
GRAVITY = 0.0005
FLOAT_FORCE = 0.001
POWERUP_TYPES = ['health', 'speed', 'shield', 'multishot']
POWERUP_DURATION = 10.0  # seconds
WAVE_DURATION = 30.0  # seconds
COMBO_TIMEOUT = 2.0  # seconds
SUPER_POWER_COOLDOWN = 10.0  # seconds
SUPER_POWER_DURATION = 2.0   # seconds

# Weapon Constants
WEAPON_TYPES = {
    'laser': {'color': (0, 1, 1), 'damage': 1, 'speed': 1.5, 'cooldown': 0.2, 'spread': 0.05},
    'plasma': {'color': (1, 0, 1), 'damage': 2, 'speed': 1.0, 'cooldown': 0.4, 'spread': 0.1},
    'missile': {'color': (1, 0.5, 0), 'damage': 3, 'speed': 0.8, 'cooldown': 0.8, 'spread': 0.02},
    'railgun': {'color': (0, 1, 0), 'damage': 4, 'speed': 2.0, 'cooldown': 1.0, 'spread': 0.0}
}

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)

def load_texture(filename):
    try:
        image = Image.open(filename)
        image_data = image.tobytes()
        width, height = image.size
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, image_data)
        return texture_id
    except Exception as e:
        print(f"Error loading texture {filename}: {e}")
        return None

class CelestialBody:
    def __init__(self, radius, distance, orbit_period, rotation_period, color, name, texture_file=None):
        self.radius = radius
        self.distance = distance
        self.orbit_period = orbit_period
        self.rotation_period = rotation_period
        self.color = color
        self.name = name
        self.angle = random.uniform(0, 360)
        self.rotation_angle = 0
        # Handle special case for the Sun (no orbit)
        self.orbit_speed = 0 if orbit_period == 0 else 360 / orbit_period
        self.rotation_speed = 360 / rotation_period
        self.texture = None
        if texture_file:
            self.texture = load_texture(texture_file)
        self.info = {
            "Diameter": f"{radius * 2:.1f} units",
            "Distance": f"{distance:.1f} units",
            "Orbit Period": "N/A" if orbit_period == 0 else f"{orbit_period:.1f} days",
            "Rotation Period": f"{abs(rotation_period):.1f} days"
        }

    def update(self, time_delta):
        # Only update orbit for non-sun bodies
        if self.orbit_period != 0:
            self.angle += self.orbit_speed * time_delta
            if self.angle >= 360:
                self.angle -= 360
        # Update rotation for all bodies
        self.rotation_angle += self.rotation_speed * time_delta
        if self.rotation_angle >= 360:
            self.rotation_angle -= 360

    def draw(self):
        glPushMatrix()
        
        # Only draw orbit for non-sun bodies
        if self.orbit_period != 0:
            glColor3f(0.3, 0.3, 0.3)
            glBegin(GL_LINE_LOOP)
            for i in range(360):
                angle = math.radians(i)
                x = math.cos(angle) * self.distance
                y = math.sin(angle) * self.distance
                glVertex3f(x, y, 0)
            glEnd()

            # Position
            glRotatef(self.angle, 0, 0, 1)
            glTranslatef(self.distance, 0, 0)
        
        # Rotation
        glRotatef(self.rotation_angle, 0, 0, 1)
        
        # Draw the celestial body
        if self.texture:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.texture)
        else:
            glColor3f(*self.color)
            
        quad = gluNewQuadric()
        if self.texture:
            gluQuadricTexture(quad, GL_TRUE)
        gluSphere(quad, self.radius, 32, 32)
        gluDeleteQuadric(quad)
        
        if self.texture:
            glDisable(GL_TEXTURE_2D)
        
        glPopMatrix()

class Projectile:
    def __init__(self, start_pos, target_pos, weapon_type):
        self.position = list(start_pos)
        self.start_pos = list(start_pos)
        self.target_pos = list(target_pos)
        self.weapon_type = weapon_type
        self.stats = WEAPON_TYPES[weapon_type]
        self.speed = self.stats['speed'] * LASER_SPEED
        self.lifetime = 1.0
        self.active = True
        self.radius = 2.0
        self.length = 5.0
        
        # Calculate direction
        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dz = target_pos[2] - start_pos[2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        self.direction = [dx/length, dy/length, dz/length] if length > 0 else [0, 0, 0]

    def update(self, time_delta):
        self.position[0] += self.direction[0] * self.speed
        self.position[1] += self.direction[1] * self.speed
        self.position[2] += self.direction[2] * self.speed
        self.lifetime -= time_delta
        if self.lifetime <= 0:
            self.active = False

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.position)
        
        # Draw projectile based on weapon type
        glColor3f(*self.stats['color'])
        if self.weapon_type == 'laser':
            glLineWidth(5.0)
            glBegin(GL_LINES)
            glVertex3f(0, 0, 0)
            glVertex3f(-self.direction[0] * self.length, -self.direction[1] * self.length, -self.direction[2] * self.length)
            glEnd()
        elif self.weapon_type == 'plasma':
            quad = gluNewQuadric()
            gluSphere(quad, 0.5, 16, 16)
            gluDeleteQuadric(quad)
        elif self.weapon_type == 'missile':
            glLineWidth(3.0)
            glBegin(GL_LINES)
            glVertex3f(0, 0, 0)
            glVertex3f(-self.direction[0] * self.length, -self.direction[1] * self.length, -self.direction[2] * self.length)
            glEnd()
            # Draw missile body
            quad = gluNewQuadric()
            gluSphere(quad, 0.3, 8, 8)
            gluDeleteQuadric(quad)
        elif self.weapon_type == 'railgun':
            glLineWidth(8.0)
            glBegin(GL_LINES)
            glVertex3f(0, 0, 0)
            glVertex3f(-self.direction[0] * self.length * 2, -self.direction[1] * self.length * 2, -self.direction[2] * self.length * 2)
            glEnd()
        
        glPopMatrix()

class Enemy:
    def __init__(self, position):
        self.position = list(position)
        self.radius = 1.0  # Increased enemy size
        self.speed = random.uniform(0.1, 0.3)
        self.angle = random.uniform(0, 360)
        self.active = True
        self.health = 2  # Enemies have 2 health
        self.hit_cooldown = 0  # Cooldown between hits
        self.type = random.choice(['normal', 'fast', 'tank'])  # New enemy types
        if self.type == 'fast':
            self.speed *= 1.5
            self.health = 1
        elif self.type == 'tank':
            self.speed *= 0.7
            self.health = 4
            self.radius = 1.5

    def update(self, time_delta, player_position):
        # Update hit cooldown
        if self.hit_cooldown > 0:
            self.hit_cooldown -= time_delta

        # Move towards player
        dx = player_position[0] - self.position[0]
        dy = player_position[1] - self.position[1]
        dz = player_position[2] - self.position[2]
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        if distance > 0:
            self.position[0] += (dx/distance) * self.speed
            self.position[1] += (dy/distance) * self.speed
            self.position[2] += (dz/distance) * self.speed

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.position)
        # Flash red when hit
        if self.hit_cooldown > 0:
            glColor3f(1, 0.5, 0.5)  # Light red when hit
        else:
            if self.type == 'fast':
                glColor3f(1, 0, 1)  # Purple for fast enemies
            elif self.type == 'tank':
                glColor3f(0.5, 0.5, 1)  # Blue for tank enemies
            else:
                glColor3f(1, 0, 0)  # Normal red
        quad = gluNewQuadric()
        gluSphere(quad, self.radius, 16, 16)
        gluDeleteQuadric(quad)
        glPopMatrix()

class Bomb:
    def __init__(self, start_pos, target_pos):
        self.position = list(start_pos)
        self.start_pos = list(start_pos)
        self.target_pos = list(target_pos)
        self.speed = LASER_SPEED * 0.5  # Slower than laser
        self.lifetime = 2.0  # Longer lifetime
        self.active = True
        self.exploded = False
        self.explosion_radius = 5.0
        self.explosion_time = 0.5  # Time to stay exploded
        
        # Calculate direction
        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dz = target_pos[2] - start_pos[2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        self.direction = [dx/length, dy/length, dz/length] if length > 0 else [0, 0, 0]

    def update(self, time_delta):
        if not self.exploded:
            self.position[0] += self.direction[0] * self.speed
            self.position[1] += self.direction[1] * self.speed
            self.position[2] += self.direction[2] * self.speed
            self.lifetime -= time_delta
            if self.lifetime <= 0:
                self.exploded = True
        else:
            self.explosion_time -= time_delta
            if self.explosion_time <= 0:
                self.active = False

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.position)
        
        if not self.exploded:
            # Draw bomb
            glColor3f(0.5, 0.5, 0.5)  # Gray bomb
            quad = gluNewQuadric()
            gluSphere(quad, 0.5, 16, 16)
            gluDeleteQuadric(quad)
        else:
            # Draw explosion
            glColor4f(1, 0.5, 0, 0.7)  # Orange explosion with transparency
            quad = gluNewQuadric()
            gluSphere(quad, self.explosion_radius * (1 - self.explosion_time/0.5), 32, 32)
            gluDeleteQuadric(quad)
        
        glPopMatrix()

class PowerUp:
    def __init__(self, position):
        self.position = list(position)
        self.radius = 0.8
        self.type = random.choice(POWERUP_TYPES)
        self.rotation = 0
        self.colors = {
            'health': (1, 0, 0),    # Red
            'speed': (0, 1, 0),     # Green
            'shield': (0, 0, 1),    # Blue
            'multishot': (1, 1, 0)  # Yellow
        }

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.position)
        glRotatef(self.rotation, 0, 0, 1)
        glColor3f(*self.colors[self.type])
        quad = gluNewQuadric()
        gluSphere(quad, self.radius, 16, 16)
        gluDeleteQuadric(quad)
        glPopMatrix()

class Particle:
    def __init__(self, position, velocity, color, lifetime):
        self.position = list(position)
        self.velocity = list(velocity)
        self.color = color
        self.lifetime = lifetime
        self.alpha = 1.0

    def update(self, time_delta):
        self.position[0] += self.velocity[0] * time_delta
        self.position[1] += self.velocity[1] * time_delta
        self.position[2] += self.velocity[2] * time_delta
        self.lifetime -= time_delta
        self.alpha = self.lifetime / 0.5  # Fade out over 0.5 seconds

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.position)
        glColor4f(*self.color, self.alpha)
        quad = gluNewQuadric()
        gluSphere(quad, 0.2, 8, 8)
        gluDeleteQuadric(quad)
        glPopMatrix()

class Player:
    def __init__(self):
        self.position = [0, 0, 20]
        self.velocity = [0, 0, 0]
        self.angle = 0
        self.lives = 3
        self.score = 0
        self.lasers = []
        self.bombs = []
        self.last_shot_time = 0
        self.last_bomb_time = 0
        self.shoot_delay = 0.2
        self.bomb_delay = 1.5
        self.is_floating = True
        self.is_dead = False
        self.respawn_time = 0
        self.invincible_time = 2.0
        self.cheat_mode = False
        self.auto_fire = False
        self.last_auto_fire_time = 0
        self.auto_fire_delay = 0.3
        self.aim_mode = 0  # 0: mouse, 1: keyboard, 2: auto-aim
        self.powerups = {
            'speed': 0,
            'shield': 0,
            'multishot': 0
        }
        self.shield_active = False
        self.combo = 0
        self.last_kill_time = 0
        self.particles = []
        self.current_weapon = 'laser'
        self.weapons = ['laser', 'plasma', 'missile', 'railgun']
        self.projectiles = []  # Replace lasers with projectiles
        self.super_power_ready = True
        self.super_power_cooldown = 0
        self.super_power_active = False
        self.super_power_timer = 0

    def reset(self):
        self.position = [0, 0, 20]
        self.velocity = [0, 0, 0]
        self.lives = 3
        self.score = 0
        self.lasers = []
        self.bombs = []
        self.is_dead = False
        self.respawn_time = 0
        self.cheat_mode = False
        self.auto_fire = False

    def get_aim_direction(self, mouse_pos, enemies):
        if self.aim_mode == 0:  # Mouse aiming
            # Get mouse position relative to center of screen
            mouse_x = mouse_pos[0] - WINDOW_WIDTH/2
            mouse_y = mouse_pos[1] - WINDOW_HEIGHT/2
            length = math.sqrt(mouse_x*mouse_x + mouse_y*mouse_y)
            if length > 0:
                return [mouse_x/length, mouse_y/length, 0]
        
        elif self.aim_mode == 1:  # Keyboard aiming
            keys = pygame.key.get_pressed()
            dx = dy = 0
            if keys[pygame.K_LEFT]:
                dx -= 1
            if keys[pygame.K_RIGHT]:
                dx += 1
            if keys[pygame.K_UP]:
                dy -= 1
            if keys[pygame.K_DOWN]:
                dy += 1
            
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                return [dx/length, dy/length, 0]
        
        elif self.aim_mode == 2 and enemies:  # Auto-aim
            # Find closest enemy
            closest_enemy = min(enemies, key=lambda e: (
                (e.position[0] - self.position[0])**2 +
                (e.position[1] - self.position[1])**2 +
                (e.position[2] - self.position[2])**2
            ))
            
            # Calculate direction to closest enemy
            dx = closest_enemy.position[0] - self.position[0]
            dy = closest_enemy.position[1] - self.position[1]
            dz = closest_enemy.position[2] - self.position[2]
            length = math.sqrt(dx*dx + dy*dy + dz*dz)
            if length > 0:
                return [dx/length, dy/length, dz/length]
        
        return [0, 0, 0]  # Default direction

    def update(self, time_delta, keys, mouse_pos, mouse_buttons, enemies):
        if self.is_dead:
            return

        # Update super power cooldown
        if not self.super_power_ready:
            self.super_power_cooldown -= time_delta
            if self.super_power_cooldown <= 0:
                self.super_power_ready = True

        # Update super power duration
        if self.super_power_active:
            self.super_power_timer -= time_delta
            if self.super_power_timer <= 0:
                self.super_power_active = False

        # Activate super power with F key
        if keys[pygame.K_f] and self.super_power_ready:
            self.super_power_ready = False
            self.super_power_cooldown = SUPER_POWER_COOLDOWN
            self.super_power_active = True
            self.super_power_timer = SUPER_POWER_DURATION
            # Create a massive explosion effect
            for _ in range(100):
                angle = random.uniform(0, 360)
                speed = random.uniform(5, 15)
                velocity = [
                    math.cos(math.radians(angle)) * speed,
                    math.sin(math.radians(angle)) * speed,
                    random.uniform(-5, 5)
                ]
                self.particles.append(Particle(
                    self.position,
                    velocity,
                    (1, 0.8, 0),  # Orange color
                    1.0
                ))

        # Toggle cheat mode with F1
        if keys[pygame.K_F1] and not self.cheat_mode:
            self.cheat_mode = True
            self.lives = 999
            self.auto_fire = True
            self.shield_active = True
            self.powerups['shield'] = float('inf')  # Infinite shield
            self.powerups['speed'] = float('inf')   # Infinite speed
            self.powerups['multishot'] = float('inf')  # Infinite multishot
        elif keys[pygame.K_F1] and self.cheat_mode:
            self.cheat_mode = False
            self.lives = 3
            self.auto_fire = False
            self.shield_active = False
            self.powerups['shield'] = 0
            self.powerups['speed'] = 0
            self.powerups['multishot'] = 0

        # Toggle aim mode with F2
        if keys[pygame.K_F2]:
            self.aim_mode = (self.aim_mode + 1) % 3

        # Apply gravity and floating force
        if self.is_floating:
            self.velocity[2] -= GRAVITY
            if self.position[2] < 5:
                self.velocity[2] += FLOAT_FORCE
            if self.position[2] > 30:
                self.velocity[2] -= FLOAT_FORCE

        # Update position based on velocity
        self.position[0] += self.velocity[0]
        self.position[1] += self.velocity[1]
        self.position[2] += self.velocity[2]

        # Movement
        if keys[pygame.K_a]:
            self.velocity[0] = -PLAYER_SPEED
        elif keys[pygame.K_d]:
            self.velocity[0] = PLAYER_SPEED
        else:
            self.velocity[0] *= 0.9

        if keys[pygame.K_w]:
            self.velocity[1] = PLAYER_SPEED
        elif keys[pygame.K_s]:
            self.velocity[1] = -PLAYER_SPEED
        else:
            self.velocity[1] *= 0.9

        # Up/Down movement
        if keys[pygame.K_SPACE]:
            self.velocity[2] = PLAYER_SPEED
        elif keys[pygame.K_LSHIFT]:
            self.velocity[2] = -PLAYER_SPEED

        # Weapon switching with number keys
        if keys[pygame.K_1]:
            self.current_weapon = 'laser'
        elif keys[pygame.K_2]:
            self.current_weapon = 'plasma'
        elif keys[pygame.K_3]:
            self.current_weapon = 'missile'
        elif keys[pygame.K_4]:
            self.current_weapon = 'railgun'

        current_time = pygame.time.get_ticks() / 1000.0

        # Update invincibility time
        if self.respawn_time > 0:
            self.respawn_time -= time_delta

        # Shooting logic
        should_shoot = mouse_buttons[0] or (self.auto_fire and current_time - self.last_auto_fire_time > self.auto_fire_delay)
        
        if should_shoot:
            weapon_stats = WEAPON_TYPES[self.current_weapon]
            if current_time - self.last_shot_time > weapon_stats['cooldown']:
                # Get aim direction based on current mode
                dir_x, dir_y, dir_z = self.get_aim_direction(mouse_pos, enemies)
                
                if dir_x != 0 or dir_y != 0 or dir_z != 0:
                    # Calculate target position
                    target_x = self.position[0] + dir_x * 100
                    target_y = self.position[1] + dir_y * 100
                    target_z = self.position[2] + dir_z * 100
                    
                    # Create projectiles in a spread pattern
                    spread = weapon_stats['spread']
                    num_projectiles = 3 if self.current_weapon != 'railgun' else 1
                    
                    for i in range(num_projectiles):
                        angle = (i - (num_projectiles-1)/2) * spread
                        cos_angle = math.cos(angle)
                        sin_angle = math.sin(angle)
                        
                        # Rotate direction vector
                        rotated_x = dir_x * cos_angle - dir_y * sin_angle
                        rotated_y = dir_x * sin_angle + dir_y * cos_angle
                        
                        spread_target_x = self.position[0] + rotated_x * 100
                        spread_target_y = self.position[1] + rotated_y * 100
                        spread_target_z = self.position[2] + dir_z * 100
                        
                        self.projectiles.append(Projectile(
                            self.position,
                            [spread_target_x, spread_target_y, spread_target_z],
                            self.current_weapon
                        ))
                    
                    self.last_shot_time = current_time
                    if self.auto_fire:
                        self.last_auto_fire_time = current_time

        # Update projectiles
        for projectile in self.projectiles[:]:
            projectile.update(time_delta)
            if not projectile.active:
                self.projectiles.remove(projectile)

        # Update powerups
        for powerup in self.powerups:
            if self.powerups[powerup] > 0:
                self.powerups[powerup] -= time_delta
                if powerup == 'shield' and self.powerups[powerup] <= 0:
                    self.shield_active = False

        # Update combo
        if pygame.time.get_ticks() / 1000.0 - self.last_kill_time > COMBO_TIMEOUT:
            self.combo = 0

        # Update particles
        for particle in self.particles[:]:
            particle.update(time_delta)
            if particle.lifetime <= 0:
                self.particles.remove(particle)

    def take_damage(self):
        if self.respawn_time <= 0 and not self.cheat_mode:  # Only take damage if not in cheat mode
            self.lives -= 1
            if self.lives <= 0:
                self.is_dead = True
            else:
                self.respawn_time = self.invincible_time
                self.position = [0, 0, 20]  # Reset position

    def draw(self):
        if self.is_dead:
            return

        glPushMatrix()
        glTranslatef(*self.position)
        
        # Flash when invincible
        if self.respawn_time > 0:
            if int(self.respawn_time * 10) % 2 == 0:
                glColor3f(1, 1, 1)
            else:
                glColor3f(0, 1, 0)
        else:
            glColor3f(0, 1, 0)
        
        # Draw player
        quad = gluNewQuadric()
        gluSphere(quad, 0.5, 16, 16)
        gluDeleteQuadric(quad)
        
        # Head
        glPushMatrix()
        glTranslatef(0, 0, 0.7)
        quad = gluNewQuadric()
        gluSphere(quad, 0.3, 16, 16)
        gluDeleteQuadric(quad)
        glPopMatrix()
        
        # Arms
        glPushMatrix()
        glTranslatef(0.7, 0, 0.3)
        glRotatef(90, 0, 1, 0)
        quad = gluNewQuadric()
        gluCylinder(quad, 0.1, 0.1, 0.6, 8, 1)
        gluDeleteQuadric(quad)
        glPopMatrix()
        
        glPushMatrix()
        glTranslatef(-0.7, 0, 0.3)
        glRotatef(90, 0, 1, 0)
        quad = gluNewQuadric()
        gluCylinder(quad, 0.1, 0.1, 0.6, 8, 1)
        gluDeleteQuadric(quad)
        glPopMatrix()
        
        glPopMatrix()

        # Draw projectiles
        for projectile in self.projectiles:
            projectile.draw()

        # Draw shield if active
        if self.shield_active:
            glPushMatrix()
            glTranslatef(*self.position)
            glColor4f(0, 0.5, 1, 0.3)
            quad = gluNewQuadric()
            gluSphere(quad, 1.2, 32, 32)
            gluDeleteQuadric(quad)
            glPopMatrix()

        # Draw particles
        for particle in self.particles:
            particle.draw()

        # Draw current weapon indicator
        glColor3f(1, 1, 1)
        weapon_stats = WEAPON_TYPES[self.current_weapon]
        print(f"\nCurrent Weapon: {self.current_weapon.upper()} (Press 1-4 to switch)")
        print(f"1: Laser | 2: Plasma | 3: Missile | 4: Railgun")

        # Draw super power effect when active
        if self.super_power_active:
            glPushMatrix()
            glTranslatef(*self.position)
            # Draw expanding sphere
            glColor4f(1, 0.8, 0, 0.3)  # Orange with transparency
            quad = gluNewQuadric()
            radius = 5 + (SUPER_POWER_DURATION - self.super_power_timer) * 10
            gluSphere(quad, radius, 32, 32)
            gluDeleteQuadric(quad)
            glPopMatrix()

        # Draw super power status
        if not self.super_power_ready:
            glColor3f(0.7, 0.7, 0.7)  # Gray
            print(f"\nSuper Power Cooldown: {int(self.super_power_cooldown)}s")
        else:
            glColor3f(1, 0.8, 0)  # Orange
            print("\nSUPER POWER READY! (Press F)")

# --- BossEnemy class ---
class BossEnemy(Enemy):
    def __init__(self, position):
        super().__init__(position)
        self.radius = 3.0
        self.health = 10  # Reduced from 20 to 10
        self.speed = 0.12
        self.color = (1, 0.5, 0)  # Orange
        self.hit_cooldown = 0

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.position)
        # Flash orange/yellow when hit
        if self.hit_cooldown > 0:
            glColor3f(1, 1, 0.5)
        else:
            glColor3f(*self.color)
        quad = gluNewQuadric()
        gluSphere(quad, self.radius, 32, 32)
        gluDeleteQuadric(quad)
        glPopMatrix()

class SolarSystem:
    def __init__(self):
        self.bodies = []
        self.camera_distance = 50
        self.camera_angle = 0
        self.camera_height = 30
        self.time_scale = 1.0
        self.selected_body = None
        self.player = Player()
        self.enemies = []
        self.boss = None
        self.boss_spawn_score = 200  # Lowered for testing
        self.next_boss_score = self.boss_spawn_score
        self.game_over = False
        self.powerups = []
        self.wave = 1
        self.wave_timer = WAVE_DURATION
        self.enemies_killed = 0
        self.particles = []
        self.initialize_bodies()
        self.setup_lighting()

    def setup_lighting(self):
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # Set up light position (sun position)
        light_position = [0, 0, 0, 1]
        glLightfv(GL_LIGHT0, GL_POSITION, light_position)
        
        # Set up light properties
        ambient_light = [0.2, 0.2, 0.2, 1.0]
        diffuse_light = [1.0, 1.0, 1.0, 1.0]
        glLightfv(GL_LIGHT0, GL_AMBIENT, ambient_light)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, diffuse_light)

    def initialize_bodies(self):
        # Sun (special case - no orbit)
        self.bodies.append(CelestialBody(5, 0, 0, 27, (1, 0.7, 0), "Sun"))
        
        # Mercury
        self.bodies.append(CelestialBody(0.4, 10, 88, 58.6, (0.7, 0.7, 0.7), "Mercury"))
        
        # Venus
        self.bodies.append(CelestialBody(0.9, 15, 224.7, -243, (0.9, 0.7, 0.5), "Venus"))
        
        # Earth
        self.bodies.append(CelestialBody(1, 20, 365.25, 1, (0, 0.5, 1), "Earth"))
        
        # Mars
        self.bodies.append(CelestialBody(0.5, 25, 687, 1.03, (0.8, 0.3, 0.2), "Mars"))
        
        # Jupiter
        self.bodies.append(CelestialBody(2.5, 35, 4333, 0.41, (0.8, 0.6, 0.4), "Jupiter"))
        
        # Saturn
        self.bodies.append(CelestialBody(2, 45, 10759, 0.45, (0.9, 0.8, 0.5), "Saturn"))

    def spawn_powerup(self):
        if random.random() < 0.1:  # 10% chance to spawn powerup
            angle = random.uniform(0, 360)
            distance = random.uniform(10, 30)
            x = self.player.position[0] + math.cos(math.radians(angle)) * distance
            y = self.player.position[1] + math.sin(math.radians(angle)) * distance
            z = random.uniform(5, 25)
            self.powerups.append(PowerUp([x, y, z]))

    def create_explosion(self, position, color=(1, 0.5, 0)):
        for _ in range(20):
            angle = random.uniform(0, 360)
            speed = random.uniform(0.5, 2.0)
            velocity = [
                math.cos(math.radians(angle)) * speed,
                math.sin(math.radians(angle)) * speed,
                random.uniform(-1, 1) * speed
            ]
            self.particles.append(Particle(position, velocity, color, 0.5))

    def update(self, time_delta):
        if self.game_over:
            return

        # Update wave system
        self.wave_timer -= time_delta
        if self.wave_timer <= 0:
            self.wave += 1
            self.wave_timer = WAVE_DURATION
            # Increase difficulty
            global ENEMY_SPAWN_RATE, MAX_ENEMIES
            ENEMY_SPAWN_RATE = min(0.05, ENEMY_SPAWN_RATE + 0.005)
            MAX_ENEMIES = min(20, MAX_ENEMIES + 2)

        # Update powerups
        for powerup in self.powerups[:]:
            # Check collision with player
            dx = powerup.position[0] - self.player.position[0]
            dy = powerup.position[1] - self.player.position[1]
            dz = powerup.position[2] - self.player.position[2]
            distance = math.sqrt(dx*dx + dy*dy + dz*dz)
            if distance < powerup.radius + 0.5:
                if powerup.type == 'health':
                    self.player.lives = min(10, self.player.lives + 1)
                elif powerup.type == 'speed':
                    self.player.powerups['speed'] = POWERUP_DURATION
                elif powerup.type == 'shield':
                    self.player.powerups['shield'] = POWERUP_DURATION
                    self.player.shield_active = True
                elif powerup.type == 'multishot':
                    self.player.powerups['multishot'] = POWERUP_DURATION
                self.powerups.remove(powerup)
                self.create_explosion(powerup.position, powerup.colors[powerup.type])

        # Update particles
        for particle in self.particles[:]:
            particle.update(time_delta)
            if particle.lifetime <= 0:
                self.particles.remove(particle)

        # Update celestial bodies
        for body in self.bodies:
            body.update(time_delta * self.time_scale)

        # Update player
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()
        self.player.update(time_delta, keys, mouse_pos, mouse_buttons, self.enemies + ([self.boss] if self.boss else []))

        # Check for restart
        if keys[pygame.K_r] and self.game_over:
            self.restart_game()
            return  # Skip the rest of the update

        # Spawn enemies
        if len(self.enemies) < MAX_ENEMIES and random.random() < ENEMY_SPAWN_RATE:
            angle = random.uniform(0, 360)
            distance = random.uniform(20, 40)
            x = math.cos(math.radians(angle)) * distance
            y = math.sin(math.radians(angle)) * distance
            z = random.uniform(5, 25)
            self.enemies.append(Enemy([x, y, z]))

        # --- Boss spawn logic ---
        if self.player.score >= self.next_boss_score and self.boss is None:
            # Spawn boss at a random position far from player
            angle = random.uniform(0, 360)
            distance = 45
            x = self.player.position[0] + math.cos(math.radians(angle)) * distance
            y = self.player.position[1] + math.sin(math.radians(angle)) * distance
            z = 20
            self.boss = BossEnemy([x, y, z])
            self.next_boss_score += self.boss_spawn_score

        # Update enemies
        for enemy in self.enemies[:]:
            enemy.update(time_delta, self.player.position)
            # Check collision with player
            if not self.player.is_dead and self.player.respawn_time <= 0:
                dx = enemy.position[0] - self.player.position[0]
                dy = enemy.position[1] - self.player.position[1]
                dz = enemy.position[2] - self.player.position[2]
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                if distance < enemy.radius + 0.5:
                    if not self.player.cheat_mode:
                        self.player.take_damage()
                    self.enemies.remove(enemy)
                    if self.player.is_dead:
                        self.game_over = True

        # --- Boss update and collision ---
        if self.boss:
            self.boss.update(time_delta, self.player.position)
            # Boss collision with player
            dx = self.boss.position[0] - self.player.position[0]
            dy = self.boss.position[1] - self.player.position[1]
            dz = self.boss.position[2] - self.player.position[2]
            distance = math.sqrt(dx*dx + dy*dy + dz*dz)
            if distance < self.boss.radius + 0.5:
                if not self.player.cheat_mode:
                    self.player.take_damage()
                if self.player.is_dead:
                    self.game_over = True

        # Check projectile collisions
        for projectile in self.player.projectiles[:]:
            for enemy in self.enemies[:]:
                if enemy.hit_cooldown <= 0:
                    dx = enemy.position[0] - projectile.position[0]
                    dy = enemy.position[1] - projectile.position[1]
                    dz = enemy.position[2] - projectile.position[2]
                    cross_x = dy * projectile.direction[2] - dz * projectile.direction[1]
                    cross_y = dz * projectile.direction[0] - dx * projectile.direction[2]
                    cross_z = dx * projectile.direction[1] - dy * projectile.direction[0]
                    perpendicular_distance = math.sqrt(cross_x*cross_x + cross_y*cross_y + cross_z*cross_z)
                    dot_product = dx * projectile.direction[0] + dy * projectile.direction[1] + dz * projectile.direction[2]
                    if perpendicular_distance < enemy.radius + projectile.radius and dot_product > 0 and dot_product < projectile.length:
                        enemy.health -= projectile.stats['damage']
                        enemy.hit_cooldown = 0.2
                        if enemy.health <= 0:
                            self.player.score += SCORE_PER_HIT
                            self.enemies.remove(enemy)
                        projectile.active = False
                        break
            # --- Boss projectile collision ---
            if self.boss and self.boss.hit_cooldown <= 0:
                dx = self.boss.position[0] - projectile.position[0]
                dy = self.boss.position[1] - projectile.position[1]
                dz = self.boss.position[2] - projectile.position[2]
                cross_x = dy * projectile.direction[2] - dz * projectile.direction[1]
                cross_y = dz * projectile.direction[0] - dx * projectile.direction[2]
                cross_z = dx * projectile.direction[1] - dy * projectile.direction[0]
                perpendicular_distance = math.sqrt(cross_x*cross_x + cross_y*cross_y + cross_z*cross_z)
                dot_product = dx * projectile.direction[0] + dy * projectile.direction[1] + dz * projectile.direction[2]
                if perpendicular_distance < self.boss.radius + projectile.radius and dot_product > 0 and dot_product < projectile.length:
                    self.boss.health -= projectile.stats['damage']
                    self.boss.hit_cooldown = 0.2
                    if self.boss.health <= 0:
                        self.player.score += 1000  # Boss kill bonus
                        self.boss = None
                    projectile.active = False

        # Check bomb collisions
        for bomb in self.player.bombs[:]:
            if bomb.exploded:
                for enemy in self.enemies[:]:
                    dx = bomb.position[0] - enemy.position[0]
                    dy = bomb.position[1] - enemy.position[1]
                    dz = bomb.position[2] - enemy.position[2]
                    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                    if distance < bomb.explosion_radius:
                        enemy.health -= 2  # Bombs do more damage
                        if enemy.health <= 0:
                            self.player.score += SCORE_PER_HIT
                            self.enemies.remove(enemy)
                # --- Boss bomb collision ---
                if self.boss:
                    dx = bomb.position[0] - self.boss.position[0]
                    dy = bomb.position[1] - self.boss.position[1]
                    dz = bomb.position[2] - self.boss.position[2]
                    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                    if distance < bomb.explosion_radius:
                        self.boss.health -= 4
                        if self.boss.health <= 0:
                            self.player.score += 1000
                            self.boss = None

        # Spawn powerups when enemies are killed
        if len(self.enemies) < MAX_ENEMIES and random.random() < ENEMY_SPAWN_RATE:
            self.spawn_powerup()

        # Super power effect
        if self.player.super_power_active:
            # Destroy all enemies
            for enemy in self.enemies[:]:
                self.player.score += SCORE_PER_HIT
                self.create_explosion(enemy.position, (1, 0.8, 0))
                self.enemies.remove(enemy)
            
            # Damage boss if present
            if self.boss:
                self.boss.health -= 5
                self.create_explosion(self.boss.position, (1, 0.8, 0))
                if self.boss.health <= 0:
                    self.player.score += 1000
                    self.boss = None

    def restart_game(self):
        self.player.reset()
        self.enemies = []
        self.boss = None
        self.next_boss_score = self.boss_spawn_score
        self.game_over = False
        self.time_scale = 1.0

    def draw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Set up camera to follow player with increased distance
        camera_x = self.player.position[0] - 20  # Increased from 10 to 20
        camera_y = self.player.position[1] - 20  # Increased from 10 to 20
        camera_z = self.player.position[2] + 10  # Increased from 5 to 10
        look_x = self.player.position[0]
        look_y = self.player.position[1]
        look_z = self.player.position[2]
        gluLookAt(camera_x, camera_y, camera_z, look_x, look_y, look_z, 0, 0, 1)
        
        # Draw all celestial bodies
        for body in self.bodies:
            body.draw()

        # Draw player
        self.player.draw()

        # Draw enemies
        for enemy in self.enemies:
            enemy.draw()

        # Draw boss
        if self.boss:
            self.boss.draw()

        # Draw powerups
        for powerup in self.powerups:
            powerup.draw()

        # Draw particles
        for particle in self.particles:
            particle.draw()

        # Draw HUD
        self.draw_hud()

        # Draw crosshair
        self.draw_crosshair()

    def draw_hud(self):
        # Switch to 2D mode for HUD
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, WINDOW_WIDTH, WINDOW_HEIGHT, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Draw score and lives
        glDisable(GL_LIGHTING)
        glColor3f(1, 1, 1)
        
        # Draw lives as hearts
        for i in range(min(self.player.lives, 10)):
            glColor3f(1, 0, 0)
            glBegin(GL_TRIANGLES)
            x = 30 + i * 30
            y = 30
            glVertex2f(x, y)
            glVertex2f(x + 10, y + 15)
            glVertex2f(x + 20, y)
            glEnd()
        
        # Draw minimap (top-right corner)
        minimap_size = 200
        minimap_x = WINDOW_WIDTH - minimap_size - 20
        minimap_y = 20
        minimap_scale = 0.25  # Define scale at the top level of the function
        
        # Minimap background
        glColor4f(0, 0, 0, 0.5)
        glBegin(GL_QUADS)
        glVertex2f(minimap_x, minimap_y)
        glVertex2f(minimap_x + minimap_size, minimap_y)
        glVertex2f(minimap_x + minimap_size, minimap_y + minimap_size)
        glVertex2f(minimap_x, minimap_y + minimap_size)
        glEnd()
        
        # Minimap border
        glColor3f(1, 1, 1)
        glLineWidth(2)
        glBegin(GL_LINE_LOOP)
        glVertex2f(minimap_x, minimap_y)
        glVertex2f(minimap_x + minimap_size, minimap_y)
        glVertex2f(minimap_x + minimap_size, minimap_y + minimap_size)
        glVertex2f(minimap_x, minimap_y + minimap_size)
        glEnd()

        # Get player position
        px, py = self.player.position[0], self.player.position[1]
        
        # Draw player dot (green)
        glColor3f(0, 1, 0)
        glPointSize(10)
        glBegin(GL_POINTS)
        glVertex2f(minimap_x + minimap_size/2, minimap_y + minimap_size/2)
        glEnd()

        # Draw enemies (different colors for different types)
        glPointSize(7)
        glBegin(GL_POINTS)
        for enemy in self.enemies:
            # Calculate relative position
            rel_x = enemy.position[0] - px
            rel_y = enemy.position[1] - py
            
            # Scale and clamp to minimap
            map_x = minimap_x + minimap_size/2 + rel_x * minimap_scale
            map_y = minimap_y + minimap_size/2 + rel_y * minimap_scale
            
            # Set color based on enemy type
            if enemy.type == 'fast':
                glColor3f(1, 0, 1)  # Purple for fast enemies
            elif enemy.type == 'tank':
                glColor3f(0.5, 0.5, 1)  # Blue for tank enemies
            else:
                glColor3f(1, 0, 0)  # Red for normal enemies
            
            glVertex2f(map_x, map_y)
        glEnd()

        # Draw boss (orange)
        if self.boss:
            glColor3f(1, 0.5, 0)
            glPointSize(12)
            glBegin(GL_POINTS)
            rel_x = self.boss.position[0] - px
            rel_y = self.boss.position[1] - py
            map_x = minimap_x + minimap_size/2 + rel_x * minimap_scale
            map_y = minimap_y + minimap_size/2 + rel_y * minimap_scale
            glVertex2f(map_x, map_y)
            glEnd()

        # Draw score and status
        glColor3f(1, 1, 1)
        aim_mode_names = ["Mouse", "Keyboard", "Auto-Aim"]
        print(f"\nScore: {self.player.score} | Lives: {self.player.lives} | Enemies: {len(self.enemies)}")
        print(f"Aim Mode: {aim_mode_names[self.player.aim_mode]} (Press F2 to change)")
        if self.player.cheat_mode:
            print("CHEAT MODE ACTIVE - Press F1 to toggle")
        if self.boss:
            print(f"BOSS HEALTH: {self.boss.health}")
        if self.game_over:
            print("\nGAME OVER! Press R to restart")
        
        # Restore 3D mode
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glEnable(GL_LIGHTING)

    def draw_crosshair(self):
        # Switch to 2D mode for crosshair
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, WINDOW_WIDTH, WINDOW_HEIGHT, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Draw crosshair
        glDisable(GL_LIGHTING)
        glColor3f(1, 1, 1)  # White crosshair
        glLineWidth(2.0)
        
        # Center of screen
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2
        
        # Draw crosshair lines
        glBegin(GL_LINES)
        # Horizontal line
        glVertex2f(center_x - 10, center_y)
        glVertex2f(center_x + 10, center_y)
        # Vertical line
        glVertex2f(center_x, center_y - 10)
        glVertex2f(center_x, center_y + 10)
        glEnd()
        
        # Restore 3D mode
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        glEnable(GL_LIGHTING)

def main():
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Floating Space Shooter")
    
    # Set up OpenGL
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    
    # Set up perspective
    glMatrixMode(GL_PROJECTION)
    gluPerspective(FOV, WINDOW_WIDTH / WINDOW_HEIGHT, NEAR_CLIP, FAR_CLIP)
    glMatrixMode(GL_MODELVIEW)
    
    # Create solar system
    solar_system = SolarSystem()
    
    # Main game loop
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Update and draw
        solar_system.update(0.016)  # Approximately 60 FPS
        solar_system.draw()
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main() 