# This file consists of python code for the simulation of the Aqua-Air Health Guard System. 

import spidev
import time
import math
import smbus
import os
import RPi.GPIO as GPIO
import subprocess
import sys
import csv  

# Constants
Vc = 5.0  # Circuit voltage (V)
RL = 10.0  # Load resistance (ohms)
Ro = 9.8  # Sensor resistance in clean air (ohms)
MQ_SAMPLE_TIME = 1  # Sample time (seconds)
VREF = 3.3  # MCP3208 reference voltage (V)

# Initializing I2C bus
bus = smbus.SMBus(1)

#GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# Open SPI bus
spi = spidev.SpiDev()
spi.open(0, 0)

# Define GPIO to LCD mapping
LCD_RS = 15
LCD_E = 16
LCD_D4 = 7
LCD_D5 = 11
LCD_D6 = 12
LCD_D7 = 13

# Timing constants
E_PULSE = 0.0005
E_DELAY = 0.0005
delay = 1

# Setting up GPIO pins for LCD
GPIO.setup(LCD_E, GPIO.OUT)  
GPIO.setup(LCD_RS, GPIO.OUT) 
GPIO.setup(LCD_D4, GPIO.OUT)  
GPIO.setup(LCD_D5, GPIO.OUT)  
GPIO.setup(LCD_D6, GPIO.OUT)  
GPIO.setup(LCD_D7, GPIO.OUT)  

# Device constants
LCD_WIDTH = 20  # Maximum characters per line
LCD_CHR = True
LCD_CMD = False
LCD_LINE_1 = 0x80  # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0  # LCD RAM address for the 2nd line
LCD_LINE_3 = 0x94  # LCD RAM address for the 3rd line

# LCD initialization function
def lcd_init():
    lcd_byte(0x33, LCD_CMD)  # 110011 Initialisation
    lcd_byte(0x32, LCD_CMD)  # 110010 Initialisation
    lcd_byte(0x06, LCD_CMD)  # 000110 Cursor move direction
    lcd_byte(0x0C, LCD_CMD)  # 001100 Display On,Cursor Off, Blink Off
    lcd_byte(0x28, LCD_CMD)  # 101000 Data length, number of lines, font size
    lcd_byte(0x01, LCD_CMD)  # 000001 Clear display
    time.sleep(E_DELAY)

# To send byte to data pins
def lcd_byte(bits, mode):
    GPIO.output(LCD_RS, mode)  # RS

    # High bits
    GPIO.output(LCD_D4, False)
    GPIO.output(LCD_D5, False)
    GPIO.output(LCD_D6, False)
    GPIO.output(LCD_D7, False)
    if bits & 0x10 == 0x10:
        GPIO.output(LCD_D4, True)
    if bits & 0x20 == 0x20:
        GPIO.output(LCD_D5, True)
    if bits & 0x40 == 0x40:
        GPIO.output(LCD_D6, True)
    if bits & 0x80 == 0x80:
        GPIO.output(LCD_D7, True)

    lcd_toggle_enable()

    # Low bits
    GPIO.output(LCD_D4, False)
    GPIO.output(LCD_D5, False)
    GPIO.output(LCD_D6, False)
    GPIO.output(LCD_D7, False)
    if bits & 0x01 == 0x01:
        GPIO.output(LCD_D4, True)
    if bits & 0x02 == 0x02:
        GPIO.output(LCD_D5, True)
    if bits & 0x04 == 0x04:
        GPIO.output(LCD_D6, True)
    if bits & 0x08 == 0x08:
        GPIO.output(LCD_D7, True)

    lcd_toggle_enable()

# Toggle enable
def lcd_toggle_enable():
    time.sleep(E_DELAY)
    GPIO.output(LCD_E, True)
    time.sleep(E_PULSE)
    GPIO.output(LCD_E, False)
    time.sleep(E_DELAY)

# To send string to display
def lcd_string(message, line):
    message = message.ljust(LCD_WIDTH, " ")
    lcd_byte(line, LCD_CMD)
    for i in range(LCD_WIDTH):
        lcd_byte(ord(message[i]), LCD_CHR)

