import pygame as pg
import time
import math
from random import randint, choice, uniform
import numpy as np


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


class TickTimer:
    def __init__(self, ticks):
        self.ticks = ticks
        self.done = False
        self.actual = 0

    def __call__(self):
        self.actual += 1
        if self.actual >= self.ticks:
            self.reboot()
            return True
        return self.done

    def reboot(self):
        self.actual = 0
        self.done = False


class App:
    def __init__(self, w: int, h: int):
        pg.init()
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
        self.dist = int(self.h / 3.5)  # between pipes horizontal
        self.gap = int(self.h / 5.5)  # between pipes vertical
        self.score = 0
        self.high_score = 0
        self.font = pg.font.Font(None, 32)
        self.view_score = self.font.render(str(self.score), True, (255, 255, 255))
        self.view_hscore = self.font.render(str(self.high_score), True, (255, 255, 255))

        self.score_flag = True

        self.bird_borders = {'top': -10, 'bot': self.images['bg'].get_height()}

        # create entity
        self.bg = BG(self)
        self.pipe = PipeCommander(self, self.w + 50, self.dist, gap=self.gap)
        self.bird = BirdCommander(self, 30)

    def run(self):

        while self.running:
            events = pg.event.get()
            for i in events:
                if i.type == pg.QUIT:
                    self.running = False
                if i.type == pg.MOUSEBUTTONDOWN:
                    self.fps = 0 if self.fps else 60

            self.score_flag = True

            # updates
            self.bg.update()
            self.pipe.update()
            self.bird.update()

            # draws
            # self.screen.fill((255, 0, 0))
            self.bg.bg.draw(self.screen)
            self.pipe.draw(self.screen)
            self.bg.ground.draw(self.screen)
            self.bird.draw(self.screen)
            self.screen.blit(self.view_score, (10, 10))
            self.screen.blit(self.view_hscore, (10, 50))

            pg.display.update()
            self.clock.tick(self.fps)

    def check_bird_collide(self, rect):
        return self.pipe.check_collision(rect)

    def coin(self, rect):
        return self.pipe.coin(rect)

    def add_score(self):
        if not self.score_flag:
            return
        self.score_flag = False

        self.score += 0.5
        self.view_score = self.font.render(str(math.floor(self.score)), True, (255, 255, 255))
        if self.score > self.high_score:
            self.high_score = self.score
            self.view_hscore = self.font.render(str(self.high_score), True, (255, 255, 255))

    def reboot(self):
        self.bird.reboot()
        self.pipe.reboot()
        self.bg.reboot()
        self.score = 0
        self.view_score = self.font.render(str(math.floor(self.score)), True, (255, 255, 255))

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
        self.image = app.images['bird']  # pg.Surface((size, size))
        self.surface = pg.Surface((int(self.image.get_width() / 3), self.image.get_height())).convert_alpha()
        self.rect = self.surface.get_rect()
        self.speed_y = 0
        self.jump_force = 12
        self.alive = True

        # animation property
        self.frame_count = 3
        self.step = 0
        self.anim_step = self.rect.w
        self.anim_timer = Timer(0.1).run()

        # first draw
        self.surface.fill((0, 0, 0, 0))
        self.surface.blit(self.image, (0, 0))

        # position bird
        x = self.app.w // 4
        y = self.app.h // 3
        self.rect.topleft = (x, y)
        self.jump_timer = TickTimer(1)  # Timer(0.1).run()  # TickTimer(5)

        # other params
        self.borders = self.app.bird_borders
        self.r = min(self.rect.size)  # radius collider
        self.coin_flag = False

    def update(self, *args, **kwargs):
        if not self.alive:
            self.app.reboot()
            return
        self.speed_y += self.app.gravity
        self.rect.top += self.speed_y

        # check border collide
        if self.rect.bottom >= self.borders['bot']:
            self.alive = False
            return
        elif self.rect.bottom <= self.borders['top']:
            self.alive = False
            return

        # check pipe collide
        if self.app.check_bird_collide(self.rect):
            self.alive = False
        self.coin_collide()

    def draw(self, sc: pg.Surface):
        self.animate()
        sc.blit(self.surface, self.rect)

    def animate(self):
        if self.anim_timer():
            self.__next_step()

            self.surface.fill((0, 0, 0, 0))
            self.surface.blit(self.image, (-1 * self.step * self.anim_step, 0))

    def __next_step(self):
        self.step += 1
        if self.step >= self.frame_count:
            self.step = 0

    def jump(self):
        if self.jump_timer():
            self.speed_y = -self.jump_force

    def reboot(self):
        self.alive = True
        self.speed_y = 0
        x = self.app.w // 4
        y = self.app.h // 3
        self.rect.topleft = (x, y)
        self.step = 0

    def coin_collide(self):
        res = self.app.coin(self.rect)
        if res != self.coin_flag:
            self.app.add_score()
        self.coin_flag = res


