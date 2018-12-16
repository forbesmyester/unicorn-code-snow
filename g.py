import time
import sys
from geopy import distance as gDistance, Point
from math import sin, cos, pi
import datetime
import fileinput
import re as re
from functools import partial, reduce
import argparse
try:
    import unicornhathd as unicornhathd
    print("unicorn hat hd detected")
except ImportError:
    from unicorn_hat_sim import unicornhathd as unicornhathd

def chain(functionList):
    def chainImpl(a):
        r = a
        for f in functionList:
            r = f(r)
        return r
    return chainImpl

def myReduce(f, init, lst):
    return reduce(f, lst, init)

def tail(arr):
    return arr[1:]


angles = [0, 45, 90, 135, 180, 225, 270, 315]
directions = [[0, -1], [-1, 1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]]
distances = [1, 4, 16, 64]


parser = argparse.ArgumentParser(description='UI for progress on journey home!')
parser.add_argument('--home', nargs=1, help='The lat,long of home, as given by google maps', required=True)
parser.add_argument('--time', nargs=1, default=int(datetime.datetime.utcnow().timestamp()), help='The current time (for testing)', required=False)
parser.add_argument('--consider', nargs=1, default=1000, help='The current time (for testing)', required=False)
args = parser.parse_args()

lineRe = r"([a-zA-Z0-9]+) ([0-9]+) (\-?[0-9]+\.[0-9]+),(\-?[0-9]+\.[0-9]+)"

def isValidLine(line):
    return re.match(lineRe, line) is not None

def buildLine(line):
    m = re.match(lineRe, line)
    return { 'name': m.group(1), 'lat': float(m.group(3)), 'lng': float(m.group(4)), 'time': int(m.group(2)) }

def getHome(homeConfig):
    r = buildLine("f 0 " + homeConfig)
    del r['time']
    return r

# WARNING: Mutation
def addDistance(home, line):
    line['distance'] = gDistance.distance(Point(home['lat'], home['lng']), Point(line['lat'], line['lng'])).km
    return line

def keyFuncByTime(lineWithDistance):
    return lineWithDistance['time']

def stripper(l):
    return l.strip()

# WARNING: Mutation
def calculateStepValues(acc, line):
    if len(acc) == 0:
        return [line]
    line['elapsed'] = ((line['time'] - acc[-1]['time'])/60)/60
    line['travelled'] = acc[-1]['distance'] - line['distance']
    acc.append(line)
    return acc

# WARNING: Mutation
def addSpeed(line):
    line['speed'] = line['distance'] / line['elapsed']
    return line

# WARNING: Mutation
def addWeight(considerTime, timeNow, line):
    w = (considerTime - (timeNow - line['time'])) / 1000
    line['weight'] = 0
    if (w > 0):
        line['weight'] = w
    return line

def addWeightedSpeed(line):
    line['weightedSpeed'] = line['weight'] * line['speed']
    return line

def tap(line):
    print(line)
    return line

def getSmoothedSpeedMaths(acc, line):
    ws = acc['weightedSpeed'] + line['weightedSpeed']
    w = acc['weight'] + line['weight']
    s = ws / w
    return {
        'weightedSpeed': ws,
        'weight': w,
        'speed': s
    }

def getAngle(angleAttempts, fromA, toB):
    start = Point(toB['lat'], toB['lng'])
    travelDistance = gDistance.VincentyDistance(kilometers = 0.01)
    def worker(acc, bearing):
        destination = travelDistance.destination(point=start, bearing=bearing)
        distancePoint = gDistance.distance(
            Point(fromA['lat'], fromA['lng']),
            Point(destination.latitude, destination.longitude)
        ).km
        if (distancePoint > acc['distance']):
            return { 'bearing': bearing, 'distance': distancePoint }
        return acc
    r = reduce(worker, angleAttempts, { 'bearing': -1, 'distance': -1 })
    return r['bearing']

def getGoodAngle(fromA, toB):
    return getAngle(range(0, 360, 1), fromA, toB)

def getRoughAngle(fromA, toB):
    return getAngle(angles, fromA, toB)


def getNames(lines):
    return list(set(map(lambda a: a['name'], lines)))

home = getHome(args.home[0])
timeNow = int(args.time[0])
considerTime = int(args.consider)


getLines = chain([
    partial(map, stripper),
    partial(filter, isValidLine),
    partial(map, buildLine),
    partial(map, partial(addDistance, home)),
])

def getDataFor(name, lines):
    def isFor(name, item):
        return name == item['name']

    f = chain([
        partial(filter, partial(isFor, name)),
        partial(sorted, key=keyFuncByTime, reverse=False),
        partial(myReduce, calculateStepValues, []),
        tail,
        partial(map, addSpeed),
        partial(map, partial(addWeight, considerTime, timeNow)),
        partial(map, addWeightedSpeed),
    ])

    return f(lines)

lines = list(getLines(sys.stdin))
names = getNames(lines)

