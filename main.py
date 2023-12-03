import pygame as pg
import time
import math
from random import randint


class Timer:
    def __init__(self, sec: int | float = 1, auto_reboot: bool = True):
        self.sec = sec
        self.auto_reboot = auto_reboot
        self.start_time = None
        self.active = False

    def __call__(self, *args, **kwargs):
        if time.time() - self.start_time > self.sec:
            self.active = True
            if self.auto_reboot:
                self.reboot()
                return True
        return self.active

    def run(self):
        self.start_time = time.time()
        return self

    def reboot(self, sec=None):
        if sec:
            self.sec = sec
        self.active = False
        self.run()


class App:
    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self.screen = pg.display.set_mode((self.w, self.h))
        self.clock = pg.time.Clock()
        self.fps = 60
        self.running = True
        self.scale = 1  # for images and speed

        # load images
        self.images = self.load_images()

        # other details
        self.gravity = 1
        self.speed = -3
        self.dist = int(self.h / 3)
        self.gap = int(self.h / 5)

    def run(self):
        bird = Bird(self)
        bg = BG(self)
        pipe = PipeCommander(self, self.w + 50, self.dist, gap=self.gap)
        while self.running:
            events = pg.event.get()
            for i in events:
                if i.type == pg.QUIT:
                    self.running = False
                if i.type == pg.MOUSEBUTTONDOWN:
                    bird.jump()

            # updates
            bg.update()
            pipe.update()
            bird.update()

            # draws
            self.screen.fill((255, 0, 0))
            bg.bg.draw(self.screen)
            pipe.draw(self.screen)
            bg.ground.draw(self.screen)
            bird.draw(self.screen)

            pg.display.update()
            self.clock.tick(self.fps)

    def load_images(self):
        res = {'bg': pg.image.load('sourse/bg.bmp').convert(),
               'bird': pg.image.load('sourse/bird.bmp').convert(),
               'ground': pg.image.load('sourse/ground.bmp').convert(),
               'pipe': pg.image.load('sourse/pipe.bmp').convert()}

        # find new self.scale
        self.scale = math.ceil(self.h / (res['bg'].get_height() + res['ground'].get_height()))

        for k in res.keys():
            w, h = res[k].get_size()
            w, h = w * self.scale, h * self.scale
            res[k] = pg.transform.scale(res[k], (w, h))

        res['bird'].set_colorkey((255, 255, 255))
        res['pipe'].set_colorkey((255, 255, 255))
        return res


class Bird:
    def __init__(self, app):
        self.app = app
        self.surface = app.images['bird']  # pg.Surface((size, size))
        self.rect = self.surface.get_rect()
        self.speed_y = 0
        self.jump_force = 12

        # position bird
        x = self.app.w // 4
        y = self.app.h // 3
        self.rect.topleft = (x, y)

        self.jump_timer = Timer(0.1).run()

    def update(self):
        self.speed_y += self.app.gravity
        self.rect.top += self.speed_y

    def draw(self, sc: pg.Surface):
        sc.blit(self.surface, self.rect)

    def jump(self):
        if self.jump_timer():
            self.speed_y = -self.jump_force


class PipeCommander:
    def __init__(self, app, start_pos, dist, gap=100):
        self.app = app
        self.start_pos = start_pos
        self.dist = dist
        self.gap = gap
        self.bot_image = self.app.images['pipe']
        self.top_image = pg.transform.rotate(self.bot_image, 180)

        # find params
        self.count = math.ceil(self.app.w / dist) + 1

        def_center = self.app.images['bg'].get_height() // 2
        delta = def_center // 3
        low_value = def_center - delta
        high_value = def_center + delta
        self.random_borders = (low_value, high_value)

        # generate pipes
        self.pipes = []
        for i in range(self.count):
            temp = Pipe(self, self.start_pos + i * self.dist, randint(*self.random_borders), self.gap)
            self.pipes.append(temp)

    def update(self):
        for pipe in self.pipes:
            pipe.move(self.app.speed)

        if self.pipes[0].right <= 0:
            new_x = self.pipes[-1].center_x + self.dist
            new_y = randint(*self.random_borders)
            self.pipes[0].set_new_position(new_x, new_y)

            self.pipes = self.pipes[1:] + [self.pipes[0]]

    def draw(self, sc: pg.Surface):
        for pipe in self.pipes:
            pipe.draw(sc)


class Pipe:
    def __init__(self, parent: PipeCommander, cx: int, cy: int, gap: int):
        self.parent = parent
        # self.cx = cx
        # self.cy = cy
        self.gap = gap
        self.bot_image = parent.bot_image
        self.top_image = parent.top_image

        self.bot_rect = self.bot_image.get_rect()
        self.top_rect = self.top_image.get_rect()

        self.set_new_position(cx, cy)

    def set_new_position(self, cx, cy):
        x = cx - int(self.top_rect.w / 2)
        half_gap = int(self.gap / 2)
        bot_y = cy + half_gap
        top_y = cy - half_gap - self.top_rect.h

        self.bot_rect.topleft = (x, bot_y)
        self.top_rect.topleft = (x, top_y)

    def move(self, step):
        self.top_rect.left += step
        self.bot_rect.left += step

    @property
    def right(self):
        return self.top_rect.right

    @property
    def center_x(self):
        return self.top_rect.centerx

    def draw(self, sc: pg.Surface):
        sc.blit(self.top_image, self.top_rect)
        sc.blit(self.bot_image, self.bot_rect)


class R:
    def __init__(self, x, y, w):
        self.x = x
        self.y = y
        self.w = w

    def set(self, x, y):
        self.x, self.y = x, y

    def add(self, x, y=0):
        self.x += x
        self.y += y

    def get(self):
        return self.x, self.y

    def get_next(self):
        return self.x + self.w, self.y

    @property
    def right(self):
        return self.x + self.w


class SpriteMover:
    def __init__(self, image: pg.Surface, y: int | float,
                 speed: float = 1, global_w: int = 10):
        self.image = image
        self.y = y
        self.speed = speed
        self.global_w = global_w

        # find count images
        self.count = math.ceil(self.global_w / self.image.get_width()) + 1

        # create sprite and params
        w = self.image.get_width()
        step = [i * w for i in range(self.count)]
        self.r = [R(i, self.y, w) for i in step]

    def update(self):
        for i in self.r:
            i.add(self.speed, 0)

        if self.r[0].right <= 0:
            self.r[0].set(*self.r[-1].get_next())
            self.r = self.r[1:] + [self.r[0]]

    def draw(self, sc: pg.Surface):
        for i in self.r:
            sc.blit(self.image, i.get())


class BG:
    def __init__(self, app):
        self.app = app
        self.bg_image = self.app.images['bg']
        self.ground_image = self.app.images['ground']

        bg_speed = self.app.speed * 0.2
        ground_speed = self.app.speed
        ground_y = self.app.h - self.ground_image.get_height()
        self.bg = SpriteMover(self.bg_image, 0, bg_speed, self.app.w)
        self.ground = SpriteMover(self.ground_image, ground_y, ground_speed, self.app.w)

    def update(self):
        self.bg.update()
        self.ground.update()

    def draw(self, sc: pg.Surface):
        self.bg.draw(sc)
        self.ground.draw(sc)


if __name__ == '__main__':
    App(800, 600).run()
