#!/usr/bin/env python3
from time import time
try:
    from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C
    from ev3dev2.sensor import INPUT_1, INPUT_2, INPUT_3
    from ev3dev2.sensor.lego import TouchSensor, ColorSensor
    from ev3dev2.sound import Sound
    from ev3dev2.led import Leds
except Exception:
    class MockMotor():
        def __init__(self, *args, **kwargs):
            pass
        def on(self, speed, brake=False, block=False):
            pass
            #print("[MOTOR] on:")

        def stop(self):
            pass
            #print("[MOTOR] stop")

        def on_for_degrees(self, speed, degrees):
            pass
            #print("[MOTOR] on_for_degrees:")

    class MockColorSensor():
        def __init__(self, *args, **kwargs):
            pass
        @property
        def rgb(self):
            # Simulate RGB values that randomly match BLACK, WHITE, GREEN, etc.
            return [
                (30, 30, 30),  # BLACK
                (120, 120, 120),  # WHITE
                (40, 110, 30),  # GREEN
                (130, 50, 50),  # RED
                (200, 200, 200)  # BRIGHT WHITE
            ][int(time() * 1000) % 5]

    class MockTouchSensor():
        checked = 0
        def __init__(self, *args, **kwargs):
            pass
        @property
        def is_pressed(self):
            if self.checked  >= 2:
                return False
            self.checked += 1
            return True

    class MockSound():
        def __init__(self, *args, **kwargs):
            pass
        def play_tone(self, freq, duration):
            pass
            #print("[SOUND] Playing tone: Hz fors")

    class MockLeds():
        def __init__(self, *args, **kwargs):
            pass
        def set_color(self, side, color):
            pass
            #print("[LED] ")

    # Replace hardware classes with mocks
    TouchSensor = MockTouchSensor
    ColorSensor = MockColorSensor
    LargeMotor = MediumMotor = MockMotor
    Sound = MockSound
    Leds = MockLeds

    # Constants to avoid hardware errors
    INPUT_1 = INPUT_2 = INPUT_3 = None
    OUTPUT_A = OUTPUT_B = OUTPUT_C = None

import logging
from time import sleep

# === CONFIGURATION ===
SOURCE_COLOR = 'RED'
TARGET_COLOR = 'GREEN'
BASE_SPEED = 10
LIFT_UP_SPEED = 10
LIFT_DEGREES = 120


# === STATE MACHINE DEFINITIONS ===

STATE_IDLE = 0
STATE_TO_SOURCE = 1
STATE_PICKING_UP = 2
STATE_TO_TARGET = 3
STATE_DELIVERING = 4
STATE_DELIVERED = 5

# === LOGGING SETUP ===
LOG_FILE = 'robot.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# logger.basicConfig(level=logging.DEBUG)

# === DEVICE INITIALIZATION ===
def init_devices():
    """Initialize all motors, sensors, sound, and LEDs as global variables."""
    global touch_sensor, color_sensor_l, color_sensor_r, left_wheel, right_wheel, lift, sound, leds
    touch_sensor = TouchSensor(INPUT_1)
    color_sensor_r = ColorSensor(INPUT_2)
    color_sensor_l = ColorSensor(INPUT_3)
    left_wheel = LargeMotor(OUTPUT_A)
    right_wheel = LargeMotor(OUTPUT_B)
    lift = MediumMotor(OUTPUT_C)
    sound = Sound()
    leds = Leds()

# === LED FEEDBACK ===
def set_led_status(status):
    """Set LED color and pattern based on status string. Uses more distinct colors and patterns for clarity."""
    # Color map: (left_color, right_color)
    color_map = {
        'ready':    ('GREEN', 'GREEN'),         # Ready to start
        'lost':     ('ORANGE', 'ORANGE'),       # Lost line
        'error':    ('RED', 'RED'),             # Error state
        'working':  ('GREEN', 'AMBER'),         # Following line/working
        'pickup':   ('AMBER', 'AMBER'),          # Picking up object
        'drop':     ('AMBER', 'AMBER'),          # Dropping object
        'pause':    ('YELLOW', 'RED'),          # Paused
        'stopped':  ('RED', 'BLACK'),           # Stopped by user
        'default':  ('BLACK', 'BLACK'),         # All off
    }
    left, right = color_map.get(status, color_map['default'])
    leds.set_color('LEFT', left)
    leds.set_color('RIGHT', right)

