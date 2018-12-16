import time
import sys
from geopy import distance, Point
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
    line['distance'] = distance.distance(Point(home['lat'], home['lng']), Point(line['lat'], line['lng'])).km
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

def getRoughAngle(fromA, toB):
    start = Point(toB['lat'], toB['lng'])
    travelDistance = distance.VincentyDistance(kilometers = 0.01)
    def worker(acc, bearing):
        destination = travelDistance.destination(point=start, bearing=bearing)
        distancePoint = distance.distance(
            Point(fromA['lat'], fromA['lng']),
            Point(destination.latitude, destination.longitude)
        ).km
        if (distancePoint > acc['distance']):
            return { 'bearing': bearing, 'distance': distancePoint }
        return acc
    r = reduce(worker, [0, 45, 90, 135, 180, 225, 270, 315], { 'bearing': -1, 'distance': -1 })
    return r['bearing']

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

houseSmall = [     [0, -2],
         [-1, -1], [0, -1], [1, -1],
         [-1, 0],  [0, 0],  [1, 0],
         ]

houseBig = [                 [0, -2],
                   [-1, -1], [0, -1], [1, -1],
         [-2, 0],  [-1, 0],  [0, 0],  [1, 0],  [2, 0],
         [-2, 1], [-1, 1],           [1, 1],   [2, 1],
         [-2, 2], [-1, 2],           [1, 2],   [2, 2],
         ]

def getSpritePixels(xy, rgb, sprite):
    def spriteMapper(xy, rgb, spriteCell):
        return {'x': xy['x'] + spriteCell[0], 'y': xy['y'] + spriteCell[1], 'r': rgb['r'], 'g': rgb['g'], 'b': rgb['b']}
    p = partial(spriteMapper, xy, rgb)
    return map(p, sprite)

def drawSpritePixels(unicornhathdspritePixels):
    print(unicornhathdspritePixels)
    for p in unicornhathdspritePixels:
        print(p)
        unicornhathd.set_pixel(p['x'], p['y'], p['r'], p['g'], p['b'])

for n in names:
    data = list(getDataFor(n, lines))
    speed = reduce(getSmoothedSpeedMaths, data, {'weight': 0, 'weightedSpeed': 0})['speed']
    travelAngle = getRoughAngle(data[-2], data[-1])
    drawAngle = getRoughAngle(home, data[-1])
    print(n + ": " + "Speed:       " + str(speed))
    print(n + ": " + "travelAngle: " + str(travelAngle))
    print(n + ": " + "draAngle:    " + str(drawAngle))


    unicornhathd.clear()
    drawSpritePixels(getSpritePixels(
        {'x': 4, 'y': 4},
        {'r': 100, 'g': 100, 'b': 255},
        houseBig
    ))
    drawSpritePixels(getSpritePixels(
        {'x': 10, 'y': 10},
        {'r': 100, 'g': 100, 'b': 255},
        houseSmall
    ))
    unicornhathd.show()
    time.sleep(5)
