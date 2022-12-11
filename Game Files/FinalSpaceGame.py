import random
import math
import arcade

SPRITE_SCALING_PLAYER = 0.5
SPRITE_SCALING_COIN = 0.4
SPRITE_SCALING_LASER = 0.8
COIN_COUNT = 3
TIMEBETWEENCOIN = 100

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 750
SCREEN_TITLE = "Space Game"
MUSIC_VOLUME = 0.5
VIEWPORT_MARGIN = 40

ENEMY_SPEED = 2
BULLET_SPEED = 10
BULLET_DAMAGE = 1
PLAYER_HEALTH = 10
MOVEMENT_SPEED = 5

# Speed limit
MAX_SPEED = 6.0

# How fast we accelerate
ACCELERATION_RATE = 0.3

# How fast to slow down after we let off the key
FRICTION = 0.06


# --- Explosion Particles Related

# How fast the particle will accelerate down. Make 0 if not desired
PARTICLE_GRAVITY = 0.05

# How fast to fade the particle
PARTICLE_FADE_RATE = 8

# How fast the particle moves. Range is from 2.5 <--> 5 with 2.5 and 2.5 set.
PARTICLE_MIN_SPEED = 2.5
PARTICLE_SPEED_RANGE = 2.5

# How many particles per explosion
PARTICLE_COUNT = 20

# How big the particle
PARTICLE_RADIUS = 3

# Possible particle colors
PARTICLE_COLORS = [arcade.color.ALIZARIN_CRIMSON,
                   arcade.color.COQUELICOT,
                   arcade.color.LAVA,
                   arcade.color.KU_CRIMSON,
                   arcade.color.DARK_TANGERINE]

# Chance we'll flip the texture to white and make it 'sparkle'
PARTICLE_SPARKLE_CHANCE = 0.02

# --- Smoke
# Note: Adding smoke trails makes for a lot of sprites and can slow things
# down. If you want a lot, it will be necessary to move processing to GPU
# using transform feedback. If to slow, just get rid of smoke.

# Start scale of smoke, and how fast is scales up
SMOKE_START_SCALE = 0.25
SMOKE_EXPANSION_RATE = 0.03

# Rate smoke fades, and rises
SMOKE_FADE_RATE = 7
SMOKE_RISE_RATE = 0.5

# Chance we leave smoke trail
SMOKE_CHANCE = 0.25


class InstructionView(arcade.View):
    def on_show_view(self):
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        self.clear()
        arcade.draw_text("Welcome to Space Escape!", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                         arcade.color.WHITE, font_size=50, anchor_x="center")
        arcade.draw_text("Shoot bullets to destroy enemies by aiming with the mouse and clicking.", SCREEN_WIDTH / 2,
                         SCREEN_HEIGHT / 2 - 75,
                         arcade.color.WHITE, font_size=20, anchor_x="center")
        arcade.draw_text("Move by using the WASD keys or the arrow keys.",
                         SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 125,
                         arcade.color.WHITE, font_size=20, anchor_x="center")
        arcade.draw_text("Click to advance", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 175,
                         arcade.color.RED, font_size=20, anchor_x="center")

    def on_mouse_press(self, _x, _y, _button, _modifiers):
        game_view = MyGame()
        game_view.setup()
        self.window.show_view(game_view)


class Smoke(arcade.SpriteCircle):
    """ This represents a puff of smoke """
    def __init__(self, size):
        super().__init__(size, arcade.color.LIGHT_GRAY, soft=True)
        self.change_y = SMOKE_RISE_RATE
        self.scale = SMOKE_START_SCALE

    def update(self):
        """ Update this particle """
        if self.alpha <= PARTICLE_FADE_RATE:
            # Remove faded out particles
            self.remove_from_sprite_lists()
        else:
            # Update values
            self.alpha -= SMOKE_FADE_RATE
            self.center_x += self.change_x
            self.center_y += self.change_y
            self.scale += SMOKE_EXPANSION_RATE