class NeiroBird(Bird):
    def __init__(self, app, parent: 'BirdCommander'):
        super().__init__(app)
        self.parent = parent
        self.rating = 0
        self.neiro = Neiro(self.parent.neiro_params)
        self.active_value = 0.5

        self.cross_f = np.vectorize(self.one_at_two)

    def update(self, top_y, bot_y):
        if not self.alive:
            return
        # gravity logic
        self.speed_y += self.app.gravity
        self.rect.top += self.speed_y

        # ask to neiro
        # prepare data
        value1 = top_y - self.rect.centery
        value2 = self.rect.centery - bot_y

        # predict
        result = self.neiro.predict([value1, value2])
        if result[0] >= self.active_value:
            self.jump()

        # check border collide
        if self.rect.bottom >= self.borders['bot']:
            self.alive = False
            return
        elif self.rect.bottom <= self.borders['top']:
            self.alive = False
            return

        # check pipe collide
        if self.app.check_bird_collide(self.rect):
            self.alive = False
        self.coin_collide()

    def reboot(self):
        super().reboot()
        self.rating = 0

    def coin_collide(self):
        res = self.app.coin(self.rect)
        if res != self.coin_flag:
            self.app.add_score()
            self.rating += 1
        self.coin_flag = res

    def draw(self, sc: pg.Surface):
        if not self.alive:
            return
        super().draw(sc)

    def cross_mutate(self, bird):
        for i in range(len(self.neiro.weight)):
            self.neiro.weight[i] = self.cross_f(self.neiro.weight[i], bird.neiro.weight[i])
        self.mutate()

    def mutate(self):
        layer = randint(0, len(self.neiro.weight) - 1)
        temp = self.neiro.weight[layer]
        y = randint(0, len(temp) - 1)
        x = randint(0, len(temp[0]) - 1)
        temp[y][x] += uniform(-0.05, 0.05)

    @staticmethod
    def one_at_two(a, b):
        return choice([a, b])


class BirdCommander:
    def __init__(self, app, count):
        self.app = app
        self.pipes = self.app.pipe
        self.count = count
        self.neiro_params = [2, 3, 1]

        self.birds = [NeiroBird(self.app, self) for _ in range(self.count)]

        self.age_timer = Timer(60).run()

        # views
        self.font = self.app.font
        self.info = self.font.render('', False, (0, 0, 0))

    def update(self):
        # check age need
        if not self.is_alive() or self.age_timer():
            self.age_timer.reboot()
            self.new_age()
            self.app.reboot()
            return

        # default update logic
        rect = self.birds[0].rect
        top_y, bot_y = self.pipes.get_pipe_info(rect)
        for bird in self.birds:
            bird.update(top_y, bot_y)

    def new_age(self):
        self.birds = sorted(self.birds, key=lambda x: x.rating, reverse=True)
        first = self.birds[0]
        for i in self.birds[1:]:
            flag = randint(0, 1)
            if flag:
                i.cross_mutate(first)
            else:
                i.mutate()

    def draw(self, sc: pg.Surface):
        for i in self.birds:
            i.draw(sc)

        lives = self.count_alive()
        self.info = self.font.render(f'Alive: {lives}', True, (255, 255, 255))
        sc.blit(self.info, (100, 10))

    def reboot(self):
        for i in self.birds:
            i.reboot()

    def is_alive(self):
        for i in self.birds:
            if i.alive:
                return True
        return False

    def count_alive(self):
        i = 0
        for bird in self.birds:
            if bird.alive:
                i += 1
        return i


