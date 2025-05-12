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
            print("[MOTOR] on:")

        def stop(self):
            print("[MOTOR] stop")

        def on_for_degrees(self, speed, degrees):
            print("[MOTOR] on_for_degrees:")

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
            self.checked +=1
            return True

    class MockSound():
        def __init__(self, *args, **kwargs):
            pass
        def play_tone(self, freq, duration):
            print("[SOUND] Playing tone: Hz fors")

    class MockLeds():
        def __init__(self, *args, **kwargs):
            pass
        def set_color(self, side, color):
            print("[LED] ")

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
# Hardcoded parameters for maximum speed and minimal dependencies
SOURCE_COLOR = 'RED'
TARGET_COLOR = 'GREEN'
LOST_LINE_THRESHOLD = 80
BASE_SPEED = 10
TURN_GAIN = 7
TURN_DURATION = 1.2
LIFT_UP_SPEED = 10
LIFT_DOWN_SPEED = -10
LIFT_DEGREES = 200
LIFT_PAUSE = 0.5
RECOVERY_OSCILLATIONS = 3
RECOVERY_OSCILLATE_DURATION = 0.2
RECOVERY_BACKUP_DURATION = 0.1
RECOVERY_ITERATIONS= 20 #LOST_LINE_THRESHOLD

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
    global touch_sensor, color_sensor1, color_sensor2, left_wheel, right_wheel, lift, sound, leds
    touch_sensor = TouchSensor(INPUT_1)
    color_sensor2 = ColorSensor(INPUT_2)
    color_sensor1 = ColorSensor(INPUT_3)
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
def get_color2(sensor):
    """Return color string based on RGB values from a ColorSensor."""
    r, g, b = sensor.rgb
    if b > 100:
        return 'WHITE'
    if g > 100:
        return 'GREEN'
    if r < 100:
        return 'BLACK'
    if r > 120:
        return 'RED'
    return 'WHITE'

def get_color(sensor):
    """Return color string based on RGB values from a ColorSensor."""
    try:
        r, g, b = sensor.rgb
    except Exception as e:
        logger.error('Sensor read error: ', e)
        set_led_status('error')
        return 'UNKNOWN'
    if r > 100 and g > 100 and b > 100:
        return 'WHITE'
    # if r < 70 and g < 120 and b > 100:
    #     return 'BLUE'
    if r < 50 and g > 100 and b < 40:
        return 'GREEN'
    if r < 100 and g < 100 and b < 100:
        return 'BLACK'
    if r > 120 and g < 60 and b < 60:
        return 'RED'
    # if r > 120 and g > 100 and b < 60:
    #     return 'YELLOW'
    return 'WHITE'

# === ACTIONS ===
def pick_up(direction):
    """Raise the lift to pick up an object."""
    logger.info('Picking up object')
    set_led_status('pickup')
    
    lcol, rcol = get_colors()
    print("starting pickup")
    print(lcol, rcol)
    if lcol == SOURCE_COLOR == rcol:
        go(BASE_SPEED/2,-BASE_SPEED/2)
        sleep(0.7)
        lcol, rcol = get_colors()
        print(lcol, rcol)
        while get_colors()[1] != "BLACK":
            print(lcol, rcol)
            lcol, rcol = get_colors()
            pass
    if lcol == SOURCE_COLOR and rcol != SOURCE_COLOR:
        go(-BASE_SPEED/2,BASE_SPEED/2)
        sleep(0.7)
        lcol, rcol = get_colors()
        print(lcol, rcol)
        while get_colors()[0] != "BLACK":
            print(lcol, rcol)
            lcol, rcol = get_colors()
            pass
    if rcol == SOURCE_COLOR and lcol != SOURCE_COLOR:
        go(BASE_SPEED/2,-BASE_SPEED/2)
        sleep(0.7)
        lcol, rcol = get_colors()
        print(lcol, rcol)
        while get_colors()[1] != "BLACK":
            print(lcol, rcol)
            lcol, rcol = get_colors()
            pass
    print("route found")
    go(BASE_SPEED,BASE_SPEED)
    sleep(2)
    go(0,0)
    state = STATE_TO_SOURCE
    print("starting going to box")
    # while(state == STATE_TO_SOURCE):
    #     state = run_transport_cycle(state)
    

def drive_to_source():
    lcol, rcol = get_colors()
    print("adjusting before box")
    set_led_status("working")
    while not (lcol == SOURCE_COLOR == rcol):
        lcol, rcol = get_colors()
        print(lcol, rcol)
        if lcol == SOURCE_COLOR and rcol != SOURCE_COLOR:
            go(-BASE_SPEED/2,0)
        if rcol == SOURCE_COLOR and lcol != SOURCE_COLOR:
            go(0,-BASE_SPEED/2)
        if lcol == SOURCE_COLOR == rcol:
            go(BASE_SPEED/2,BASE_SPEED/2)
    go(BASE_SPEED/2,BASE_SPEED/2)
    sleep(2)
    go(0,0)
    print("picking up box")
    lift.on_for_degrees(LIFT_UP_SPEED, LIFT_DEGREES)
    sleep(LIFT_PAUSE)
    pass

