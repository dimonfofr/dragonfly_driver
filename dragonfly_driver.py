import minimalmodbus
import serial.tools.list_ports
import time
import sys
import time
from influxdb import InfluxDBClient

BACKEND = "influx"

SLEEP_TIME = 1


BAUDRATE = 115200


INFLUX_HOST = 'localhost'
INFLUX_PORT = 8086
INFLUX_USER = 'bee'
INFLUX_PASS = 'bee'
INFLUX_DB = 'weather'

mb = None

weathers = {}

def FindDevice():
    global mb

    for p in list(serial.tools.list_ports.comports()):
        if (p.vid == 0x0403) and (p.pid == 0x6015):
            mb = minimalmodbus.Instrument(str(p.device), 0x80, mode='ascii')
            if not mb.serial.is_open:
                mb.serial.open()
            print('Device Found!')
            return True
    
    return False


FindDevice()



def get_dragonfly_data():
    for i in range(0,3):
        start_reg = 8 * i
        
        address  = mb.read_register(start_reg + 0, functioncode=0x03)

        if (address == 0):
            continue
        temp_1   = mb.read_register(start_reg + 1, functioncode=0x03)
        humi_1   = mb.read_register(start_reg + 2, functioncode=0x03)
        temp_2   = mb.read_register(start_reg + 3, functioncode=0x03)
        humi_2   = mb.read_register(start_reg + 4, functioncode=0x03)
        pressure = mb.read_register(start_reg + 5, functioncode=0x03)
        voltage  = mb.read_register(start_reg + 6, functioncode=0x03)
        rssi     = mb.read_register(start_reg + 7, functioncode=0x03)

        weather = {}
        weather['address'] = address
        weather['temp_1'] = float((temp_1 / 10.0))
        weather['temp_2'] = float((temp_2 / 10.0))
        weather['humi_1'] = humi_1
        weather['humi_2'] = humi_2
        weather['pressure'] = pressure
        weather['voltage'] = voltage

        weathers[address] = weather
        print('address:   %d'    % int(weathers[address]['address']))
        print('temp_1:   %.1f'  % float(weathers[address]['temp_1']))
        print('humi_1:   %d'    % int(weathers[address]['humi_1']))
        print('temp_2:   %.1f'  % float(weathers[address]['temp_2']))
        print('humi_2:   %d'    % int(weathers[address]['humi_2']))
        print('pressure: %d'    % int(weathers[address]['pressure']))
        print('voltage:  %d'    % int(weathers[address]['voltage']))
        print('\n')
        
    time.sleep(1)

def insert_influx(weather):
    global weathers
    client = InfluxDBClient(host=INFLUX_HOST,
                            port=INFLUX_PORT,
                            username=INFLUX_USER,
                            password=INFLUX_PASS)
    databases = [db['name'] for db in client.get_list_database()]
    if INFLUX_DB not in databases:
        print('Database {db} not found.'.format(db=INFLUX_DB))
        client.create_database(INFLUX_DB)
        
        databases = [db['name'] for db in client.get_list_database()]

        if INFLUX_DB not in databases:
            print('Cannot create database {db}.'.format(db=INFLUX_DB))
            sys.exit(1)

        print('Database {db} created.'.format(db=INFLUX_DB))
    
    client.switch_database(INFLUX_DB)
    
    # Writing weather information
    print('\n')
    print(weathers)
    print('\n')
    for key, val in weathers.items():
            
            
            json_body = [
                {
                    "measurement": "weather",
                    "tags": {
                        "station-id": key
                    },
                    "fields": {
                        "temp1":        float(weathers[key]['temp_1']),
                        "temp2":        float(weathers[key]['temp_2']),
                        "humi1":        int(weathers[key]['humi_1']),
                        "humi2":        int(weathers[key]['humi_2']),
                        "pressure":     int(weathers[key]['pressure']),
                        "voltage":      int(weathers[key]['voltage'])
                    }
                }
            ]

            if not client.write_points(json_body):
                print('Cannot write tech data into database!')
                sys.exit(1)
    
def delete_db():
    client = InfluxDBClient(host=INFLUX_HOST,
                        port=INFLUX_PORT,
                        username=INFLUX_USER,
                        password=INFLUX_PASS)
    databases = [db['name'] for db in client.get_list_database()]
    client.drop_database(INFLUX_DB)
    print('DB dropped!')

   


def main():

    delete_db()

    while (1):
        get_dragonfly_data()
        insert_influx(weathers)
        time.sleep(SLEEP_TIME)
        pass
    

if __name__ == '__main__':
    main()