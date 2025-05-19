#!/usr/bin/env python3
from ev3dev2.motor import LargeMotor, MediumMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, OUTPUT_D

left_wheel = LargeMotor(OUTPUT_A)
right_wheel = LargeMotor(OUTPUT_B)

left_wheel.stop()
right_wheel.stop()


# def get_color(sensor):
#     # sensor.rgb
#     col = {'WHITE':[255,255,255],'BLACK':[35,35,30],'BLUE':[45, 90, 190], 'GREEN':[40, 115, 60],'YELLOW':[255, 175, 60],'RED':[255, 40, 30]}
#     min_d = 9999999999
    
#     for c in ['WHITE','BLACK','BLUE', 'GREEN','YELLOW','RED']:
#         d = dist(col[c],sensor.rgb)
#         min_d = min(d,min_d)
#         col[d] = c
#     return col[min_d]
    
#green 40 115 60
#yellow 255 175 60
#red 255 40 30

#scp ./fastpz.py robot@192.168.18.80:~/fastpz.py
#ssh robot@192.168.18.80
