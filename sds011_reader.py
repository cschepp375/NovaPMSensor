#!/usr/bin/env python3

"""
Script based on https://gist.github.com/marw/9bdd78b430c8ece8662ec403e04c75fe

Get reading from Nova PM Sensor SDS011
(dust sensor, air quality sensor, PM10, PM2,5)
Designed to run from cron and append CSV file.
Script tested using Python3.4 on Ubuntu 14.04.
TODO: choose by dev name using udev, add dev id info, python package pyudev
    udevadm info -q property --export /dev/ttyUSB0
"""

import os
import csv
import io

import logging
import datetime
import argparse
import time
import requests
import yaml

try:
    import serial
except ImportError:
    print('Python serial library required, on Ubuntu/Debian:')
    print('    apt-get install python-serial python3-serial')
    raise

config = {}
start_time = None
LOG_FORMAT = '%(asctime)-15s %(levelname)-8s %(message)s'

def load_config():
    global config
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

def start_timer():
    global start_time
    start_time = time.time()

def append_csv(filename, field_names, row_dict):
    """
    Create or append one row of data to csv file.
    """
    file_exists = os.path.isfile(filename)
    with io.open(filename, 'a', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile,
                                delimiter=',',
                                lineterminator='\n',
                                fieldnames=field_names)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row_dict)


def read_nova_dust_sensor(device='/dev/ttyUSB0'):
    dev = serial.Serial(device, 9600)

    if not dev.isOpen():
        dev.open()

    msg = dev.read(10)
    assert msg[0] == ord(b'\xaa')
    assert msg[1] == ord(b'\xc0')
    assert msg[9] == ord(b'\xab')
    pm25 = (msg[3] * 256 + msg[2]) / 10.0
    pm10 = (msg[5] * 256 + msg[4]) / 10.0
    checksum = sum(v for v in msg[2:8]) % 256
    assert checksum == msg[8]
    return {'PM10': pm10, 'PM2_5': pm25}

"""
Send PM data as they occur to a webservice
"""
def send_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 10):
    """
    Send JSON data to a web service endpoint via HTTP POST.

    :param url: Endpoint URL
    :param payload: Dictionary to be sent as JSON
    :param headers: Optional additional headers
    :param timeout: Request timeout in seconds
    :return: requests.Response object
    """
    default_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    if headers:
        default_headers.update(headers)

    response = requests.post(
        url,
        json=payload,           # Automatically JSON-encodes
        headers=default_headers,
        timeout=timeout
    )

    response.raise_for_status()  # Raises HTTPError for 4xx/5xx
    return response

def main():
    global config
    global start_time

    load_config()
    host = config['webservice']['host']
    port = config['webservice']['port']
    uri =  config['webservice']['uri']
    start_timer()
    timeout_seconds = config['timeout_minutes'] * 60
    
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

    parser = argparse.ArgumentParser(description='Read data from Nova PM sensor.')
    parser.add_argument('--device', default='/dev/ttyUSB0',
                        help='Device file of connected by USB RS232 Nova PM sensor')
    parser.add_argument('--csv', default=None,
                        help='Append results to csv, you can use year, month, day in format')
    args = parser.parse_args()

    while time.time() - start_time < timeout_seconds:
        data = read_nova_dust_sensor(args.device)
        logging.info('My PM10=% 3.1f ug/m^3 My sPM2.5=% 3.1f ug/m^3', data['PM10'], data['PM2_5'])

        response = send_json(f"http://{host}:{port}{uri}", data)
        
        if args.csv:
            field_list = ['date', 'PM10', 'PM2_5']
            today = datetime.datetime.today()
            data['date'] = today.strftime('%Y-%m-%d %H:%M:%S')
            csv_file = args.csv % {'year': today.year,
                               'month': '%02d' % today.month,
                               'day': '%02d' % today.day,
                               }
            append_csv(csv_file, field_list, data)
        time.sleep(10)

if __name__ == '__main__':
    main()