def drop():
    """Lower the lift to drop an object."""
    logger.info('Dropping object')
    set_led_status('drop')
    lift.on_for_degrees(LIFT_DOWN_SPEED, LIFT_DEGREES)
    sleep(LIFT_PAUSE)

def turn_around(base_speed=BASE_SPEED, duration=TURN_DURATION):
    """Turn the robot 180 degrees in place."""
    logger.info('Turning around')
    set_led_status('working')
    left_wheel.on(base_speed)
    right_wheel.on(-base_speed)
    sleep(duration)
    stop_all_motors()
    # sleep(0.2)
    set_led_status('ready')

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
    lcol = get_color(color_sensor1)
    rcol = get_color(color_sensor2)
    return lcol, rcol

# === BUTTON HANDLING ===
def wait_for_button_press(prompt='Waiting for button press to start...'):
    """Block until the touch sensor is pressed and released."""
    print(prompt)
    logger.info('Awaiting button press: %s', prompt)
    set_led_status('ready')
    while not touch_sensor.is_pressed:
        sleep(0.05)
    while touch_sensor.is_pressed:
        sleep(0.05)
    logger.info('Button pressed')
    set_led_status('working')

# === LOST LINE RECOVERY ===
def lost_line_recovery(base_speed=BASE_SPEED):
    """Attempt to recover the line if both sensors are white for a threshold period."""
    logger.warning('Lost line detected, attempting recovery')
    set_led_status('lost') 
    stop_all_motors()
    for i in range(RECOVERY_ITERATIONS):
        left_wheel.on(-base_speed)
        right_wheel.on(-base_speed)
        sleep(RECOVERY_BACKUP_DURATION)
        lcol = get_color(color_sensor1)
        rcol = get_color(color_sensor2)
        if lcol == 'BLACK' or rcol == 'BLACK':
            print('Line recovered, continuing previous action...')
            return True
    print('Line not found, waiting for button to retry...')
    return False


def go(left, right):
    left_wheel.on(left)
    right_wheel.on(right)

# === MAIN TRANSPORT ROUTINE WITH STATE MACHINE ===
def run_transport_cycle(state):
    """Run a single transport cycle using a state machine."""
    lost_counter = 0
    turn_reduction=0
    last_state=1
    while True:
        # print("Lost line counter: ", lost_counter)
        lcol, rcol = get_colors()
        print(lcol, rcol)
        if 'WHITE' == rcol:
            if lcol == 'WHITE':
                go(BASE_SPEED, BASE_SPEED)
                # lost_counter += 1
                if lost_counter > LOST_LINE_THRESHOLD:
                    lost_line_recovery()
                    # lost_counter = 0
                continue
            elif(lcol == 'BLACK'):
                go(-BASE_SPEED,-BASE_SPEED*0.7)
                sleep(0.05)
                go(BASE_SPEED, -BASE_SPEED)
                turn_reduction -= last_state
                last_state = 1
                # lost_counter = 0
                continue
        if 'WHITE' == lcol:
            if rcol == 'WHITE':
                go(BASE_SPEED, BASE_SPEED)
                lost_counter += 1
                if lost_counter > LOST_LINE_THRESHOLD:
                    lost_line_recovery()
                    lost_counter = 0
                continue
            elif(rcol == 'BLACK'):
                go(-BASE_SPEED*0.7,-BASE_SPEED)
                sleep(0.05)
                go(-BASE_SPEED, BASE_SPEED)
                last_state = -1
                lost_counter = 0
                continue
            
        if state == STATE_TO_SOURCE and (lcol == SOURCE_COLOR or rcol == SOURCE_COLOR):
            stop_all_motors()
            pick_up(lcol == SOURCE_COLOR)
            state = STATE_PICKING_UP
            # turn_around()
            break
        elif state == STATE_PICKING_UP and (lcol == SOURCE_COLOR or rcol == SOURCE_COLOR):
            stop_all_motors()
            drive_to_source()
            state = STATE_TO_TARGET
            turn_around()
            break
        elif state ==  STATE_TO_TARGET and lcol == TARGET_COLOR or rcol == TARGET_COLOR:
            stop_all_motors()
            drop()
            state = STATE_TO_SOURCE
            turn_around()
            break
        # elif lcol == 'BLACK' and rcol == 'BLACK':
        go(BASE_SPEED*last_state,-BASE_SPEED*last_state)
            # left_wheel.on(BASE_SPEED)
            # right_wheel.on(BASE_SPEED)
            # sleep(0.25)
        if touch_sensor.is_pressed:
            stop_all_motors()
            logger.info('Button pressed, stopping')
            sleep(0.5)
            while(not touch_sensor.is_pressed):
                pass
            return STATE_IDLE
    return state

# === MAIN ENTRY POINT ===
def main():
    """Main program loop handling repeated transport cycles and safe shutdown."""
    init_devices()
    # sound.play_tone(220, 0.4)
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
        print('KeyboardInterrupt, motors stopped')
    # except BaseException as e:
    #     stop_all_motors()
    #     print('BaseExpection, motors stopped.')
    #     print(e)
    #     logger.info('Program interrupted, motors stopped')
    except Exception as e:
        stop_all_motors()
        print('Unexpected error:', e)
        logger.exception('Unexpected error: ', e)
        set_led_status('error')
    finally:
        stop_all_motors()
        set_led_status('error')

if __name__ == '__main__':
    main()
