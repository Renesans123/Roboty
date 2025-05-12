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
            print("!!!!!!  hardware not detected !!!!!! ")
            print("!!!!!!  fallback to simulate mock HW !!!!!! ")
        def on(self, speed, brake=False, block=False):
            print("[MOTOR] on: {}".format(speed))

        def stop(self):
            print("[MOTOR] stop")

        def on_for_degrees(self, speed, degrees):
            print("[MOTOR] on_for_degrees: {}, {}".format(speed, degrees))

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


    class MockLeds():
        def __init__(self, *args, **kwargs):
            pass
        def set_color(self, side, color):
            print("[LED] {}: {}".format(side, color))

    # Replace hardware classes with mocks
    TouchSensor = MockTouchSensor
    ColorSensor = MockColorSensor
    LargeMotor = MediumMotor = MockMotor
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
RECOVERY_OSCILLATE_DURATION = 0.2
RECOVERY_BACKUP_DURATION = 0.1
RECOVERY_ITERATIONS = 20 #LOST_LINE_THRESHOLD

# New constants for advanced line following
K_CORRECTION_TURN = 0.18           # coefficient for speed of the backward/slower wheel in corrective static turn (e.g. 1.0 for equal opposite speed)
CENTERING_TURN_DURATION = 2     # seconds for the brief centering counter-turn

# === STATE MACHINE DEFINITIONS ===
STATE_IDLE = 0
STATE_TO_SOURCE = 1
STATE_TO_TARGET = 2
STATE_DELIVERED = 3

# === LOGGING SETUP ===
LOG_FILE = 'robot.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# logger.basicConfig(level=logging.DEBUG)


# center robot over line
def static_turn(right: bool) -> None:
    if right:
        right_wheel.on(BASE_SPEED * K_CORRECTION_TURN)
        left_wheel.on(-BASE_SPEED)
        while get_color(color_sensor_l) != 'BLACK':
            pass
        # Center: both wheels opposite for a short moment
        right_wheel.on(BASE_SPEED)
        left_wheel.on(-BASE_SPEED)
    else:
        left_wheel.on(BASE_SPEED * K_CORRECTION_TURN)
        right_wheel.on(-BASE_SPEED)
        while get_color(color_sensor_r) != 'BLACK':
            pass
        # Center: both wheels opposite for a short moment
        left_wheel.on(BASE_SPEED)
        right_wheel.on(-BASE_SPEED)
    sleep(CENTERING_TURN_DURATION)
    left_wheel.stop()
    right_wheel.stop()


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
    if b>100:
        return 'WHITE'
    if g > 100:
        return 'GREEN'
    if r < 100:
        return 'BLACK'
    if r > 120:
        return 'RED'
    return 'WHITE'

# === ACTIONS ===
def pick_up():
    """Raise the lift to pick up an object."""
    logger.info('Picking up object')
    set_led_status('pickup')

    lcol, rcol = get_colors()

    if lcol == SOURCE_COLOR and rcol != SOURCE_COLOR:
        go(-BASE_SPEED/2,BASE_SPEED/2)
        sleep(0.1)
        while get_color()[0] != "BLACK":
            pass
    if rcol == SOURCE_COLOR and lcol == SOURCE_COLOR:
        go(BASE_SPEED/2,-BASE_SPEED/2)
        sleep(0.1)
        while get_color()[1] != "BLACK":
            pass
    go(BASE_SPEED,BASE_SPEED)
    sleep(0.5)
    go(0,0)
    state = STATE_TO_SOURCE
    while(state == STATE_TO_SOURCE):
        state = run_transport_cycle(state)
    
    lift.on_for_degrees(LIFT_UP_SPEED, LIFT_DEGREES)
    sleep(LIFT_PAUSE)

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
    # sleep(duration)
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
    lcol = get_color(color_sensor_l)
    rcol = get_color(color_sensor_r)
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
        lcol = get_color(color_sensor_l)
        rcol = get_color(color_sensor_r)
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
    """Run a single transport cycle using a two-sensor bang-bang line follower."""
    lost_counter = 0

    while True:
        lcol, rcol = get_colors()

        # --- colour-based state transitions ---
        if state == STATE_TO_SOURCE and (lcol == SOURCE_COLOR or rcol == SOURCE_COLOR):
            stop_all_motors()
            pick_up()
            state = STATE_TO_TARGET
            turn_around()
            break
        if lcol == TARGET_COLOR or rcol == TARGET_COLOR:
            stop_all_motors()
            drop()
            state = STATE_TO_SOURCE
            turn_around()
            break

        # --- line following logic ---
        if lcol == 'BLACK' and rcol == 'BLACK':
            # centred on the line – drive straight
            go(BASE_SPEED, BASE_SPEED)
            lost_counter = 0
        elif lcol == 'BLACK':
            static_turn(right=False)
            lost_counter = 0
        elif rcol == 'BLACK':
            static_turn(right=True)
            lost_counter = 0
        else:
            # go straight
            go(BASE_SPEED, BASE_SPEED)
            lost_counter += 1
            if lost_counter > LOST_LINE_THRESHOLD:
                recovered = lost_line_recovery()
                lost_counter = 0
                if not recovered:
                    return STATE_IDLE

        # Emergency stop by touch sensor
        if touch_sensor.is_pressed:
            stop_all_motors()
            logger.info('Button pressed, stopping')
            return STATE_IDLE

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
            state = STATE_TO_SOURCE
    except KeyboardInterrupt:
        stop_all_motors()
        print('KeyboardInterrupt, motors stopped')
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




