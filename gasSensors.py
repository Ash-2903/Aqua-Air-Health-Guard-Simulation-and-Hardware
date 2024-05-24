import machine
import time
import os

def convert_to_ppm(sensor_value, a, b):
    ppm = a * sensor_value + b
    return ppm

def append_to_csv(filename, data):
    try:
        exists = os.stat(filename)
    except OSError:
        exists = None
    
    with open(filename, 'w') as file:
        file.write("co,ch4,co2,nh3\n")
        file.write(data + '\n')

csv_file_path = "D:\\IOT\\dataFiles\\mq9_mq135.csv"

# Calibration coefficients for MQ-9 CO
a_mq9_co = 0.01  
b_mq9_co = 0.0   

# Calibration coefficients for MQ-9 CH4
a_mq9_ch4 = 0.015  
b_mq9_ch4 = 0.0    

# Calibration coefficients for MQ-135 CO2
a_mq135_co2 = 0.02  
b_mq135_co2 = 0.0   

# Calibration coefficients for MQ-135 NH3
a_mq135_nh3 = 0.025  
b_mq135_nh3 = 0.0    

# Constants
Vc = 5.0  # Circuit voltage (V)
RL = 10.0  # Load resistance (ohms)
Ro = 9.8  # Sensor resistance in clean air (ohms)
MQ_SAMPLE_TIME = 1  # Sample time (seconds)
VREF = 3.3  # MCP3208 reference voltage (V)
CHANNEL = 0  # Channel connected to MQ sensors

analog_pin_mq9 = machine.ADC(28)
analog_pin_mq135 = machine.ADC(26)

flag = 0

while True:
    sensor_value_mq9 = analog_pin_mq9.read_u16()
    sensor_value_mq135 = analog_pin_mq135.read_u16()

    # Convert MQ-9 sensor values to ppm
    mq9_co_ppm = convert_to_ppm(sensor_value_mq9, a_mq9_co, b_mq9_co)
    mq9_ch4_ppm = convert_to_ppm(sensor_value_mq9, a_mq9_ch4, b_mq9_ch4)

    # Convert MQ-135 sensor values to ppm
    mq135_co2_ppm = convert_to_ppm(sensor_value_mq135, a_mq135_co2, b_mq135_co2)
    mq135_nh3_ppm = convert_to_ppm(sensor_value_mq135, a_mq135_nh3, b_mq135_nh3)
    

    if flag == 0:
        print("MQ-9 CO ppm: {:.2f}".format(mq9_co_ppm))
        print("MQ-9 CH4 ppm: {:.2f}".format(mq9_ch4_ppm))
        print("MQ-135 CO2 ppm: {:.2f}".format(mq135_co2_ppm))
        print("MQ-135 NH3 ppm: {:.2f}".format(mq135_nh3_ppm))
        datas = "{:.2f},{:.2f},{:.2f},{:.2f}".format(mq9_co_ppm, mq9_ch4_ppm, mq135_co2_ppm, mq135_nh3_ppm)
        append_to_csv(csv_file_path,datas)
        flag=1

