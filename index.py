import time
import random
try:
    import unicornhathd as unicornhathd
    print("unicorn hat hd detected")
except ImportError:
    from unicorn_hat_sim import unicornhathd as unicornhathd

sleep_time = 1/120
# sleep_time = 1/16
maxHeight = 15
maxWidth = 15

class AirSnow:
    x = 0
    h = maxHeight
    def __init__(self, x):
        self.x = x
    def __repr__(self):
        return 'A' + str(self.x) + ':' + str(self.h)
    def fall(self):
        self.h = self.h - 1

air = []
ground = [0 for _ in range(maxWidth + 1)]

def hasHitGround(airSnow):
    groundHeight = 0
    if len(ground) > airSnow.x:
        groundHeight = ground[airSnow.x]
    if airSnow.h <= groundHeight + 1:
        return True
    return False

def addToGround(index):
    ground[air[index].x] = ground[air[index].x] + 1
    air.pop(index)

def slideGroundImpl(rng, wind):
    for i in rng:
        if ground[i + wind] < ground[i] - 1:
            ground[i + wind] = ground[i + wind] + 1
            ground[i] = ground[i] - 1

def slideGround(direction):
    if (direction == 1):
        slideGroundImpl(range(maxWidth), 1)
    else:
        slideGroundImpl(range(maxWidth, 0, -1), -1)

def snowColor():
    r = (max(ground) * 16) + 64
    if r > 255:
        return 255
    return r


def draw(ground, air):
    unicornhathd.clear()
    for x, height in enumerate(ground):
        r = 0
        for y in range(maxHeight, 0, -1):
            if (y == height):
                r = 63
            if (r > 0) and (r < 255):
                r = r + 16
            unicornhathd.set_pixel(x, maxHeight - y ,r, 0, 0)
    for air in air:
        unicornhathd.set_pixel(air.x, maxHeight - air.h, snowColor(), 0, 0)
    unicornhathd.show()



timeLoop = 0
while (max(ground) < 16):
    draw(ground, air)
    if (timeLoop % 5) == 0:
        air.append(AirSnow(random.randint(0, maxWidth)))
    if (timeLoop % random.randint(3, 7)) == 0:
	    slideGround(random.randint(0, 1))
    for i in range(len(air) - 1, -1, -1):
        air[i].fall()
        if (hasHitGround(air[i])):
            addToGround(i)
    time.sleep(sleep_time)
    timeLoop = timeLoop + 1

time.sleep(2)
unicornhathd.clear()
unicornhathd.show()