class Particle(arcade.SpriteCircle):
    """ Explosion particle """
    def __init__(self, my_list):
        # Choose a random color
        color = random.choice(PARTICLE_COLORS)

        # Make the particle
        super().__init__(PARTICLE_RADIUS, color)

        # Track normal particle texture, so we can 'flip' when we sparkle.
        self.normal_texture = self.texture

        # Keep track of the list we are in, so we can add a smoke trail
        self.my_list = my_list

        # Set direction/speed
        speed = random.random() * PARTICLE_SPEED_RANGE + PARTICLE_MIN_SPEED
        direction = random.randrange(360)
        self.change_x = math.sin(math.radians(direction)) * speed
        self.change_y = math.cos(math.radians(direction)) * speed

        # Track original alpha. Used as part of 'sparkle' where we temp set the
        # alpha back to 255
        self.my_alpha = 255

        # What list do we add smoke particles to?
        self.my_list = my_list

    def update(self):
        """ Update the particle """
        if self.my_alpha <= PARTICLE_FADE_RATE:
            # Faded out, remove
            self.remove_from_sprite_lists()
        else:
            # Update
            self.my_alpha -= PARTICLE_FADE_RATE
            self.alpha = self.my_alpha
            self.center_x += self.change_x
            self.center_y += self.change_y
            self.change_y -= PARTICLE_GRAVITY

            # Should we sparkle this?
            if random.random() <= PARTICLE_SPARKLE_CHANCE:
                self.alpha = 255
                self.texture = arcade.make_circle_texture(int(self.width),
                                                          arcade.color.WHITE)
            else:
                self.texture = self.normal_texture

            # Leave a smoke particle?
            if random.random() <= SMOKE_CHANCE:
                smoke = Smoke(5)
                smoke.position = self.position
                self.my_list.append(smoke)


class Player(arcade.Sprite):
    """ Player Class """

    def update(self):
        """ Move the player """
        # Move player.
        # Remove these lines if physics engine is moving player.
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Check for out-of-bounds
        if self.left < 0:
            self.left = 0
            self.change_x = 0  # Zero x speed
        elif self.right > SCREEN_WIDTH - 1:
            self.right = SCREEN_WIDTH - 1
            self.change_x = 0

        if self.bottom < 0:
            self.bottom = 0
            self.change_y = 0
        elif self.top > SCREEN_HEIGHT - 1:
            self.top = SCREEN_HEIGHT - 1
            self.change_y = 0


class Coin(arcade.Sprite):
    def __init__(self, image, scale, speed):
        super().__init__(image, scale)
        self.enemy_speed = speed

    def follow_sprite(self, player_sprite):
        """
        This function will move the current sprite towards whatever
        other sprite is specified as a parameter.

        We use the 'min' function here to get the sprite to line up with
        the target sprite, and not jump around if the sprite is not off
        an exact multiple of SPRITE_SPEED.
        """

        if self.center_y < player_sprite.center_y:
            self.center_y += min(self.enemy_speed, player_sprite.center_y - self.center_y)
        elif self.center_y > player_sprite.center_y:
            self.center_y -= min(self.enemy_speed, self.center_y - player_sprite.center_y)

        if self.center_x < player_sprite.center_x:
            self.center_x += min(self.enemy_speed, player_sprite.center_x - self.center_x)
        elif self.center_x > player_sprite.center_x:
            self.center_x -= min(self.enemy_speed, self.center_x - player_sprite.center_x)


