#!/usr/bin/env python3
from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, OUTPUT_D
from ev3dev2.sensor import INPUT_1, INPUT_2,INPUT_3
from ev3dev2.sensor.lego import TouchSensor, ColorSensor
from ev3dev2.led import Leds
from time import sleep, time



RTIME_90 = 1
RTIME_180 = 1.7
leds = Leds()

touch_sensor = TouchSensor(INPUT_1)
color_sensor1 = ColorSensor(INPUT_2)
color_sensor2 = ColorSensor(INPUT_3)
left_wheel = LargeMotor(OUTPUT_A)
right_wheel = LargeMotor(OUTPUT_B)
# lift = MediumMotor(OUTPUT_C)

# leds.set_color("RIGHT", "GREEN")

def get_color(sensor):
    r, g, b = sensor.rgb
    if r > 100 and g > 100 and b > 100:
        return 'WHITE'
    elif r < 70 and g < 120 and b > 100: #45, 90, 200
        # print("\n Blue r: {}, g: {}, b: {}".format(r, g, b))
        return 'BLUE'
    elif r > 50 and g < 40 and b < 40:
        # print("\n Green r: {}, g: {}, b: {}".format(r, g, b))
        return 'GREN'
    elif r < 100 and g < 100 and b < 100:
        return 'BLACK'
    else:
        return 'WHITE'



# def rot_90(speed, left=True):
#     if left:
#         left_wheel.on(speed*2)
#         right_wheel.on(-speed)
#         sleep(RTIME_90)
#     else:
#         left_wheel.on(-speed)
#         right_wheel.on(speed*2)
#         sleep(RTIME_90)
#         left_wheel.stop()
#         right_wheel.stop()

# def rot_180(speed):
#     left_wheel.on(speed*2)
#     right_wheel.on(-speed*2)
#     sleep(RTIME_180)

# def forward(speed):
#     left_wheel.on(speed)
#     right_wheel.on(speed)

# def backward(speed):
#     left_wheel.on(-speed)
#     right_wheel.on(-speed)

# def turn2(speed, direction):
#     if direction >0:
#         left_wheel.on(speed * direction)
#         right_wheel.on(speed)
#         # right_wheel.on(speed * -direction)
#     else:
#         direction = -direction
#         # left_wheel.on(speed * direction)
#         left_wheel.on(speed) 
#         right_wheel.on(speed* direction)

# def turn(speed,direction):
#     w1, w2 =left_wheel,right_wheel
#     if direction < 0:
#         w1 = right_wheel
#         w2 = left_wheel
#         direction = -direction
#     if direction>0.2:
#         w1.on(speed)
#         w2.on(speed)

# def rot_90(speed, left=True):
#     if left:
#         left_wheel.on(speed*2)
#         right_wheel.on(-speed)
#         sleep(RTIME_90)
#     else:
#         left_wheel.on(-speed)
#         right_wheel.on(speed*2)
#         sleep(RTIME_90)
#         left_wheel.stop()
#         right_wheel.stop()

# def rot_180(speed):
#     left_wheel.on(speed*2)
#     right_wheel.on(-speed*2)
#     sleep(RTIME_180)

# def forward(speed):
#     left_wheel.on(speed)
#     right_wheel.on(speed)

# def backward(speed):
#     left_wheel.on(-speed)
#     right_wheel.on(-speed)

# def turn2(speed, direction):
#     if direction >0:
#         left_wheel.on(speed * direction)
#         right_wheel.on(speed)
#         # right_wheel.on(speed * -direction)
#     else:
#         direction = -direction
#         # left_wheel.on(speed * direction)
#         left_wheel.on(speed) 
#         right_wheel.on(speed* direction)

# def turn(speed,direction):
#     w1, w2 =left_wheel,right_wheel
#     if direction < 0:
#         w1 = right_wheel
#         w2 = left_wheel
#         direction = -direction
#     if direction>0.2:
#         w1.on(speed)
#         w2.on(speed)
#     else:
#         w1.on(speed * direction)
#         w2.on(speed)
#     else:
#         w1.on(speed * direction)
#         w2.on(speed)

def go(speed, direction):
    w1, w2 =left_wheel,right_wheel
    if speed == 0:
        w1.stop()
        w2.stop()
    elif direction < 0:
        w1 = right_wheel
        w2 = left_wheel
        direction = -direction
    elif direction < 1:
        w1.on(speed - speed * direction)
        w2.on(speed + speed * direction)
    else:
        w1.on(-speed * direction)
        w2.on(+ speed * direction)


try:
    temp_time = time()

    speed = 10
    direction = 0
    while True:
        # color = get_color(color_sensor1)
        colorL = get_color(color_sensor1)
        colorR = get_color(color_sensor2)

        # full throttle
        if colorL == colorR == 'WHITE':
            speed = 10
            direction = 0
        elif colorL == colorR == "BLACK":
            speed = 5
            direction = 1
        elif colorL == "BLACK":
            speed = 10
            direction = max(1, direction+0.1)
        elif colorL == colorR == "BLUE":
            speed = 0
            direction = 0
            go(speed, direction)
            sleep(1)
            
        go(speed, direction)

        print("left/right :" + colorL + '/' + colorR + " timeD:" + str(time() - temp_time))
        # "RGB" + str(color_sensor1.rgb) + 
        

        # direction = color_sensor1.reflected_light_intensity - 50
        # direction*=0.01
        # direction = max(-1,min(direction,1))

        #leds.set_color("RIGHT", color)
        # print("1")
        # + " direction: " + str(direction)
        # turn(10,direction)
        # if color == 'BLACK':
        #     turn(5,0.5)
        # else:
        #     turn(5,-0.5)
        
        temp_time = time()

        if touch_sensor.is_pressed:
            left_wheel.stop()
            right_wheel.stop()
            raise KeyboardInterrupt
except KeyboardInterrupt:
    left_wheel.stop()
    right_wheel.stop()
except BaseException as e:
    left_wheel.stop()
    right_wheel.stop()
    print("Błąd b :", e)
except Exception as e:
    left_wheel.stop()
    right_wheel.stop()
    print("Błąd:", e)