# === COLOR DETECTION ===
def get_color(sensor):
    """Return color string based on RGB values from a ColorSensor."""
    r, g, b = sensor.rgb

    # #print(r,g,b)
    if b > 100:
        return 'WHITE'
    if r < 40 and g > 60 and b < 80:
        return 'GREEN'
    if r > 100 and g<60:
        return 'RED'
    if r < 100 and g<100 and b<100:
        return 'BLACK'
    return 'WHITE'

def go(left, right):
    left_wheel.on(left)
    right_wheel.on(right)
    # right_wheel.on_for_degrees(right, 25, block=False, brake=False)
    # left_wheel.on_for_degrees(left, 25, block=False, brake=False)

# === ACTIONS ===
def turn_to_pick_up(turn_right):
    """Raise the lift to pick up an object."""
    set_led_status('pickup')
    #print("starting pickup")

    if turn_right:
        turn(90)
    else:
        turn(-90)

    go(BASE_SPEED,BASE_SPEED)
    sleep(2)
    # go(0,0)
    #print("starting going to box")
    

def drive_to_source(target_color, lift_direction):
    lcol, rcol = get_colors()
    # #print("adjusting before box")
    set_led_status("working")

    right_wheel.on_for_degrees(BASE_SPEED, 100, block=False)
    left_wheel.on_for_degrees(BASE_SPEED, 100, block=True)
    #print("picking up box")
    lift.on_for_degrees(LIFT_UP_SPEED, LIFT_DEGREES * lift_direction)
    right_wheel.on_for_degrees(BASE_SPEED, -100, block=False)
    left_wheel.on_for_degrees(BASE_SPEED, -100, block=True)
    turn(180)
    # pass

# === MOTOR SAFETY ===
def stop_all_motors():
    """Stop all drive and lift motors."""
    logger.info('Stopping all motors')
    left_wheel.on(0, brake=False, block=False)
    right_wheel.on(0, brake=False, block=False)
    left_wheel.stop()
    right_wheel.stop()
    lift.on(0, brake=False, block=False)
    lift.stop()

# === LINE FOLLOWING ===
def get_colors() -> (str, str):
    """Perform one step of proportional line following. Returns detected colors."""
    lcol = get_color(color_sensor_l)
    rcol = get_color(color_sensor_r)
    return lcol, rcol

# === BUTTON HANDLING ===
def wait_for_button_press(prompt='Waiting for button press to start...'):
    """Block until the touch sensor is pressed and released."""
    #print(prompt)
    logger.info('Awaiting button press: %s', prompt)
    set_led_status('ready')
    while not touch_sensor.is_pressed:
        sleep(0.05)
    while touch_sensor.is_pressed:
        sleep(0.05)
    logger.info('Button pressed')
    set_led_status('working')



def turn(degrees):
    degrees <<= 1
    right_wheel.on_for_degrees(BASE_SPEED, degrees, block=False)
    left_wheel.on_for_degrees(BASE_SPEED, -degrees, block=True)