class MyGame(arcade.View):
    """ Main application class. """

    def __init__(self):
        """ Initializer """
        # Call the parent class initializer
        super().__init__()

        # Background image will be stored in this variable
        self.background = None

        # Variables that will hold sprite lists
        self.player_list = None
        self.coin_list = None
        self.bullet_list = None
        self.explosions_list = None
        self.mouse_list = None

        # Set up the player info
        self.player_sprite = None
        self.score = 0
        self.time_taken = 0

        # Difficulty
        self.dropTime = TIMEBETWEENCOIN
        self.difficulty = 70  # Initial speed determiner
        self.enemy_speed = ENEMY_SPEED

        # Timer
        self.total_time = 0.0
        self.timer_text = arcade.Text(
            text="00:00:00",
            start_x=200,
            start_y=20,
            color=arcade.color.WHITE,
            font_size=14,
            anchor_x="center",
        )

        # Track the current state of what key is pressed
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        # mouse cursor
        self.mouse_sprite = None

        # Don't show the mouse cursor
        self.window.set_mouse_visible(False)

        # Load sounds. Sounds from kenney.nl
        self.gun_sound = arcade.sound.load_sound(":resources:sounds/laser3.wav")
        self.hit_sound = arcade.sound.load_sound(":resources:sounds/explosion2.wav")

        arcade.set_background_color(arcade.color.BLACK)

        # Music
        self.music = arcade.load_sound("music/Steamtech-Mayhem_Looping.wav")

    def on_show_view(self):
        arcade.set_background_color(arcade.color.AMAZON)

        # Don't show the mouse cursor
        self.window.set_mouse_visible(False)

    def setup(self):

        """ Set up the game and initialize the variables. """

        self.background = arcade.load_texture("images/aRTU12s.jpg")

        # Sprite lists
        self.player_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.explosions_list = arcade.SpriteList()
        self.mouse_list = arcade.SpriteList()

        # Set up the player
        self.score = 0

        # Set up Music
        self.music.play(1.0, 0.0, True, 1.0)

        # Image from kenney.nl
        self.player_sprite = Player(":resources:images/space_shooter/playerShip2_orange.png", SPRITE_SCALING_PLAYER)

        # PlayerFollow
        self.player_sprite.center_x = 50
        self.player_sprite.center_y = 70
        self.player_list.append(self.player_sprite)

        # Mouse image
        self.mouse_sprite = arcade.Sprite(":resources:images/space_shooter/meteorGrey_tiny1.png", SPRITE_SCALING_PLAYER)
        self.mouse_sprite.center_x = 50
        self.mouse_sprite.center_y = 70
        self.mouse_list.append(self.mouse_sprite)

        # Create the coins

        for coin_index in range(5):

            # Create the coin instance
            # Coin image from kenney.nl
            coin = Coin(":resources:images/space_shooter/playerShip1_green.png",
                        SPRITE_SCALING_COIN, ENEMY_SPEED)
            coin.angle = 180

            # Position the coin
            coin.center_x = random.randrange(SCREEN_WIDTH)
            coin.center_y = SCREEN_HEIGHT

            # Add the coin to the lists
            self.coin_list.append(coin)

    def on_draw(self):
        """
        Render the screen.
        """

        # This command has to happen before we start drawing
        self.clear()

        # Draw the background texture
        arcade.draw_lrwh_rectangle_textured(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, self.background)

        # Draw all the sprites.
        self.coin_list.draw()
        self.bullet_list.draw()
        self.player_list.draw()
        self.explosions_list.draw()
        self.mouse_list.draw()

        # Render the text
        arcade.draw_text(f"Score: {self.score}", 10, 20, arcade.color.WHITE, 14)
        self.timer_text.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        """
        Called whenever the mouse moves.
        """
        self.mouse_sprite.center_x = x
        self.mouse_sprite.center_y = y

    def on_mouse_press(self, x, y, button, modifiers):

        """
        Called whenever the mouse button is clicked.
        """

        # Gunshot sound
        arcade.sound.play_sound(self.gun_sound)

        # Create a bullet
        bullet = arcade.Sprite(":resources:images/space_shooter/laserBlue01.png", SPRITE_SCALING_LASER)

        # The image points to the right, and we want it to point up. So
        # rotate it.

        # Give it a speed
        bullet.change_y = BULLET_SPEED

        # Position the bullet
        bullet.center_x = self.player_sprite.center_x
        bullet.bottom = self.player_sprite.top

        start_x = self.player_sprite.center_x
        start_y = self.player_sprite.center_y
        bullet.center_x = start_x
        bullet.center_y = start_y

        # Get from the mouse the destination location for the bullet
        # IMPORTANT! If you have a scrolling screen, you will also need
        # to add in self.view_bottom and self.view_left.
        dest_x = x
        dest_y = y

        # Do math to calculate how to get the bullet to the destination.
        # Calculation the angle in radians between the start points
        # and end points. This is the angle the bullet will travel.
        x_diff = dest_x - start_x
        y_diff = dest_y - start_y
        angle = math.atan2(y_diff, x_diff)

        # Angle the bullet sprite, so it doesn't look like it is flying
        # sideways.
        bullet.angle = math.degrees(angle)
        self.player_sprite.change_angle = (round(math.degrees(angle)) * -1)

        # Taking into account the angle, calculate our change_x
        # and change_y. Velocity is how fast the bullet travels.
        bullet.change_x = math.cos(angle) * BULLET_SPEED
        bullet.change_y = math.sin(angle) * BULLET_SPEED

        # Add the bullet to the appropriate lists
        self.bullet_list.append(bullet)

    def on_mouse_release(self, x, y, button, modifiers):
        self.player_sprite.change_angle = 0
        super().on_mouse_release(x, y, button, modifiers)

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """

        # Forward/back
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """

        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False

    def on_update(self, delta_time):
        """ Movement and game logic """

        # Call update on bullet sprites
        self.bullet_list.update()
        self.explosions_list.update()
        self.player_list.update()
        self.mouse_list.update()
        self.coin_list.update()

        if self.dropTime == 0:
            for coin_index in range(COIN_COUNT):
                # Create the coin instance
                # Coin image from kenney.nl
                coin = Coin(":resources:images/space_shooter/playerShip1_green.png", SPRITE_SCALING_COIN,
                            self.enemy_speed)
                coin.angle = 180

                # Position the coin
                coin.center_x = random.randrange(SCREEN_WIDTH)
                coin.center_y = SCREEN_HEIGHT

                # Add the coin to the lists
                self.coin_list.append(coin)
            self.dropTime = TIMEBETWEENCOIN * (random.randrange(self.difficulty, 100) / 100)

        else:
            self.dropTime = self.dropTime - 1

        for coin in self.coin_list:
            coin.follow_sprite(self.player_sprite)

        # Accumulate the total time
        self.total_time += delta_time

        # Calculate minutes
        minutes = int(self.total_time) // 60

        # Calculate seconds by using a modulus (remainder)
        seconds = int(self.total_time) % 60

        # Calculate 100s of a second
        seconds_100s = int((self.total_time - seconds) * 100)

        # Use string formatting to create a new text string for our timer
        self.timer_text.text = f"Time: {minutes:02d}:{seconds:02d}:{seconds_100s:02d}"

        # Add some friction
        if self.player_sprite.change_x > FRICTION:
            self.player_sprite.change_x -= FRICTION
        elif self.player_sprite.change_x < -FRICTION:
            self.player_sprite.change_x += FRICTION
        else:
            self.player_sprite.change_x = 0

        if self.player_sprite.change_y > FRICTION:
            self.player_sprite.change_y -= FRICTION
        elif self.player_sprite.change_y < -FRICTION:
            self.player_sprite.change_y += FRICTION
        else:
            self.player_sprite.change_y = 0

        # Apply acceleration based on the keys pressed
        if self.up_pressed and not self.down_pressed:
            self.player_sprite.change_y += ACCELERATION_RATE
        elif self.down_pressed and not self.up_pressed:
            self.player_sprite.change_y += -ACCELERATION_RATE
        if self.left_pressed and not self.right_pressed:
            self.player_sprite.change_x += -ACCELERATION_RATE
        elif self.right_pressed and not self.left_pressed:
            self.player_sprite.change_x += ACCELERATION_RATE

        if self.player_sprite.change_x > MAX_SPEED:
            self.player_sprite.change_x = MAX_SPEED
        elif self.player_sprite.change_x < -MAX_SPEED:
            self.player_sprite.change_x = -MAX_SPEED
        if self.player_sprite.change_y > MAX_SPEED:
            self.player_sprite.change_y = MAX_SPEED
        elif self.player_sprite.change_y < -MAX_SPEED:
            self.player_sprite.change_y = -MAX_SPEED

        # Loop through each bullet
        for bullet in self.bullet_list:

            # Check this bullet to see if it hit a coin
            hit_list = arcade.check_for_collision_with_list(bullet, self.coin_list)

            # If it did...
            if len(hit_list) > 0:

                # Get rid of the bullet
                bullet.remove_from_sprite_lists()

            # For every coin we hit, add to the score and remove the coin
            for coin in hit_list:
                # Make an explosion
                for i in range(PARTICLE_COUNT):
                    particle = Particle(self.explosions_list)
                    particle.position = coin.position
                    self.explosions_list.append(particle)

                smoke = Smoke(50)
                smoke.position = coin.position
                self.explosions_list.append(smoke)

                coin.remove_from_sprite_lists()
                self.score += 1
                if self.score % 5 == 0:
                    self.enemy_speed += .2
                    for item in self.coin_list:
                        item.enemy_speed += .2

                # Hit Sound
                arcade.sound.play_sound(self.hit_sound)

            # If the bullet flies off-screen, remove it.
            if bullet.bottom > SCREEN_HEIGHT:
                bullet.remove_from_sprite_lists()
            if bullet.bottom < 20:
                bullet.remove_from_sprite_lists()

        # Generate a list of all sprites that collided with the player.
        hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.coin_list)

        # If we've collected all the games, then move to a "GAME_OVER"
        # state.
        if len(hit_list) > 0:
            self.hit_sound = arcade.sound.load_sound(":resources:sounds/gameover3.wav")
            arcade.sound.play_sound(self.hit_sound, 5.0)

            game_over_view = GameOverView(self.timer_text.text, self.score)
            self.window.set_mouse_visible(True)
            self.window.show_view(game_over_view)


class GameOverView(arcade.View):
    def __init__(self, time, score):
        super().__init__()
        self.time_taken = time
        self.total_score = score

    def on_show_view(self):
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        self.clear()
        """
        Draw "Game over" across the screen.
        """
        arcade.draw_text("YOU DIED ~ Game Over", SCREEN_WIDTH / 2, 400, arcade.color.RED, 54, anchor_x="center")
        arcade.draw_text("Press Escape to End", SCREEN_WIDTH / 2, 300, arcade.color.WHITE, 24, anchor_x="center")
        arcade.draw_text(self.time_taken, SCREEN_WIDTH / 2, 100, arcade.color.WHITE, 30, anchor_x="center")

        output_total = f"Total Score: {self.total_score}"
        arcade.draw_text(output_total, SCREEN_WIDTH / 2, 20, arcade.color.WHITE, 30, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            arcade.exit()


def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "Space Game")
    menu_view = InstructionView()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()