houseSprite = [

    [                      [0, 0]
    ],

    [
                           [0, -1],
                 [-1, 0],  [0, 0],  [1, 0],
                 [-1, 1],  [0, 1],  [1, 1]
    ],

    [
                           [0, -2],
                 [-1, -1], [0, -1], [1, -1],
        [-2, 0], [-1, 0],  [0, 0],  [1, 0],  [2, 0],
        [-2, 1], [-1, 1],  [0, 1],  [1, 1],  [2, 1],
        [-2, 2], [-1, 2],  [0, 2],  [1, 2],  [2, 2]
    ],

    [
                                     [0, -3],
                           [-1, -2], [0, -2], [1, -2],
                 [-2, -1], [-1, -1], [0, -1], [1, -1], [2, -1],
        [-3, 0], [-2, 0],  [-1, 0],  [0, 0],  [1, 0],  [2, 0],  [3, 0],
        [-3, 1], [-2, 1],  [-1, 1],  [0, 1],  [1, 1],  [2, 1],  [3, 1],
        [-3, 2], [-2, 2],  [-1, 2],  [0, 2],  [1, 2],  [2, 2],  [3, 2],
        [-3, 3], [-2, 3],  [-1, 3],  [0, 3],  [1, 3],  [2, 3],  [3, 3],
    ],
]

# def full(rgb):
#     r = []
#     for x in range(0, 15):
#         for y in range(0, 15):
#             r.push({'x': x, 'y': y, 'r': rgb['r'], 'g': rgb['g'], 'b': rgb['b']})
#     return r


def getSpritePixels(xy, rgb, sprite, zeroIsFull=False):
    # if (len(sprite) == 0) and zeroIsFull:
    #     return full(rgb)
    def spriteMapper(xy, rgb, spriteCell):
        return {'x': xy['x'] + spriteCell[0], 'y': xy['y'] + spriteCell[1], 'r': rgb['r'], 'g': rgb['g'], 'b': rgb['b']}
    p = partial(spriteMapper, xy, rgb)
    return map(p, sprite)

def drawSpritePixels(unicornhathdspritePixels):
    for p in unicornhathdspritePixels:
        if (p['x'] < 15) and (p['x'] > 0) and (p['y'] < 15) and (p['y'] > 0):
            unicornhathd.set_pixel(15 - p['x'], p['y'], p['r'], p['g'], p['b'])

def getScaleSpriteIndex(distance):
    r = 0
    for d in distances:
        if distance < d:
            return r
        r = r + 1
        if r == 4:
            return -1

def getScaleSpriteDistance(distance):
    i = getScaleSpriteIndex(distance)
    if i == -1:
        return distance
    return distances[i]

def getScaleSpriteSize(distance):
    s = getScaleSpriteIndex(distance)
    if s == -1:
        return 0
    return 3 - s


def getScaleSprite(isLeft, scaleSpriteSize):
    def m():
        if isLeft:
            return 1
        return -1

    r = []
    for p in range(scaleSpriteSize):
        r.append([p * m(), 0])
    return r

def getPersonSprite(pixelCount, screenDistance, personDistance, angle):
    pixelMultiplier = ((personDistance / screenDistance) * pixelCount)
    return [[
        round(pixelMultiplier * sin(angle*(pi/180))),
        0 - round(pixelMultiplier * cos(angle*(pi/180))),
    ]]

maxDistance = sorted(lines, key=keyFuncByTime, reverse=True)[0]['distance']

def getHousePosition(angle):
    direction = directions[angles.index(angle)]
    housePositions = [[8, 2], [2, 13], [13, 8], [13, 13], [8, 13], [2, 13], [2, 8], [2, 2]]
    return {'x': 8 + (direction[0] * 5), 'y': 8 + (direction[1] * 5)}


for n in names:
    data = list(getDataFor(n, lines))
    personDistance = sorted(data, key=keyFuncByTime, reverse=True)[-1]['distance']
    speed = reduce(getSmoothedSpeedMaths, data, {'weight': 0, 'weightedSpeed': 0})['speed']

    travelAngle = getRoughAngle(data[-2], data[-1])
    houseAngle = getRoughAngle(data[-1], home)
    personAngle = getGoodAngle(home, data[-1])
    screenDistance = getScaleSpriteDistance(maxDistance)
    scaleSize = getScaleSpriteSize(maxDistance)
    personSprite = getPersonSprite(13, screenDistance, personDistance, personAngle)
    print(n + ": Max Distance:      " + str(maxDistance))
    print(n + ": Distance:          " + str(personDistance))
    print(n + ": Screen Size Km:    " + str(screenDistance))
    print(n + ": Speed:             " + str(speed))
    print(n + ": Travel Angle:      " + str(travelAngle))
    print(n + ": Scale Size:        " + str(scaleSize))
    print(n + ": House Angle:       " + str(houseAngle))
    print(n + ": Person Angle:      " + str(personAngle))

    unicornhathd.clear()
    housePosition = getHousePosition(houseAngle)
    drawSpritePixels(getSpritePixels(
        housePosition,
        {'r': 100, 'g': 100, 'b': 255},
        houseSprite[scaleSize],
        True
    ))
    drawSpritePixels(getSpritePixels(
        {'x': 15, 'y': 0},
        {'r': 255, 'g': 255, 'b': 255},
        getScaleSprite(False, scaleSize)
    ))

    drawSpritePixels(getSpritePixels(
        housePosition,
        {'r': 255, 'g': 100, 'b': 100},
        personSprite,
    ))

    unicornhathd.show()
    time.sleep(5)

