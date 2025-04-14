#!/usr/bin/env python3
from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, OUTPUT_D

left_wheel = LargeMotor(OUTPUT_A)
right_wheel = LargeMotor(OUTPUT_B)

left_wheel.stop()
right_wheel.stop()


