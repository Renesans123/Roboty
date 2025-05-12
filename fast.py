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
CENTERING_TURN_DURATION = 0.1     # seconds for the brief centering counter-turn
CORRECTIVE_TURN_STEP_DURATION = 0.02 # duration of each small step in corrective turn
PRE_TURN_STOP_DURATION = 0.05       # duration to stop before initiating a corrective turn
MAIN_LOOP_STEP_DURATION = 0.01      # small sleep in the main transport loop
K_CORRECTION_TURN = 1.0           # coefficient for speed of the backward/slower wheel in corrective static turn (e.g. 1.0 for equal opposite speed)
K_CENTERING_TURN = 0.7            # coefficient for speed during centering maneuver (e.g. 0.7 for 70% of BASE_SPEED)

# === STATE MACHINE DEFINITIONS ===
STATE_IDLE = 0
STATE_TO_SOURCE = 1
STATE_TO_TARGET = 2
STATE_DELIVERED = 3

# === LOGGING SETUP ===
logging.basicConfig(level=logging.INFO,
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

    lcol, rcol = get_colors() # Get current colors for initial check

    # Fine-tune alignment over SOURCE_COLOR before picking up
    if lcol == SOURCE_COLOR and rcol != SOURCE_COLOR:
        logger.info("Aligning: {} on left. Turning slightly right.".format(SOURCE_COLOR))
        go(-BASE_SPEED / 2, BASE_SPEED / 2)
        sleep(0.1) # Brief turn
        # Loop until left sensor is back on black (edge of line)
        # This implies the source color is a patch on one side of the line.
        # Consider if this logic needs to be more robust or tied to finding the line's center.
        temp_lcol = get_color(color_sensor1)
        while temp_lcol != 'BLACK':
            logger.debug("Aligning (L on {}): Waiting for left sensor to see BLACK. Currently: {}".format(SOURCE_COLOR, temp_lcol))
            sleep(0.05)
            temp_lcol = get_color(color_sensor1)
            if touch_sensor.is_pressed: return # Allow interruption
        logger.info("Alignment: Left sensor now on BLACK.")

    elif rcol == SOURCE_COLOR and lcol != SOURCE_COLOR: # Corrected this condition
        logger.info("Aligning: {} on right. Turning slightly left.".format(SOURCE_COLOR))
        go(BASE_SPEED / 2, -BASE_SPEED / 2)
        sleep(0.1) # Brief turn
        # Loop until right sensor is back on black (edge of line)
        temp_rcol = get_color(color_sensor2)
        while temp_rcol != 'BLACK':
            logger.debug("Aligning (R on {}): Waiting for right sensor to see BLACK. Currently: {}".format(SOURCE_COLOR, temp_rcol))
            sleep(0.05)
            temp_rcol = get_color(color_sensor2)
            if touch_sensor.is_pressed: return # Allow interruption
        logger.info("Alignment: Right sensor now on BLACK.")
    
    # If both are on source color, or after alignment, move forward slightly to ensure grasp
    # The original code had a complex re-entry to run_transport_cycle here. Removing it.
    # Assuming the run_transport_cycle got us close enough and the fine-tune above helped.
    logger.info("Moving forward slightly before lift.")
    go(BASE_SPEED, BASE_SPEED)
    sleep(0.5) # Adjust duration as needed
    go(0,0) # Stop before lifting
    
    lift.on_for_degrees(LIFT_UP_SPEED, LIFT_DEGREES)
    sleep(LIFT_PAUSE)
    logger.info("Object picked up.")

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
    """Run a single transport cycle using a two-sensor advanced line follower."""
    lost_counter = 0

    while True:
        lcol, rcol = get_colors()
        # Basic logging for current sensor readings and state
        # Consider changing to logger.debug for less verbose output during normal operation
        # print("L: {}, R: {}, Lost: {}, State: {}".format(lcol, rcol, lost_counter, state))
        logger.info("L: {}, R: {}, Lost: {}, State: {}".format(lcol, rcol, lost_counter, state))

        # --- Colour-based state transitions for pick-up/drop-off ---
        if state == STATE_TO_SOURCE and (lcol == SOURCE_COLOR or rcol == SOURCE_COLOR):
            logger.info("Source color {} detected.".format(SOURCE_COLOR))
            stop_all_motors()
            pick_up()
            state = STATE_TO_TARGET
            turn_around()
            break 
        # Added check for STATE_TO_TARGET for clarity, though TARGET_COLOR implies it
        if state == STATE_TO_TARGET and (lcol == TARGET_COLOR or rcol == TARGET_COLOR):
            logger.info("Target color {} detected.".format(TARGET_COLOR))
            stop_all_motors()
            drop()
            state = STATE_TO_SOURCE
            turn_around()
            break

        # --- Advanced Line Following Logic ---
        if lcol == 'BLACK' and rcol == 'WHITE':  # Line under left sensor, veer right
            logger.info("Left sensor on BLACK, right on WHITE. Initiating corrective static RIGHT turn.")
            stop_all_motors()
            sleep(PRE_TURN_STOP_DURATION)
            while lcol == 'BLACK' and rcol == 'WHITE':
                go(-K_CORRECTION_TURN * BASE_SPEED, BASE_SPEED)  # Left wheel backward, Right wheel forward
                sleep(CORRECTIVE_TURN_STEP_DURATION)
                lcol_new, rcol_new = get_colors()
                if touch_sensor.is_pressed:
                    stop_all_motors()
                    logger.info('Button pressed during corrective RIGHT turn, stopping.')
                    return STATE_IDLE
                if lcol_new != lcol or rcol_new != rcol: # Only update if changed to avoid spamming logs
                    lcol, rcol = lcol_new, rcol_new
                    logger.info("Corrective RIGHT turn: L:{}, R:{}".format(lcol, rcol))
                if lcol == 'WHITE': # Guiding sensor lost the line
                    logger.warning("Left (guiding) sensor lost BLACK during corrective RIGHT turn.")
                    break # Exit corrective turn loop
            stop_all_motors() # Stop after corrective turn loop

            if lcol == 'BLACK' and rcol == 'BLACK': # Check if both sensors are now on black
                logger.info("Both sensors on BLACK after corrective RIGHT turn. Performing centering LEFT turn.")
                go(K_CENTERING_TURN * BASE_SPEED, -K_CENTERING_TURN * BASE_SPEED) # Centering: Left fwd, Right bwd
                sleep(CENTERING_TURN_DURATION)
                stop_all_motors()
            lost_counter = 0 # Reset lost counter after a correction attempt

        elif rcol == 'BLACK' and lcol == 'WHITE':  # Line under right sensor, veer left
            logger.info("Right sensor on BLACK, left on WHITE. Initiating corrective static LEFT turn.")
            stop_all_motors()
            sleep(PRE_TURN_STOP_DURATION)
            while rcol == 'BLACK' and lcol == 'WHITE':
                go(BASE_SPEED, -K_CORRECTION_TURN * BASE_SPEED)  # Left wheel forward, Right wheel backward
                sleep(CORRECTIVE_TURN_STEP_DURATION)
                lcol_new, rcol_new = get_colors()
                if touch_sensor.is_pressed:
                    stop_all_motors()
                    logger.info('Button pressed during corrective LEFT turn, stopping.')
                    return STATE_IDLE
                if lcol_new != lcol or rcol_new != rcol:
                    lcol, rcol = lcol_new, rcol_new
                    logger.info("Corrective LEFT turn: L:{}, R:{}".format(lcol, rcol))
                if rcol == 'WHITE': # Guiding sensor lost the line
                    logger.warning("Right (guiding) sensor lost BLACK during corrective LEFT turn.")
                    break # Exit corrective turn loop
            stop_all_motors() # Stop after corrective turn loop

            if lcol == 'BLACK' and rcol == 'BLACK': # Check if both sensors are now on black
                logger.info("Both sensors on BLACK after corrective LEFT turn. Performing centering RIGHT turn.")
                go(-K_CENTERING_TURN * BASE_SPEED, K_CENTERING_TURN * BASE_SPEED) # Centering: Left bwd, Right fwd
                sleep(CENTERING_TURN_DURATION)
                stop_all_motors()
            lost_counter = 0 # Reset lost counter after a correction attempt

        elif lcol == 'BLACK' and rcol == 'BLACK':  # Both sensors on the line
            logger.info("Both sensors on BLACK. Driving straight.")
            go(BASE_SPEED, BASE_SPEED)
            lost_counter = 0
        
        else:  # Both sensors on WHITE or other unexpected combination
            logger.info("Sensors not on a clear line (L:{}, R:{}). Driving straight, lost_counter = {}.".format(lcol, rcol, lost_counter + 1))
            go(BASE_SPEED, BASE_SPEED)
            lost_counter += 1
            if lost_counter > LOST_LINE_THRESHOLD:
                logger.warning("Lost line threshold ({}) reached.".format(LOST_LINE_THRESHOLD))
                recovered = lost_line_recovery() # lost_line_recovery handles its own logging
                lost_counter = 0  # Reset counter regardless of recovery success
                if not recovered:
                    logger.error("Lost line recovery FAILED. Returning to IDLE state.")
                    return STATE_IDLE
                else:
                    logger.info("Lost line recovery SUCCEEDED.")

        # Main loop emergency stop check
        if touch_sensor.is_pressed:
            stop_all_motors()
            logger.info('Button pressed in main loop, stopping.')
            return STATE_IDLE
        
        sleep(MAIN_LOOP_STEP_DURATION) # Brief pause for stability and to reduce CPU load

    return state # Should be unreachable due to breaks or returns in the loop

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