# Class for MQ-9 Sensor
class MQ9Sensor:
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)

    def read_adc(self):
        adc = self.spi.xfer2([1, (8 + 0) << 4, 0])
        adc_result = ((adc[1] & 3) << 8) + adc[2]
        return adc_result

    def read_rs_air(self):
        adc_value = self.read_adc()
        vrl = (VREF * adc_value) / 1024.0
        rs_air = ((Vc - vrl) / vrl) * RL
        return rs_air

    def read_ratio(self):
        rs_air = self.read_rs_air()
        rs_sum = 0.0
        for _ in range(MQ_SAMPLE_TIME):
            rs_sum += rs_air
            time.sleep(0.1)
        rs_avg = rs_sum / MQ_SAMPLE_TIME
        ratio = rs_avg / Ro
        return ratio

    def calculate_ppm(self, a, b):
        ratio = self.read_ratio()
        ppm = math.exp(((math.log10(ratio) - b) / a))
        return ppm

    def calculate_lpg_ppm(self):
        a_lpg = -0.45
        b_lpg = 2.30
        return self.calculate_ppm(a_lpg, b_lpg)

    def calculate_methane_ppm(self):
        a_ch4 = -0.36
        b_ch4 = 2.30
        return self.calculate_ppm(a_ch4, b_ch4)

    def calculate_co_ppm(self):
        a_co = -0.46
        b_co = 2.30
        return self.calculate_ppm(a_co, b_co)

# Class for MQ-135 Sensor
class MQ135Sensor:
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)

    def read_adc(self):
        adc = self.spi.xfer2([1, (8 + 1) << 4, 0])
        adc_result = ((adc[1] & 3) << 8) + adc[2]
        return adc_result

    def read_rs_air(self):
        adc_value = self.read_adc()
        vrl = (VREF * adc_value) / 1024.0
        rs_air = ((Vc - vrl) / vrl) * RL
        return rs_air

    def read_ratio(self):
        rs_air = self.read_rs_air()
        rs_sum = 0.0
        for _ in range(MQ_SAMPLE_TIME):
            rs_sum += rs_air
            time.sleep(0.1)
        rs_avg = rs_sum / MQ_SAMPLE_TIME
        ratio = rs_avg / Ro
        return ratio

    def calculate_ppm(self, a, b, max_value):
        ratio = self.read_ratio()
        ppm = math.exp(((math.log10(ratio) - b) / a))

        # Ensure the calculated ppm is within the specified range
        ppm = max(0, min(ppm, max_value))
        
        return ppm

    def calculate_ppm_CO2(self):
        a_co2 = -0.1005
        b_co2 = 1.0
        max_co2_value = 5000
        return self.calculate_ppm(a_co2, b_co2, max_co2_value)

    def calculate_ppm_NH3(self):
        a_nh3 = -0.2
        b_nh3 = 1.0
        max_nh3_value = 300
        return self.calculate_ppm(a_nh3, b_nh3, max_nh3_value)

# Class for turbidity sensor
class TurbiditySensor:    
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.calibration_params = {'a': 0.1, 'b': 1, 'c': 0.0}  # Calibration parameters

    def read_adc(self):
        adc = self.spi.xfer2([1, (8 + 2) << 4, 0])
        adc_result = ((adc[1] & 3) << 8) + adc[2]
        return adc_result

    def read_voltage(self):
        adc_value = self.read_adc()
        voltage = (adc_value * VREF) / 1024.0  # Assuming VREF as reference voltage
        return voltage

    def convert_to_ntu(self, voltage):
        a = self.calibration_params['a']
        b = self.calibration_params['b']
        c = self.calibration_params['c']
        ntu = a * (voltage ** 2) + b * voltage + c
        return ntu

    def read_turbidity(self):
        voltage = self.read_voltage()
        ntu = self.convert_to_ntu(voltage)
        return ntu

class PHSensor:
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)

    def read_adc(self):
        adc = self.spi.xfer2([1, (8 + 3) << 4, 0])
        adc_result = ((adc[1] & 3) << 8) + adc[2]
        return adc_result
	
    def ConvertTemp(self, data):
        temp = ((data * 330) / float(1023))
        temp = round(temp, 2)  # Round to 2 decimal places
        return temp

# Initialization of previous sensor values
prev_co_ppm = None
prev_lpg_ppm = None
prev_methane_ppm = None
prev_co2_ppm = None
prev_nh3_ppm = None
prev_turbidity_ntu = None
prev_ph = None

