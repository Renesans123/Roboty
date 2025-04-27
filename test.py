#!/usr/bin/env python3
from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, OUTPUT_D
from ev3dev2.sensor import INPUT_1, INPUT_2,INPUT_3
from ev3dev2.sensor.lego import TouchSensor, ColorSensor
from ev3dev2.led import Leds
from time import sleep, time


def dist(a,b):
    ret = 0
    for i in range(len(a)):
        ret += (a[i]-b[i]) * (a[i]-b[i])
    return ret

RTIME_90 = 1
RTIME_180 = 1.7

ts = TouchSensor(INPUT_1)
leds = Leds()
sensor1 = ColorSensor(INPUT_2)
sensor2 = ColorSensor(INPUT_3)
left_wheel = LargeMotor(OUTPUT_A)
right_wheel = LargeMotor(OUTPUT_B)

# leds.set_color("RIGHT", "GREEN")

# def get_color(sensor):
#     r, g, b = sensor.rgb
#     if r > 100 and g > 100 and b > 100:
#         return 'White'
#     elif r < 40 and g < 80 and b > 80: #45, 90, 200
#         # print("\n Blue r: {}, g: {}, b: {}".format(r, g, b))
#         return 'Blue'
#     elif r > 50 and g < 40 and b < 40:
#         # print("\n Green r: {}, g: {}, b: {}".format(r, g, b))
#         return 'Green'
#     elif r < 100 and g < 100 and b < 100:
#         return 'Black'
#     elif r < 120 and g < 120 and b < 120:
#         return 'Gray'
#     else:
#         return 'White'

def get_color(sensor):
    # sensor.rgb
    col = {'WHITE':[255,255,255],'BLACK':[35,35,30],'BLUE':[45, 90, 190], 'GREEN':[40, 115, 60],'YELLOW':[255, 175, 60],'RED':[255, 40, 30]}
    min_d = 9999999999
    
    for c in ['WHITE','BLACK','BLUE', 'GREEN','YELLOW','RED']:
        d = dist(col[c],sensor.rgb)
        min_d = min(d,min_d)
        col[d] = c
    return col[min_d]
    
#green 40 115 60
#yellow 255 175 60
#red 255 40 30


def rot_90(speed, left=True):
    if left:
        left_wheel.on(speed*2)
        right_wheel.on(-speed)
        sleep(RTIME_90)
    else:
        left_wheel.on(-speed)
        right_wheel.on(speed*2)
        sleep(RTIME_90)
        left_wheel.stop()
        right_wheel.stop()

def rot_180(speed):
    left_wheel.on(speed*2)
    right_wheel.on(-speed*2)
    sleep(RTIME_180)

def forward(speed):
    left_wheel.on(speed)
    right_wheel.on(speed)

def backward(speed):
    left_wheel.on(-speed)
    right_wheel.on(-speed)

def turn(speed, dir):
    if dir >0:
        left_wheel.on(speed * dir)
        right_wheel.on(speed)
    else:
        left_wheel.on(speed * -dir) 
        right_wheel.on(speed)

try:
    temp_time = time()

    while True:
        color = get_color(sensor1)
        if color == 'BLUE':
            # leds.brightness(0)
            pass
        elif color == 'WHITE':
            # leds.brightness(99)
            pass
        else:
            leds.set_color("RIGHT", color)
        # print("1")
        print("RGB" + str(sensor1.rgb) + "col:" 
        + color 
        + "    timeD:" + str(time() - temp_time))
        dir = sensor1.reflected_light_intensity - 35
        turn(15,dir*2)
        
        temp_time = time()

        if ts.is_pressed:
            left_wheel.stop()
            right_wheel.stop()
            raise KeyboardInterrupt
except KeyboardInterrupt:
    left_wheel.stop()
    right_wheel.stop()
except Exception as e:
    left_wheel.stop()
    right_wheel.stop()
    print("Błąd:", e)

