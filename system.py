import datetime
import json
import time

from pymata4 import pymata4

import dig_calls

# DIG constants
SEND_DIG = True
IGNITION_CODE = 10000
ODOMETER_CODE = 5
BRAKE_CODE = 1
HIGH_BEAM_CODE = 2091
HAZARD_LIGHT_CODE = 2090
LEFT_SIGNAL_CODE = 41
RIGHT_SIGNAL_CODE = 42

# Pinout constants
IGNITION_PIN = 2

X_PIN = 0
Y_PIN = 1
Z_PIN = 3

BUTTON_HB_PIN = 4
BUTTON_HZ_PIN = 5
LED_L_PIN = 6
LED_R_PIN = 7

POT_PIN = 2
LED_HB_PIN = 8
LED_HZ_PIN = 9

# Constant values
CYCLE_TIME = 0.1
POLL_COUNT = 25

MAX_INT = 1024
LEFT_THRESH = MAX_INT // 4
RIGHT_THRESH = MAX_INT * 3 // 4

# Device serial number from config
with open("config.json", "r") as file:
    data = json.load(file)
    SERIAL_NUMBER = data["serialNo"]

# State variables
state = {
    "ignition": 0,
    "x": 0,
    "y": 0,
    "z": 0,
    "speed": 0,
    "accel": 0,
    "bl": 0,
    "br": 0,
    "hb": 0,
    "hz": 0,
}

local_state = {
    "z": 0,
    "hb": 0,
    "hz": 0,
    "bl": 0,
    "br": 0,
}

# Board setup
board = pymata4.Pymata4()

board.set_pin_mode_digital_input(IGNITION_PIN)

board.set_pin_mode_analog_input(X_PIN)
board.set_pin_mode_analog_input(Y_PIN)
board.set_pin_mode_digital_input(Z_PIN)

board.set_pin_mode_analog_input(POT_PIN)

board.set_pin_mode_digital_output(LED_L_PIN)
board.set_pin_mode_digital_output(LED_R_PIN)

board.set_pin_mode_digital_input(BUTTON_HB_PIN)
board.set_pin_mode_digital_input(BUTTON_HZ_PIN)

board.set_pin_mode_digital_output(LED_HB_PIN)
board.set_pin_mode_digital_output(LED_HZ_PIN)

# Authentication calls for MyAdmin and DIG
if SEND_DIG:
    try:
        MyAdmin_authenticate_flag, userId, sessionId = dig_calls.authenticate_MyAdmin()
        assert MyAdmin_authenticate_flag

        DIG_authenticate_flag, token, tokenExpiration, refreshToken, refreshTokenExpiration = (
            dig_calls.authenticate_DIG()
        )
        assert DIG_authenticate_flag
    except AssertionError:
        print("Authentication Error")


# Sends dig calls
def send_dig_call(value, code):
    print(f"sending {value} for {code}")
    if SEND_DIG:
        try:
            res = dig_calls.send_GenericStatusRecord(
                token=token,
                serialNo=SERIAL_NUMBER,
                code=code,
                value=value,
                timestamp=datetime.datetime.now(),
            )
            assert res
        except AssertionError:
            print("sending GeneritStatusRecord failed")


# Handles the ignition data
def ignition_handler(ignition):
    if ignition != state["ignition"]:
        state["ignition"] = ignition
        send_dig_call(state["ignition"], IGNITION_CODE)


# Handles the button press data
def button_handler(value, key):
    if value != local_state[key]:
        local_state[key] = value
        if value:
            if state[key]:
                state[key] = 0
            else:
                state[key] = 1
        if key == "z":
            send_dig_call(state[key], BRAKE_CODE)
        elif key == "hb":
            board.digital_write(LED_HB_PIN, state[key])
            send_dig_call(state[key], HIGH_BEAM_CODE)
        elif key == "hz":
            board.digital_write(LED_HZ_PIN, state[key])
            send_dig_call(state[key], HAZARD_LIGHT_CODE)


# Handles the joystick data
def joystick_handler(x, z):
    accel = (x - MAX_INT // 2) * 10 / (MAX_INT // 2)
    speed = max(state["speed"] - 10 if z else state["speed"] + accel * CYCLE_TIME, 0)

    state["accel"] = int(accel)
    state["speed"] = int(speed)
    state["x"] += int((state["speed"] + speed) // 2 * CYCLE_TIME)

    button_handler(z, "z")

    if ticks % POLL_COUNT == 0:
        send_dig_call(state["x"], ODOMETER_CODE)


# Handles the potentiometer data
def pot_handler(pot):
    if pot < LEFT_THRESH and not state["bl"]:
        state["bl"] = 1
        board.digital_pin_write(LED_L_PIN, 1)
        if not local_state["bl"]:
            send_dig_call(state["bl"], LEFT_SIGNAL_CODE)
            local_state["bl"] = 1
    elif pot > LEFT_THRESH and state["bl"]:
        state["bl"] = 0
        board.digital_pin_write(LED_L_PIN, 0)
        if local_state["bl"]:
            send_dig_call(state["bl"], LEFT_SIGNAL_CODE)
            local_state["bl"] = 0
    if pot > RIGHT_THRESH and not state["br"]:
        state["br"] = 1
        board.digital_pin_write(LED_R_PIN, 1)
        if not local_state["br"]:
            send_dig_call(state["br"], RIGHT_SIGNAL_CODE)
            local_state["br"] = 1
    elif pot < RIGHT_THRESH and state["br"]:
        state["br"] = 0
        board.digital_pin_write(LED_R_PIN, 0)
        if local_state["br"]:
            send_dig_call(state["br"], RIGHT_SIGNAL_CODE)
            local_state["br"] = 0


# Updates the state by reading the inputs and calling the handlers
def update_state():
    ignition, _ = board.digital_read(IGNITION_PIN)
    ignition_handler(ignition)

    hb, _ = board.digital_read(BUTTON_HB_PIN)
    button_handler(hb, "hb")

    hz, _ = board.digital_read(BUTTON_HZ_PIN)
    button_handler(hz, "hz")

    x, _ = board.analog_read(X_PIN)
    z, _ = board.digital_read(Z_PIN)
    joystick_handler(x, z)

    pot, _ = board.analog_read(POT_PIN)
    pot_handler(pot)


# Main process
if __name__ == "__main__":
    try:
        ticks = 0
        # Update the state every tick
        while True:
            update_state()
            ticks += 1
            time.sleep(CYCLE_TIME)
    except KeyboardInterrupt:
        board.shutdown()
        print("Program terminated")