class Neiro:
    def __init__(self, arr: list[int], name=''):
        self.name = name
        self.arr = arr
        self.len_arr = len(self.arr)
        self.act_func = np.vectorize(self.le_relu)

        # create weights
        self.weight = []
        for i in range(self.len_arr - 1):
            buf = np.random.uniform(-1, 1, (self.arr[i + 1], self.arr[i] + 1))
            self.weight.append(buf)

        # create layers
        self.layer = []
        for i in range(self.len_arr - 1):
            self.layer.append(np.ones(self.arr[i] + 1, float))
        self.layer.append(np.ones(self.arr[-1], float))

    def predict(self, arr):
        self.layer[0][:-1] = np.array(arr, float)
        for i in range(self.len_arr - 2):
            res = np.dot(self.weight[i], self.layer[i])
            res = self.act_func(res)
            self.layer[i + 1][:-1] = res
        res = np.dot(self.weight[-1], self.layer[-2])
        self.layer[-1] = self.act_func(res)
        return self.layer[-1]

    @staticmethod
    def sig(a):
        if a < 0:
            return -1.0
        return -3 / (a + 1) + 2

    @staticmethod
    def zz(a):
        res = math.sin(a)
        return res * 3

    @staticmethod
    def le_relu(a):
        ma = 1.0
        mi = 0.0
        if a < mi:
            return a * 0.1
        if a > ma:
            return (a - ma) * 0.1 + ma
        return a

    @staticmethod
    def relu(a):
        if a < 0:
            return 0.0
        else:
            return a


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

    def get_pipe_info(self, rect):
        # find actual pipe
        temp = None
        for pipe in self.pipes:
            res = pipe.actual(rect)
            if res:
                temp = pipe
                break

        return temp.top_rect.bottom, temp.bot_rect.top

    def coin(self, rect):
        flag = False
        for pipe in self.pipes:
            flag = pipe.coin(rect)
            if flag:
                return flag
        return flag

    def check_collision(self, rect):
        flag = False
        for pipe in self.pipes:
            flag = pipe.check_collision(rect)
            if flag:
                return flag
        return flag

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

    def reboot(self):
        i = 0
        for pipe in self.pipes:
            new_x = self.start_pos + i * self.dist
            new_y = randint(*self.random_borders)
            pipe.set_new_position(new_x, new_y)
            i += 1


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
        self.coin_rect = pg.Rect(0, 0, self.top_rect.w, self.gap)

        self.set_new_position(cx, cy)

    def check_collision(self, rect):
        f1 = self.top_rect.colliderect(rect)
        f2 = self.bot_rect.colliderect(rect)
        return f1 or f2

    def coin(self, rect):
        return self.coin_rect.colliderect(rect)

    def actual(self, rect):
        if rect.left > self.top_rect.right:
            return False
        return True

    def set_new_position(self, cx, cy):
        x = cx - int(self.top_rect.w / 2)
        half_gap = int(self.gap / 2)
        bot_y = cy + half_gap
        top_y = cy - half_gap - self.top_rect.h

        self.bot_rect.topleft = (x, bot_y)
        self.top_rect.topleft = (x, top_y)
        self.coin_rect.center = (cx, cy)

    def move(self, step):
        self.top_rect.left += step
        self.bot_rect.left += step
        self.coin_rect.left += step

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

    def reboot(self):
        pass


if __name__ == '__main__':
    App(800, 600).run()
