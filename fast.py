#!/usr/bin/env python3
from time import time
try:
    from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B
    from ev3dev2.sensor import INPUT_1, INPUT_2, INPUT_3
    from ev3dev2.sensor.lego import TouchSensor, ColorSensor
    from ev3dev2.sound import Sound
    from ev3dev2.led import Leds
except Exception:
    print("Lib import error")
import logging
from time import sleep

# === CONFIGURATION ===
SOURCE_COLOR = 'GREEN'
TARGET_COLOR = 'RED'
BASE_SPEED = 12
# LIFT_UP_SPEED = 10
# LIFT_DEGREES = 120


# === STATE MACHINE DEFINITIONS ===

# STATE_IDLE = 0
# STATE_TO_SOURCE = 1
# STATE_PICKING_UP = 2
# STATE_TO_TARGET = 3
# STATE_DELIVERING = 4
# STATE_DELIVERED = 5

# # === LOGGING SETUP ===
LOG_FILE = 'robot.log'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# logger.basicConfig(level=logging.DEBUG)

# === DEVICE INITIALIZATION ===
def init_devices():
    """Initialize all motors, sensors, sound, and LEDs as global variables."""
    global touch_sensor, color_sensor_l, color_sensor_r, left_wheel, right_wheel, sound, leds
    touch_sensor = TouchSensor(INPUT_1)
    color_sensor_r = ColorSensor(INPUT_2)
    color_sensor_l = ColorSensor(INPUT_3)
    left_wheel = LargeMotor(OUTPUT_A)
    right_wheel = LargeMotor(OUTPUT_B)
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
    if r < 60 and g > 60 and b < 80:
        return 'GREEN'
    if r > 100 and g<60:
        return 'RED'
    if r < 100 and g<100 and b<100:
        return 'BLACK'
    return 'WHITE'

def get_color2(sensor):
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

def go(left, right):
    left_wheel.on(left)
    right_wheel.on(right)
    # right_wheel.on_for_degrees(right, 25, block=False, brake=False)
    # left_wheel.on_for_degrees(left, 25, block=False, brake=False)

# === MOTOR SAFETY ===
def stop_all_motors():
    """Stop all drive and lift motors."""
    logger.info('Stopping all motors')
    left_wheel.on(0, brake=False, block=False)
    right_wheel.on(0, brake=False, block=False)
    left_wheel.stop()
    right_wheel.stop()
    # lift.on(0, brake=False, block=False)
    # lift.stop()

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


BOOST_RATIO = 2
MAX_SPEED = 20

# === MAIN TRANSPORT ROUTINE WITH STATE MACHINE ===
def run_transport_cycle(state):
    """Run a single transport cycle using a state machine."""
    memory_of_black= [10,10]
    prev_states = [None, None, None]
    global special_black
    while True:
        lcol, rcol = get_colors()
        
        # if prev_states != [lcol, rcol, state]:
        #     prev_states = [lcol, rcol, state]
        #     print(lcol, rcol, state)
        #     print(color_sensor_l.rgb,color_sensor_r.rgb)
        if touch_sensor.is_pressed:
            stop_all_motors()
            # logger.info('Button pressed, stopping')
            sleep(0.5)
            while(not touch_sensor.is_pressed):
                pass
            return 0
        elif 'WHITE' == rcol:
            # !!!! reersed color sensors !!!
            if lcol == 'WHITE':
                # go(8, 8)
                go(BASE_SPEED,BASE_SPEED)
                # continue
            elif(lcol == 'BLACK'):
                if memory_of_black[1] < 5:
                    right_wheel.on_for_degrees(BASE_SPEED, 20, block=False)
                    left_wheel.on_for_degrees(BASE_SPEED, 20, block=True)
                else:
                    right_wheel.on_for_degrees(BASE_SPEED, -23, block=True)
                # continue
                memory_of_black[0] = 0
        elif 'WHITE' == lcol:
            if(rcol == 'BLACK'):
                if memory_of_black[0] < 5:
                    right_wheel.on_for_degrees(BASE_SPEED, 20, block=False)
                    left_wheel.on_for_degrees(BASE_SPEED, 20, block=True)
                else:
                    left_wheel.on_for_degrees(BASE_SPEED, -23, block=True)
                    memory_of_black[1] = 0
                # last_state = -1
                # continue
        else:
            # last_state = -1
            right_wheel.on_for_degrees(BASE_SPEED, 20, block=False)
            left_wheel.on_for_degrees(BASE_SPEED, 20, block=True)
            # go(BASE_SPEED*last_state,-BASE_SPEED*last_state)
            # go(BASE_SPEED,BASE_SPEED)
            memory_of_black = [10,10]
        memory_of_black[0] +=1
        memory_of_black[1] +=1

    return state

# === MAIN ENTRY POINT ===
def main():
    """Main program loop handling repeated transport cycles and safe shutdown."""
    init_devices()
    state = 1
    try:

        while True:
            wait_for_button_press()
            state = run_transport_cycle(state)
            # After button stop, go back to IDLE (wait for next press)
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