csv_file_path = "D:\\IOT\\dataFiles\\aqua_air_readings.csv"



try:
    lcd_init()
    lcd_string("Welcome!", LCD_LINE_1)
    time.sleep(0.2)
    # Main loop
    while True:
        # MQ-9 Sensor readings
        mq9 = MQ9Sensor()
        co_ppm = mq9.calculate_co_ppm()
        lpg_ppm = mq9.calculate_lpg_ppm()
        methane_ppm = mq9.calculate_methane_ppm()

        # Print MQ-9 sensor values if they change or are not initialized
        if co_ppm != prev_co_ppm or prev_co_ppm is None:
            lcd_string("MQ-9 Sensor: ", LCD_LINE_1)
            lcd_string("CO: {:.2f} ppm".format(co_ppm), LCD_LINE_1)
            print("MQ-9 Sensor:")
            print("Carbon Monoxide concentration: {:.3f} ppm".format(co_ppm))
            prev_co_ppm = co_ppm

        if lpg_ppm != prev_lpg_ppm or prev_lpg_ppm is None:
            print("LPG concentration: {:.3f} ppm".format(lpg_ppm))
            prev_lpg_ppm = lpg_ppm

        if methane_ppm != prev_methane_ppm or prev_methane_ppm is None:
            lcd_string("Methane: {:.2f} ppm".format(methane_ppm), LCD_LINE_2)
            print("Methane concentration: {:.3f} ppm".format(methane_ppm))
            prev_methane_ppm = methane_ppm

        # MQ-135 Sensor readings
        mq135 = MQ135Sensor()
        co2_ppm = mq135.calculate_ppm_CO2()
        nh3_ppm = mq135.calculate_ppm_NH3()

        # Print MQ-135 sensor values if they change or are not initialized
        if co2_ppm != prev_co2_ppm or prev_co2_ppm is None:
            lcd_string("MQ-135 Sensor: ", LCD_LINE_1)
            lcd_string("CO2: {:.2f} ppm".format(co2_ppm), LCD_LINE_1)
            print("MQ-135 Sensor:")
            print("Carbon Dioxide concentration: {:.3f} ppm".format(co2_ppm))
            prev_co2_ppm = co2_ppm

        if nh3_ppm != prev_nh3_ppm or prev_nh3_ppm is None:
            lcd_string("NH3: {:.2f} ppm".format(nh3_ppm), LCD_LINE_2)
            print("Ammonia concentration: {:.3f} ppm".format(nh3_ppm))
            prev_nh3_ppm = nh3_ppm

        turbidity_sensor = TurbiditySensor()
        turbidity_ntu = turbidity_sensor.read_turbidity()

        # Print Turbidity sensor value if it changes or is not initialized
        if turbidity_ntu != prev_turbidity_ntu or prev_turbidity_ntu is None:
            lcd_string("Turbidity: {:.2f} NTU".format(turbidity_ntu), LCD_LINE_2)
            print("Turbidity Sensor:")
            print("Turbidity: {:.3f} NTU".format(turbidity_ntu))
            prev_turbidity_ntu = turbidity_ntu

        ph_sensor = PHSensor()
        ph_adc = ph_sensor.read_adc()
        ph_value = ph_sensor.ConvertTemp(ph_adc)

        # Print pH sensor value if it changes or is not initialized
        if ph_value != prev_ph or prev_ph is None:
            lcd_string("pH: {:.2f}".format(ph_value), LCD_LINE_1)
            print("pH Sensor:")
            print("pH: {:.2f}".format(ph_value))
            prev_ph = ph_value

        time.sleep(0.2)
	
	# my stuff
        with open(csv_file_path, 'w', newline='') as csvfile:
            fieldnames = ['co', 'methane', 'co2', 'nh3', 'turbidity', 'ph']
            csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            # Check if the file is empty, write header if needed
            #if csvfile.tell() == 0:
            csv_writer.writeheader()
            csv_writer.writerow({'co': co_ppm,'methane': methane_ppm,'co2': co2_ppm,'nh3': nh3_ppm,'turbidity': turbidity_ntu,'ph': ph_value})

            # Flush the buffer to ensure immediate writing
            csvfile.flush()
            time.sleep(delay)
        
        
except KeyboardInterrupt:
    pass
finally:
    csvfile.close()
    GPIO.cleanup()
    