special_black = False
# === MAIN TRANSPORT ROUTINE WITH STATE MACHINE ===
def run_transport_cycle(state):
    """Run a single transport cycle using a state machine."""
    last_state=1
    global special_black
    while True:
        lcol, rcol = get_colors()
        if touch_sensor.is_pressed:
            stop_all_motors()
            logger.info('Button pressed, stopping')
            sleep(0.5)
            while(not touch_sensor.is_pressed):
                pass
            return STATE_IDLE
        if 'WHITE' == rcol:
            # !!!! reersed color sensors !!!
            if lcol == 'WHITE':
                go(BASE_SPEED, BASE_SPEED)
                continue
            elif(lcol == 'BLACK'):
                # right_wheel.on_for_degrees(BASE_SPEED>>1, -25, block=False)
                # left_wheel.on_for_degrees(BASE_SPEED, 30, block=True)
                right_wheel.on_for_degrees(BASE_SPEED, -10, block=True)
                

                last_state = 1
                continue
        if 'WHITE' == lcol:
   
            if(rcol == 'BLACK'):
                # left_wheel.on_for_degrees(BASE_SPEED>>1, -25, block=False)
                # right_wheel.on_for_degrees(BASE_SPEED, 30, block=True)

                left_wheel.on_for_degrees(BASE_SPEED, -10, block=True)
                # go(-BASE_SPEED, BASE_SPEED)
                last_state = -1
                continue
        if state == STATE_TO_SOURCE and (lcol == SOURCE_COLOR or rcol == SOURCE_COLOR):
            stop_all_motors()
            turn_to_pick_up(rcol == SOURCE_COLOR)
            state = STATE_PICKING_UP
            break
        elif state == STATE_PICKING_UP and (lcol == SOURCE_COLOR or rcol == SOURCE_COLOR):
            stop_all_motors()
            drive_to_source(target_color=SOURCE_COLOR, lift_direction=1)
            state = STATE_TO_TARGET
            special_black = time()
            break
        elif state ==  STATE_TO_TARGET and lcol == TARGET_COLOR or rcol == TARGET_COLOR:
            stop_all_motors()
            turn_to_pick_up(rcol == TARGET_COLOR)
            state = STATE_DELIVERING
            break
        elif state ==  STATE_DELIVERING and lcol == TARGET_COLOR or rcol == TARGET_COLOR:
            stop_all_motors()
            drive_to_source(target_color=TARGET_COLOR, lift_direction=-1)
            state = STATE_TO_SOURCE
            break

        # both BLACK, turn in previous dirction
        go(BASE_SPEED*last_state,-BASE_SPEED*last_state)
        # if special_black:
        #     if time()-special_black < 15:
        #         turn(90)
        #     special_black = False
        # else:
        #     go(BASE_SPEED,BASE_SPEED)
    return state

# === MAIN ENTRY POINT ===
def main():
    """Main program loop handling repeated transport cycles and safe shutdown."""
    init_devices()
    state = STATE_TO_SOURCE
    try:

        while True:
            wait_for_button_press()
            while state != STATE_IDLE:
                state = run_transport_cycle(state)
            # After button stop, go back to IDLE (wait for next press)
            state = STATE_TO_SOURCE
    except KeyboardInterrupt:
        stop_all_motors()
        #print('KeyboardInterrupt, motors stopped')
    except Exception as e:
        stop_all_motors()
        #print('Unexpected error:', e)
        logger.exception('Unexpected error: ', e)
        set_led_status('error')
    finally:
        stop_all_motors()
        set_led_status('error')

if __name__ == '__main__':
    main()




#green 20 75 50
#white 130 130 180
#yellow 160 130 40 
#red 120 20 15
#blue 20 50 120
#gray 140 135 200
#laczenie  100 110 180



# def get_color2(sensor):
#     """Return color string based on RGB values from a ColorSensor."""
#     try:
#         r, g, b = sensor.rgb
#     except Exception as e:
#         logger.error('Sensor read error: ', e)
#         set_led_status('error')
#         return 'UNKNOWN'
#     if r > 100 and g > 100 and b > 100:
#         return 'WHITE'
#     # if r < 70 and g < 120 and b > 100:
#     #     return 'BLUE'
#     if r < 50 and g > 100 and b < 40:
#         return 'GREEN'
#     if r < 100 and g < 100 and b < 100:
#         return 'BLACK'
#     if r > 120 and g < 60 and b < 60:
#         return 'RED'
#     # if r > 120 and g > 100 and b < 60:
#     #     return 'YELLOW'
#     return 'WHITE'
