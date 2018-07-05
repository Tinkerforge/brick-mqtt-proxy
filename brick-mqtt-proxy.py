#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Brick MQTT Proxy
Copyright (C) 2015-2017 Matthias Bolte <matthias@tinkerforge.com>
Copyright (C) 2017 Ishraq Ibne Ashraf <ishraq@tinkerforge.com>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public
License along with this program; if not, write to the
Free Software Foundation, Inc., 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.
"""

BRICKD_HOST = 'localhost'
BRICKD_PORT = 4223
BROKER_HOST = 'localhost'
BROKER_PORT = 1883 # 8883 for TLS
GLOBAL_TOPIC_PREFIX = 'tinkerforge/'
UPDATE_INTERVAL = 3.0 # seconds
ENUMERATE_INTERVAL = 15.0 # seconds

import argparse
import json
import struct
import sys
import time
import threading
import logging
import paho.mqtt.client as mqtt # pip install paho-mqtt
from tinkerforge.ip_connection import IPConnection, Error
# Bricks
from tinkerforge.brick_dc import BrickDC
from tinkerforge.brick_imu import BrickIMU
from tinkerforge.brick_imu_v2 import BrickIMUV2
from tinkerforge.brick_master import BrickMaster
from tinkerforge.brick_servo import BrickServo
from tinkerforge.brick_silent_stepper import BrickSilentStepper
from tinkerforge.brick_stepper import BrickStepper
# Bricklets
from tinkerforge.bricklet_accelerometer import BrickletAccelerometer
from tinkerforge.bricklet_ambient_light import BrickletAmbientLight
from tinkerforge.bricklet_ambient_light_v2 import BrickletAmbientLightV2
from tinkerforge.bricklet_analog_in import BrickletAnalogIn
from tinkerforge.bricklet_analog_in_v2 import BrickletAnalogInV2
from tinkerforge.bricklet_analog_out import BrickletAnalogOut
from tinkerforge.bricklet_analog_out_v2 import BrickletAnalogOutV2
from tinkerforge.bricklet_analog_in_v3 import BrickletAnalogInV3
from tinkerforge.bricklet_barometer import BrickletBarometer
from tinkerforge.bricklet_can import BrickletCAN
from tinkerforge.bricklet_co2 import BrickletCO2
from tinkerforge.bricklet_color import BrickletColor
from tinkerforge.bricklet_current12 import BrickletCurrent12
from tinkerforge.bricklet_current25 import BrickletCurrent25
from tinkerforge.bricklet_distance_ir import BrickletDistanceIR
from tinkerforge.bricklet_distance_us import BrickletDistanceUS
from tinkerforge.bricklet_dmx import BrickletDMX
from tinkerforge.bricklet_dual_button import BrickletDualButton
from tinkerforge.bricklet_dual_relay import BrickletDualRelay
from tinkerforge.bricklet_dust_detector import BrickletDustDetector
from tinkerforge.bricklet_gps import BrickletGPS
from tinkerforge.bricklet_gps_v2 import BrickletGPSV2
from tinkerforge.bricklet_hall_effect import BrickletHallEffect
from tinkerforge.bricklet_humidity import BrickletHumidity
from tinkerforge.bricklet_humidity_v2 import BrickletHumidityV2
from tinkerforge.bricklet_industrial_analog_out import BrickletIndustrialAnalogOut
from tinkerforge.bricklet_industrial_digital_in_4 import BrickletIndustrialDigitalIn4
from tinkerforge.bricklet_industrial_digital_out_4 import BrickletIndustrialDigitalOut4
from tinkerforge.bricklet_industrial_dual_0_20ma import BrickletIndustrialDual020mA
from tinkerforge.bricklet_industrial_dual_analog_in import BrickletIndustrialDualAnalogIn
from tinkerforge.bricklet_industrial_quad_relay import BrickletIndustrialQuadRelay
from tinkerforge.bricklet_io16 import BrickletIO16
from tinkerforge.bricklet_io4 import BrickletIO4
from tinkerforge.bricklet_joystick import BrickletJoystick
from tinkerforge.bricklet_laser_range_finder import BrickletLaserRangeFinder
from tinkerforge.bricklet_lcd_16x2 import BrickletLCD16x2
from tinkerforge.bricklet_lcd_20x4 import BrickletLCD20x4
from tinkerforge.bricklet_led_strip import BrickletLEDStrip
from tinkerforge.bricklet_line import BrickletLine
from tinkerforge.bricklet_linear_poti import BrickletLinearPoti
from tinkerforge.bricklet_load_cell import BrickletLoadCell
from tinkerforge.bricklet_moisture import BrickletMoisture
from tinkerforge.bricklet_motion_detector import BrickletMotionDetector
from tinkerforge.bricklet_motion_detector_v2 import BrickletMotionDetectorV2
from tinkerforge.bricklet_motorized_linear_poti import BrickletMotorizedLinearPoti
from tinkerforge.bricklet_multi_touch import BrickletMultiTouch
from tinkerforge.bricklet_nfc_rfid import BrickletNFCRFID
from tinkerforge.bricklet_oled_128x64 import BrickletOLED128x64
from tinkerforge.bricklet_oled_64x48 import BrickletOLED64x48
from tinkerforge.bricklet_piezo_buzzer import BrickletPiezoBuzzer
from tinkerforge.bricklet_piezo_speaker import BrickletPiezoSpeaker
from tinkerforge.bricklet_outdoor_weather import BrickletOutdoorWeather
from tinkerforge.bricklet_ptc import BrickletPTC
from tinkerforge.bricklet_real_time_clock import BrickletRealTimeClock
from tinkerforge.bricklet_remote_switch import BrickletRemoteSwitch
from tinkerforge.bricklet_remote_switch_v2 import BrickletRemoteSwitchV2
from tinkerforge.bricklet_rgb_led import BrickletRGBLED
from tinkerforge.bricklet_rgb_led_button import BrickletRGBLEDButton
from tinkerforge.bricklet_rgb_led_matrix import BrickletRGBLEDMatrix
from tinkerforge.bricklet_rotary_encoder import BrickletRotaryEncoder
from tinkerforge.bricklet_rotary_encoder_v2 import BrickletRotaryEncoderV2
from tinkerforge.bricklet_rotary_poti import BrickletRotaryPoti
from tinkerforge.bricklet_rs232 import BrickletRS232
from tinkerforge.bricklet_rs485 import BrickletRS485
from tinkerforge.bricklet_segment_display_4x7 import BrickletSegmentDisplay4x7
from tinkerforge.bricklet_solid_state_relay import BrickletSolidStateRelay
from tinkerforge.bricklet_solid_state_relay_v2 import BrickletSolidStateRelayV2
from tinkerforge.bricklet_sound_intensity import BrickletSoundIntensity
from tinkerforge.bricklet_temperature import BrickletTemperature
from tinkerforge.bricklet_temperature_ir import BrickletTemperatureIR
from tinkerforge.bricklet_temperature_ir_v2 import BrickletTemperatureIRV2
from tinkerforge.bricklet_thermal_imaging import BrickletThermalImaging
from tinkerforge.bricklet_thermocouple import BrickletThermocouple
from tinkerforge.bricklet_tilt import BrickletTilt
from tinkerforge.bricklet_uv_light import BrickletUVLight
from tinkerforge.bricklet_voltage import BrickletVoltage
from tinkerforge.bricklet_voltage_current import BrickletVoltageCurrent

class Getter(object):
    def __init__(self, proxy, getter_name, parameters, topic_suffix, result_name):
        self.proxy = proxy
        self.getter = getattr(proxy.device, getter_name)
        self.parameters = parameters
        self.topic_suffix = topic_suffix
        self.result_name = result_name
        self.last_result = None

    def update(self):
        try:
            if self.parameters == None:
                result = self.getter()
            elif isinstance(self.parameters, tuple):
                result = self.getter(*self.parameters)
            else: # dict
                result = {}

                for key, value in self.parameters.items():
                    try:
                        result[key] = self.getter(*value)
                    except Error as e:
                        if e.value in [Error.INVALID_PARAMETER, Error.NOT_SUPPORTED]:
                            result[key] = None
                        else:
                            raise
        except Exception as e:
            result = self.last_result

        if result != None and result != self.last_result:
            payload = {}

            if isinstance(result, dict):
                for key, value in result.items():
                    payload[key] = {}

                    if isinstance(value, tuple) and hasattr(value, '_fields'): # assume it is a namedtuple
                        for field in value._fields:
                            payload[key][field] = getattr(value, field)
                    elif value == None:
                        payload[key] = value
                    else:
                        payload[key][self.result_name] = value
            elif isinstance(result, tuple) and hasattr(result, '_fields'): # assume it is a namedtuple
                for field in result._fields:
                    payload[field] = getattr(result, field)
            else:
                payload[self.result_name] = result

            self.proxy.publish_values(self.topic_suffix, **payload)

        self.last_result = result

class Setter(object):
    def __init__(self, proxy, setter_name, topic_suffix, parameter_names, getter_info = None):
        self.setter = None
        self.getter = None
        self.proxy = proxy
        self.getter_info = getter_info
        self.topic_suffix = topic_suffix
        self.parameter_names = parameter_names

        if setter_name != None:
            self.setter = getattr(self.proxy.device, setter_name)

        if getter_info != None:
            self.getter = getattr(self.proxy.device, self.getter_info['getter_name'])

    def handle_message(self, payload):
        args = []

        for parameter_name in self.parameter_names:
            try:
                args.append(payload[parameter_name])
            except:
                return

        if  self.getter_info == None:
            try:
                self.setter(*tuple(args))
            except:
                pass
        else:
            payload = {}

            try:
                result = self.getter(*tuple(args))

                if isinstance(result, tuple) and hasattr(result, '_fields'): # assume it is a namedtuple
                    for field in result._fields:
                        payload[field] = getattr(result, field)
                else:
                    payload[self.getter_info['getter_return_value']] = result

                self.proxy.publish_values(self.getter_info['getter_publish_topic'], **payload)
            except:
                pass

class DeviceProxy(object):
    GETTER_SPECS = []
    SETTER_SPECS = []
    EXTRA_SUBSCRIPTIONS = []

    def __init__(self, uid, connected_uid, position, hardware_version, firmware_version,
                 ipcon, client, update_interval, global_topic_prefix):
        self.timestamp = time.time()
        self.uid = uid
        self.connected_uid = connected_uid
        self.position = position
        self.hardware_version = hardware_version
        self.firmware_version = firmware_version
        self.ipcon = ipcon
        self.client = client
        self.device = self.DEVICE_CLASS(uid, ipcon)
        self.topic_prefix = '{0}/{1}/'.format(self.TOPIC_PREFIX, uid)
        self.getters = []
        self.setters = {}
        self.global_topic_prefix = global_topic_prefix
        self.update_interval = 0 # seconds
        self.update_timer = None
        self.update_timer_lock = threading.Lock()

        for getter_spec in self.GETTER_SPECS:
            self.getters.append(Getter(self, *getter_spec))

        for setter_spec in self.SETTER_SPECS:
            self.setters[setter_spec[1]] = Setter(self, *setter_spec)
            self.subscribe(self.topic_prefix + setter_spec[1])

        for topic_suffix in self.EXTRA_SUBSCRIPTIONS:
            self.subscribe(self.topic_prefix + topic_suffix)

        self.subscribe(self.topic_prefix + '_update_interval/set')

        try:
            self.setup_callbacks()
        except:
            logging.exception('Exception during setup_callbacks call')

        self.update_getters()
        self.set_update_interval(update_interval)

    def handle_message(self, topic_suffix, payload):
        if topic_suffix == '_update_interval/set':
            try:
                self.set_update_interval(float(payload['_update_interval']))
            except:
                pass
        elif topic_suffix in self.setters:
            self.setters[topic_suffix].handle_message(payload)
        else:
            try:
                self.handle_extra_message(topic_suffix, payload)
            except:
                logging.exception('Exception during handle_extra_message call')

        self.update_getters()

    def handle_extra_message(self, topic_suffix, payload): # to be implemented by subclasses
        pass

    def publish_as_json(self, topic, payload, *args, **kwargs):
        self.client.publish(self.global_topic_prefix + topic,
                            json.dumps(payload, separators=(',', ':')),
                            *args, **kwargs)

    def publish_values(self, topic_suffix, **kwargs):
        payload = {'_timestamp': time.time()}

        for key, value in kwargs.items():
            payload[key] = value

        self.publish_as_json(self.topic_prefix + topic_suffix, payload, retain=True)

    def set_update_interval(self, update_interval): # in seconds
        update_timer = None

        with self.update_timer_lock:
            update_timer = self.update_timer
            self.update_timer = None

        if update_timer != None:
            update_timer.cancel()

        if self.update_interval != update_interval:
            self.publish_values('_update_interval', _update_interval=float(update_interval))

        with self.update_timer_lock:
            self.update_interval = update_interval

            if self.update_timer == None and self.update_interval > 0:
                self.update_timer = threading.Timer(self.update_interval, self.update)
                self.update_timer.start()

    def update_getters(self):
        for getter in self.getters:
            getter.update()

        try:
            self.update_extra_getters()
        except:
            logging.exception('Exception during update_extra_getters call')

    def update_extra_getters(self): # to be implemented by subclasses
        pass

    def update(self):
        with self.update_timer_lock:
            if self.update_timer == None:
                return

            self.update_timer = None

        self.update_getters()

        with self.update_timer_lock:
            if self.update_timer == None and self.update_interval > 0:
                self.update_timer = threading.Timer(self.update_interval, self.update)
                self.update_timer.start()

    def setup_callbacks(self): # to be implemented by subclasses
        pass

    def get_enumerate_entry(self):
        return {'_timestamp': self.timestamp,
                'uid': self.uid,
                'connected_uid': self.connected_uid,
                'position': self.position,
                'hardware_version': self.hardware_version,
                'firmware_version': self.firmware_version,
                'device_identifier': self.DEVICE_CLASS.DEVICE_IDENTIFIER}

    def subscribe(self, topic_suffix):
        topic = self.global_topic_prefix + topic_suffix

        logging.debug('Subscribing to ' + topic)
        self.client.subscribe(topic)

    def unsubscribe(self, topic_suffix):
        topic = self.global_topic_prefix + topic_suffix

        logging.debug('Unsubscribing from ' + topic)
        self.client.unsubscribe(topic)

    def destroy(self):
        self.set_update_interval(0)

        for setter_spec in self.SETTER_SPECS:
            self.unsubscribe(self.topic_prefix + setter_spec[1])

        for topic_suffix in self.EXTRA_SUBSCRIPTIONS:
            self.unsubscribe(self.topic_prefix + topic_suffix)

        self.unsubscribe(self.topic_prefix + '_update_interval/set')

#
# DeviceProxy is the base class for all Brick and Bricklet MQTT handling. The
# DeviceProxy class expects subclasses to define several members:
#
# - DEVICE_CLASS (required): This is the Brick or Bricklet API bindings class.
#   The DeviceProxy automatically creates an instance of this class that can be
#   accessed via self.device in subclasses.
#
# - TOPIC_PREFIX (required): The MQTT topic prefix used for this DeviceProxy
#   subclass. All messages published by this DeviceProxy to any topic suffix
#   will automatically be prefixed with the topic prefix and the UID of the
#   represented device:
#
#     tinkerforge/<topic-prefix>/<uid>/<topic-suffix>
#
#   Also all subscriptions for any topic suffix will automatically be prefixed
#   with the same topic prefix.
#
# - GETTER_SPECS (optional): A list of Brick or Bricklet getter specifications.
#   The DeviceProxy instance automatically calls the specified getter with the
#   configured update interval on self.device. If the returned value changed
#   since the last call then the new value is published as a retained message
#   with a JSON payload that is formatted according to the getter specification.
#   Each getter specification is a 4-tuple:
#
#     (<getter-name>, <parameters>, <topic-suffix>, <value-name>)
#
#   If the getter returns a single value, then the value name is used as key
#   in the JSON payload. If the getter does not return a single value then it
#   returns a namedtuple instead. The DeviceProxy instance automatically uses
#   the field names of the namedtuple as keys in the JSON payload. In this case
#   the value name in the getter specification is ignored and should be set to
#   None.
#
# - update_extra_getters (optional): A bound function taking no arguments. This
#   can be used to implement things that don't fit into a getter specification.
#   The DeviceProxy instance will automatically call this function with the
#   configured update interval. Inside this function the publish_values function
#   of the DeviceProxy class can be used to publish a dict formatted as JSON to
#   a specified topic suffix.
#
# - SETTER_SPECS (optional): A list of Brick or Bricklet setter specifications.
#   The DeviceProxy instance automatically subscribes to the specified topics
#   and handles messages with JSON payloads that contain key-value pairs
#   according to the specified format. Each setter specification is a 3-tuple:
#
#     (<setter-name>, <topic-suffix>, [<parameter-name>, ...])
#
#   If the setter has no parameters then the third item in the tuple can be an
#   empty list. Otherwise it has to be a list of strings specifying parameter
#   names for the setter. The DeviceProxy instance looks for keys in the JSON
#   payload that match the specified values names. If a value was found for
#   each parameter then the specified setter is called on self.device with the
#   arguments from the JSON payload.
#
#   Getters which require input arguments are provided with the arguments through
#   setter mechanism. In which case the setter specification is as follows:
#
#     (None, <topic-suffix>, [<parameter-name>, ...], {<getter-info>})
#
#   In this case the dictionary getter-info has the following fields:
#
#   getter_name = Name of the getter to call. This getter will be called with
#                 the arguments as received on the <topic-suffix> topic as
#                 described above.
#
#   getter_publish_topic = Name of the topic to which the getter return values
#                          are to be published.
#
#   getter_return_value = Fields of the getter return value. If the getter returns
#                         more than one value then this field should be "None".
#                         Otherwise the return value field name must be specified
#                         as a string.
#
# - EXTRA_SUBSCRIPTIONS (optional): A list of additional topic suffixes. This
#   can be used to implement things that don't fit into a setter specification.
#   The DeviceProxy instance automatically subscribes to the specified topics
#   and handles messages with JSON payloads. The payload is decoded as JSON and
#   passed to the bound handle_extra_message function.
#
# - handle_extra_message (optional): A bound function taking two arguments: the
#   topic suffix as str and the decoded JSON payload as dict.
#
# - setup_callbacks (optional): A bound function taking no arguments. This can
#   be used to deal with callbacks such as the button pressed/released callbacks
#   of the LCD 20x4 Bricklet. Only callbacks without configuration should be
#   used, because the configuration in global and could interfere with other
#   user programs.
#
# To add a new DeviceProxy subclass implement it according to the description
# above. The Proxy class will automatically pick up all DeviceProxy subclasses
# and use them.
#

class BrickDCProxy(DeviceProxy):
    DEVICE_CLASS = BrickDC
    TOPIC_PREFIX = 'brick/dc'
    GETTER_SPECS = [('get_velocity', None, 'velocity', 'velocity'),
                    ('get_current_velocity', None, 'current_velocity', 'velocity'),
                    ('get_acceleration', None, 'acceleration', 'acceleration'),
                    ('is_enabled', None, 'enabled', 'enabled'),
                    ('get_pwm_frequency', None, 'pwm_frequency', 'frequency'),
                    ('get_stack_input_voltage', None, 'stack_input_voltage', 'voltage'),
                    ('get_external_input_voltage', None, 'external_input_voltage', 'voltage'),
                    ('get_current_consumption', None, 'current_consumption', 'current'),
                    ('get_drive_mode', None, 'drive_mode', 'mode'),
                    ('is_status_led_enabled', None, 'status_led_enabled', 'enabled'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('set_velocity', 'velocity/set', ['velocity']),
                    ('set_acceleration', 'acceleration/set', ['acceleration']),
                    ('full_brake', 'full_brake/set', []),
                    ('enable', 'enable/set', []),
                    ('disable', 'disable/set', []),
                    ('set_pwm_frequency', 'pwm_frequency/set', ['frequency']),
                    ('set_drive_mode', 'drive_mode/set', ['mode']),
                    ('enable_status_led', 'enable_status_led/set', []),
                    ('disable_status_led', 'disable_status_led/set', []),
                    ('reset', 'reset/set', [])]

class BrickIMUProxy(DeviceProxy):
    DEVICE_CLASS = BrickIMU
    TOPIC_PREFIX = 'brick/imu'
    GETTER_SPECS = [('get_orientation', None, 'orientation', None),
                    ('get_quaternion', None, 'quaternion', None),
                    ('are_leds_on', None, 'leds_on', 'leds_on'),
                    ('get_convergence_speed', None, 'convergence_speed', 'speed'),
                    ('get_acceleration', None, 'acceleration', None),
                    ('get_magnetic_field', None, 'magnetic_field', None),
                    ('get_angular_velocity', None, 'angular_velocity', None),
                    ('get_all_data', None, 'all_data', None),
                    ('get_imu_temperature', None, 'imu_temperature', 'temperature'),
                    ('get_acceleration_range', None, 'acceleration_range', 'range'),
                    ('get_magnetometer_range', None, 'magnetometer_range', 'range'),
                    ('get_calibration',
                     {
                        'accelerometer_gain': (BrickIMU.CALIBRATION_TYPE_ACCELEROMETER_GAIN,),
                        'accelerometer_bias': (BrickIMU.CALIBRATION_TYPE_ACCELEROMETER_BIAS,),
                        'magnetometer_gain': (BrickIMU.CALIBRATION_TYPE_MAGNETOMETER_GAIN,),
                        'magnetometer_bias': (BrickIMU.CALIBRATION_TYPE_MAGNETOMETER_BIAS,),
                        'gyroscope_gain': (BrickIMU.CALIBRATION_TYPE_GYROSCOPE_GAIN,),
                        'gyroscope_bias': (BrickIMU.CALIBRATION_TYPE_GYROSCOPE_BIAS,)
                     },
                     'calibration', 'data'
                    ),
                    ('is_orientation_calculation_on', None, 'orientation_calculation_on', 'orientation_calculation_on'),
                    ('is_status_led_enabled', None, 'status_led_enabled', 'enabled'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('leds_on', 'leds_on/set', []),
                    ('leds_off', 'leds_off/set', []),
                    ('set_convergence_speed', 'convergence_speed/set', ['speed']),
                    ('set_acceleration_range', 'acceleration_range/set', ['range']),
                    ('set_magnetometer_range', 'magnetometer_range/set', ['range']),
                    ('set_calibration', 'calibration/set', ['typ', 'data']),
                    ('orientation_calculation_on', 'orientation_calculation_on/set', []),
                    ('orientation_calculation_off', 'orientation_calculation_off/set', []),
                    ('enable_status_led', 'enable_status_led/set', []),
                    ('disable_status_led', 'disable_status_led/set', []),
                    ('reset', 'reset/set', [])]

class BrickIMUV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickIMUV2
    TOPIC_PREFIX = 'brick/imu_v2'
    GETTER_SPECS = [('get_orientation', None, 'orientation', None),
                    ('get_linear_acceleration', None, 'linear_acceleration', None),
                    ('get_gravity_vector', None, 'gravity_vector', None),
                    ('get_quaternion', None, 'quaternion', None),
                    ('get_all_data', None, 'all_data', None),
                    ('are_leds_on', None, 'leds_on', 'leds'),
                    ('get_acceleration', None, 'acceleration', None),
                    ('get_magnetic_field', None, 'magnetic_field', None),
                    ('get_angular_velocity', None, 'angular_velocity', None),
                    ('get_temperature', None, 'temperature', 'temperature'),
                    ('get_sensor_configuration', None, 'sensor_configuration', None),
                    ('get_sensor_fusion_mode', None, 'sensor_fusion_mode', 'mode'),
                    ('is_status_led_enabled', None, 'status_led_enabled', 'enabled'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('leds_on', 'leds_on/set', []),
                    ('leds_off', 'leds_off/set', []),
                    ('set_sensor_configuration', 'sensor_configuration/set', ['magnetometer_rate', 'gyroscope_range', 'gyroscope_bandwidth', 'accelerometer_range', 'accelerometer_bandwidth']),
                    ('set_sensor_fusion_mode', 'sensor_fusion_mode/set', ['mode']),
                    ('enable_status_led', 'enable_status_led/set', []),
                    ('disable_status_led', 'disable_status_led/set', []),
                    ('reset', 'reset/set', [])]

class BrickMasterProxy(DeviceProxy):
    DEVICE_CLASS = BrickMaster
    TOPIC_PREFIX = 'brick/master'
    GETTER_SPECS = [('get_stack_voltage', None, 'stack_voltage', 'voltage'),
                    ('get_stack_current', None, 'stack_current', 'current'),
                    ('get_usb_voltage', None, 'usb_voltage', 'voltage'),
                    ('get_connection_type', None, 'connection_type', 'connection_type'),
                    ('is_status_led_enabled', None, 'status_led_enabled', 'enabled'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('enable_status_led', 'enable_status_led/set', []),
                    ('disable_status_led', 'disable_status_led/set', []),
                    ('reset', 'reset/set', [])]

class BrickServoProxy(DeviceProxy):
    DEVICE_CLASS = BrickServo
    TOPIC_PREFIX = 'brick/servo'
    GETTER_SPECS = [('is_enabled', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'enabled', 'enabled'),
                    ('get_position', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'position', 'position'),
                    ('get_current_position', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'current_position', 'position'),
                    ('get_velocity', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'velocity', 'velocity'),
                    ('get_current_velocity', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'current_velocity', 'velocity'),
                    ('get_acceleration', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'acceleration', 'acceleration'),
                    ('get_output_voltage', None, 'output_voltage', 'voltage'),
                    ('get_pulse_width', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'pulse_width', None),
                    ('get_degree', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'degree', None),
                    ('get_period', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'period', 'period'),
                    ('get_servo_current', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,)}, 'current', 'current'),
                    ('get_overall_current', None, 'overall_current', 'current'),
                    ('get_stack_input_voltage', None, 'stack_input_voltage', 'voltage'),
                    ('get_external_input_voltage', None, 'external_input_voltage', 'voltage'),
                    ('is_status_led_enabled', None, 'status_led_enabled', 'enabled'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('enable', 'enable/set', ['servo_num']),
                    ('disable', 'disable/set', ['servo_num']),
                    ('set_position', 'position/set', ['servo_num', 'position']),
                    ('set_velocity', 'velocity/set', ['servo_num', 'velocity']),
                    ('set_acceleration', 'acceleration/set', ['servo_num', 'acceleration']),
                    ('set_output_voltage', 'output_voltage/set', ['voltage']),
                    ('set_pulse_width', 'pulse_width/set', ['servo_num', 'min', 'max']),
                    ('set_degree', 'degree/set', ['servo_num', 'min', 'max']),
                    ('set_period', 'period/set', ['servo_num', 'period']),
                    ('enable_status_led', 'enable_status_led/set', []),
                    ('disable_status_led', 'disable_status_led/set', []),
                    ('reset', 'reset/set', [])]

class BrickSilentStepperProxy(DeviceProxy):
    DEVICE_CLASS = BrickSilentStepper
    TOPIC_PREFIX = 'brick/silent_stepper'
    GETTER_SPECS = [('get_max_velocity', None, 'max_velocity', 'velocity'),
                    ('get_current_velocity', None, 'current_velocity', 'velocity'),
                    ('get_speed_ramping', None, 'speed_ramping', None),
                    ('get_steps', None, 'steps', 'steps'),
                    ('get_remaining_steps', None, 'remaining_steps', 'steps'),
                    ('get_motor_current', None, 'motor_current', 'current'),
                    ('is_enabled', None, 'enabled', 'enabled'),
                    ('get_basic_configuration', None, 'basic_configuration', None),
                    ('get_current_position', None, 'current_position', 'position'),
                    ('get_target_position', None, 'target_position', 'position'),
                    ('get_step_configuration', None, 'step_configuration', None),
                    ('get_stack_input_voltage', None, 'stack_input_voltage', 'voltage'),
                    ('get_external_input_voltage', None, 'external_input_voltage', 'voltage'),
                    ('get_spreadcycle_configuration', None, 'spreadcycle_configuration', None),
                    ('get_stealth_configuration', None, 'stealth_configuration', None),
                    ('get_coolstep_configuration', None, 'coolstep_configuration', None),
                    ('get_misc_configuration', None, 'misc_configuration', None),
                    ('get_driver_status', None, 'driver_status', None),
                    ('get_time_base', None, 'time_base', None),
                    ('get_all_data', None, 'all_data', None),
                    ('is_status_led_enabled', None, 'status_led_enabled', 'enabled'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('set_max_velocity', 'max_velocity/set', ['velocity']),
                    ('set_speed_ramping', 'speed_ramping/set', ['acceleration', 'deacceleration']),
                    ('full_brake', 'full_brake/set', []),
                    ('set_steps', 'steps/set', ['steps']),
                    ('drive_forward', 'drive_forward/set', []),
                    ('drive_backward', 'drive_backward/set', []),
                    ('stop', 'stop/set', []),
                    ('set_motor_current', 'motor_current/set', ['current']),
                    ('enable', 'enable/set', []),
                    ('disable', 'disable/set', []),
                    ('set_basic_configuration', 'basic_configuration/set', ['standstill_current, motor_run_current', 'standstill_delay_time', 'power_down_time, stealth_threshold', 'coolstep_threshold', 'classic_threshold', 'high_velocity_chopper_mode']),
                    ('set_current_position', 'current_position/set', ['position']),
                    ('set_target_position', 'target_position/set', ['position']),
                    ('set_step_configuration', 'step_configuration/set', ['step_resolution', 'interpolation']),
                    ('set_spreadcycle_configuration', 'spreadcycle_configuration/set', ['slow_decay_duration', 'enable_random_slow_decay', 'fast_decay_duration', 'hysteresis_start_value', 'hysteresis_end_value', 'sine_wave_offset', 'chopper_mode', 'comparator_blank_time', 'fast_decay_without_comparator']),
                    ('set_stealth_configuration', 'stealth_configuration/set', ['enable_stealth', 'amplitude', 'gradient', 'enable_autoscale', 'force_symmetric', 'freewheel_mode']),
                    ('set_coolstep_configuration', 'coolstep_configuration/set', ['minimum_stallguard_value', 'maximum_stallguard_value', 'current_up_step_width', 'current_down_step_width', 'minimum_current', 'stallguard_threshold_value', 'stallguard_mode']),
                    ('set_misc_configuration', 'misc_configuration/set', ['disable_short_to_ground_protection', 'synchronize_phase_frequency']),
                    ('set_time_base', 'time_base/set', ['time_base']),
                    ('enable_status_led', 'enable_status_led/set', []),
                    ('disable_status_led', 'disable_status_led/set', []),
                    ('reset', 'reset/set', [])]

class BrickStepperProxy(DeviceProxy):
    DEVICE_CLASS = BrickStepper
    TOPIC_PREFIX = 'brick/stepper'
    GETTER_SPECS = [('get_max_velocity', None, 'max_velocity', 'velocity'),
                    ('get_current_velocity', None, 'current_velocity', 'velocity'),
                    ('get_speed_ramping', None, 'speed_ramping', None),
                    ('get_steps', None, 'steps', 'steps'),
                    ('get_remaining_steps', None, 'remaining_steps', 'steps'),
                    ('get_motor_current', None, 'motor_current', 'current'),
                    ('is_enabled', None, 'enabled', 'enabled'),
                    ('get_current_position', None, 'current_position', 'position'),
                    ('get_target_position', None, 'target_position', 'position'),
                    ('get_step_mode', None, 'step_mode', 'mode'),
                    ('get_stack_input_voltage', None, 'stack_input_voltage', 'voltage'),
                    ('get_external_input_voltage', None, 'external_input_voltage', 'voltage'),
                    ('get_current_consumption', None, 'current_consumption', 'current'),
                    ('get_decay', None, 'decay', 'decay'),
                    ('is_sync_rect', None, 'sync_rect', 'sync_rect'),
                    ('get_time_base', None, 'time_base', 'time_base'),
                    ('get_all_data', None, 'all_data', None),
                    ('is_status_led_enabled', None, 'status_led_enabled', 'enabled'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('set_max_velocity', 'max_velocity/set', ['velocity']),
                    ('set_speed_ramping', 'speed_ramping/set', ['acceleration', 'deacceleration']),
                    ('full_brake', 'full_brake/set', []),
                    ('set_steps', 'steps/set', ['steps']),
                    ('drive_forward', 'drive_forward/set', []),
                    ('drive_backward', 'drive_backward/set', []),
                    ('stop', 'stop/set', []),
                    ('set_motor_current', 'motor_current/set', ['current']),
                    ('enable', 'enable/set', []),
                    ('disable', 'disable/set', []),
                    ('set_current_position', 'current_position/set', ['position']),
                    ('set_target_position', 'target_position/set', ['position']),
                    ('set_step_mode', 'step_mode/set', ['mode']),
                    ('set_decay', 'decay/set', ['decay']),
                    ('set_sync_rect', 'sync_rect/set', ['sync_rect']),
                    ('set_time_base', 'time_base/set', ['time_base']),
                    ('enable_status_led', 'enable_status_led/set', []),
                    ('disable_status_led', 'disable_status_led/set', []),
                    ('reset', 'reset/set', [])]

class BrickletAccelerometerProxy(DeviceProxy):
    DEVICE_CLASS = BrickletAccelerometer
    TOPIC_PREFIX = 'bricklet/accelerometer'
    GETTER_SPECS = [('get_acceleration', None, 'acceleration', None),
                    ('get_temperature', None, 'temperature', 'temperature'),
                    ('get_configuration', None, 'configuration', None),
                    ('is_led_on', None, 'led_on', 'on')]
    SETTER_SPECS = [('set_configuration', 'configuration/set', ['data_rate', 'full_scale', 'filter_bandwidth']),
                    ('led_on', 'led_on/set', []),
                    ('led_off', 'led_off/set', [])]

# FIXME: expose analog_value getter?
class BrickletAmbientLightProxy(DeviceProxy):
    DEVICE_CLASS = BrickletAmbientLight
    TOPIC_PREFIX = 'bricklet/ambient_light'
    GETTER_SPECS = [('get_illuminance', None, 'illuminance', 'illuminance')]

class BrickletAmbientLightV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletAmbientLightV2
    TOPIC_PREFIX = 'bricklet/ambient_light_v2'
    GETTER_SPECS = [('get_illuminance', None, 'illuminance', 'illuminance'),
                    ('get_configuration', None, 'configuration', None)]
    SETTER_SPECS = [('set_configuration', 'configuration/set', ['illuminance_range', 'integration_time'])]

# FIXME: expose analog_value getter?
class BrickletAnalogInProxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogIn
    TOPIC_PREFIX = 'bricklet/analog_in'
    GETTER_SPECS = [('get_voltage', None, 'voltage', 'voltage'),
                    ('get_range', None, 'range', 'range'),
                    ('get_averaging', None, 'averaging', 'average')]
    SETTER_SPECS = [('set_range', 'range/set', ['range']),
                    ('set_averaging', 'averaging/set', ['average'])]

# FIXME: expose analog_value getter?
class BrickletAnalogInV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogInV2
    TOPIC_PREFIX = 'bricklet/analog_in_v2'
    GETTER_SPECS = [('get_voltage', None, 'voltage', 'voltage'),
                    ('get_moving_average', None, 'moving_average', 'average')]
    SETTER_SPECS = [('set_moving_average', 'moving_average/set', ['average'])]

class BrickletAnalogOutProxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogOut
    TOPIC_PREFIX = 'bricklet/analog_out'
    GETTER_SPECS = [('get_voltage', None, 'voltage', 'voltage'),
                    ('get_mode', None, 'mode', 'mode')]
    SETTER_SPECS = [('set_voltage', 'voltage/set', ['voltage']),
                    ('set_mode', 'mode/set', ['mode'])]

class BrickletAnalogOutV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogOutV2
    TOPIC_PREFIX = 'bricklet/analog_out_v2'
    GETTER_SPECS = [('get_output_voltage', None, 'output_voltage', 'voltage'),
                    ('get_input_voltage', None, 'input_voltage', 'voltage')]
    SETTER_SPECS = [('set_output_voltage', 'output_voltage/set', ['voltage'])]

class BrickletAnalogInV3Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogInV3
    TOPIC_PREFIX = 'bricklet/analog_in_v3'
    GETTER_SPECS = [('get_voltage', None, 'voltage', 'voltage')]

class BrickletBarometerProxy(DeviceProxy):
    DEVICE_CLASS = BrickletBarometer
    TOPIC_PREFIX = 'bricklet/barometer'
    GETTER_SPECS = [('get_air_pressure', None, 'air_pressure', 'air_pressure'),
                    ('get_altitude', None, 'altitude', 'altitude'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature'),
                    ('get_reference_air_pressure', None, 'reference_air_pressure', 'air_pressure'),
                    ('get_averaging', None, 'averaging', None)]
    SETTER_SPECS = [('set_reference_air_pressure', 'reference_air_pressure/set', ['air_pressure']),
                    ('set_averaging', 'averaging/set', ['moving_average_pressure', 'average_pressure', 'average_temperature'])]

class BrickletCANProxy(DeviceProxy):
    DEVICE_CLASS = BrickletCAN
    TOPIC_PREFIX = 'bricklet/can'
    GETTER_SPECS = [('read_frame', None, 'read_frame', None),
                    ('get_configuration', None, 'configuration', None),
                    ('get_read_filter', None, 'read_filter', None),
                    ('get_error_log', None, 'error_log', None)]
    SETTER_SPECS = [(None, 'write_frame/set', ['frame_type', 'identifier', 'data', 'length'], {'getter_name': 'write_frame', 'getter_publish_topic': 'write_frame', 'getter_return_value': 'success'}),
                    ('set_configuration', 'configuration/set', ['baud_rate', 'transceiver_mode', 'write_timeout']),
                    ('set_read_filter', 'read_filter/set', ['mode', 'mask', 'filter1', 'filter2'])]

    # Arguments required for a getter must be published to "<GETTER-NAME>/set"
    # topic which will execute the getter with the provided arguments.
    # The output of the getter then will be published on the "<GETTER-NAME>"
    # topic.

class BrickletCO2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletCO2
    TOPIC_PREFIX = 'bricklet/co2'
    GETTER_SPECS = [('get_co2_concentration', None, 'co2_concentration', 'co2_concentration')]

class BrickletColorProxy(DeviceProxy):
    DEVICE_CLASS = BrickletColor
    TOPIC_PREFIX = 'bricklet/color'
    GETTER_SPECS = [('get_color', None, 'color', None),
                    ('get_illuminance', None, 'illuminance', 'illuminance'),
                    ('get_color_temperature', None, 'color_temperature', 'color_temperature'),
                    ('get_config', None, 'config', None),
                    ('is_light_on', None, 'light_on', 'light')]
    SETTER_SPECS = [('set_config', 'config/set', ['gain', 'integration_time']),
                    ('light_on', 'light_on/set', []),
                    ('light_off', 'light_off/set', [])]

# FIXME: expose analog_value getter?
# FIXME: handle over_current callback?
class BrickletCurrent12Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletCurrent12
    TOPIC_PREFIX = 'bricklet/current12'
    GETTER_SPECS = [('get_current', None, 'current', 'current'),
                    ('is_over_current', None, 'over_current', 'over')]
    SETTER_SPECS = [('calibrate', 'calibrate/set', [])]

# FIXME: expose analog_value getter?
# FIXME: handle over_current callback?
class BrickletCurrent25Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletCurrent25
    TOPIC_PREFIX = 'bricklet/current25'
    GETTER_SPECS = [('get_current', None, 'current', 'current'),
                    ('is_over_current', None, 'over_current', 'over')]
    SETTER_SPECS = [('calibrate', 'calibrate/set', [])]

# FIXME: expose analog_value getter?
# FIXME: expose sampling_point getter/setter?
class BrickletDistanceIRProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDistanceIR
    TOPIC_PREFIX = 'bricklet/distance_ir'
    GETTER_SPECS = [('get_distance', None, 'distance', 'distance')]

class BrickletDistanceUSProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDistanceUS
    TOPIC_PREFIX = 'bricklet/distance_us'
    GETTER_SPECS = [('get_distance_value', None, 'distance_value', 'distance'),
                    ('get_moving_average', None, 'moving_average', 'average')]
    SETTER_SPECS = [('set_moving_average', 'moving_average/set', ['average'])]

class BrickletDMXProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDMX
    TOPIC_PREFIX = 'bricklet/dmx'
    GETTER_SPECS = [('get_dmx_mode', None, 'dmx_mode', 'dmx_mode'),
                    ('read_frame', None, 'read_frame', None),
                    ('get_frame_duration', None, 'frame_duration', 'frame_duration'),
                    ('get_frame_error_count', None, 'frame_error_count', None),
                    ('get_communication_led_config', None, 'communication_led_config', 'config'),
                    ('get_error_led_config', None, 'error_led_config', 'config'),
                    ('get_status_led_config', None, 'status_led_config', 'config'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('set_dmx_mode', 'dmx_mode/set', ['dmx_mode']),
                    ('write_frame', 'write_frame/set', ['frame']),
                    ('set_frame_duration', 'frame_duration/set', ['frame_duration']),
                    ('set_communication_led_config', 'communication_led_config/set', ['config']),
                    ('set_error_led_config', 'error_led_config/set', ['config']),
                    ('set_status_led_config', 'status_led_config/set', ['config']),
                    ('reset', 'reset/set', [])]

class BrickletDualButtonProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDualButton
    TOPIC_PREFIX = 'bricklet/dual_button'
    SETTER_SPECS = [('set_led_state', 'led_state/set', ['led_l', 'led_r']),
                    ('set_selected_led_state', 'selected_led_state/set', ['led', 'state'])]

    def cb_state_changed(self, button_l, button_r, led_l, led_r):
        self.publish_values('button_state', button_l=button_l, button_r=button_r)
        self.publish_values('led_state', led_l=led_l, led_r=led_r)

    def setup_callbacks(self):
        try:
            button_l, button_r = self.device.get_button_state()
            self.publish_values('button_state', button_l=button_l, button_r=button_r)
        except:
            pass

        try:
            led_l, led_r = self.device.get_led_state()
            self.publish_values('led_state', led_l=led_l, led_r=led_r)
        except:
            pass

        self.device.register_callback(BrickletDualButton.CALLBACK_STATE_CHANGED,
                                      self.cb_state_changed)

# FIXME: get_monoflop needs special handling
# FIXME: handle monoflop_done callback?
class BrickletDualRelayProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDualRelay
    TOPIC_PREFIX = 'bricklet/dual_relay'
    GETTER_SPECS = [('get_state', None, 'state', None)]
    SETTER_SPECS = [('set_state', 'state/set', ['relay1', 'relay2']),
                    ('set_monoflop', 'monoflop/set', ['relay', 'state', 'time']),
                    ('set_selected_state', 'selected_state/set', ['relay', 'state'])]

class BrickletDustDetectorProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDustDetector
    TOPIC_PREFIX = 'bricklet/dust_detector'
    GETTER_SPECS = [('get_dust_density', None, 'dust_density', 'dust_density'),
                    ('get_moving_average', None, 'moving_average', 'average')]
    SETTER_SPECS = [('set_moving_average', 'moving_average/set', ['average'])]

# FIXME: get_coordinates, get_altitude and get_motion need special status handling to avoid publishing invalid data
class BrickletGPSProxy(DeviceProxy):
    DEVICE_CLASS = BrickletGPS
    TOPIC_PREFIX = 'bricklet/gps'
    GETTER_SPECS = [('get_status', None, 'status', None),
                    ('get_coordinates', None, 'coordinates', None),
                    ('get_altitude', None, 'altitude', None),
                    ('get_motion', None, 'motion', None),
                    ('get_date_time', None, 'date_time', 'date_time')]
    SETTER_SPECS = [('restart', 'restart/set', ['restart_type'])]

class BrickletGPSV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletGPSV2
    TOPIC_PREFIX = 'bricklet/gps_v2'
    GETTER_SPECS = [('get_coordinates', None, 'coordinates', None),
                    ('get_status', None, 'status', None),
                    ('get_altitude', None, 'altitude', None),
                    ('get_motion', None, 'motion', None),
                    ('get_date_time', None, 'date_time', None),
                    ('get_satellite_system_status', {'gps': (BrickletGPSV2.SATELLITE_SYSTEM_GPS,), 'glonass': (BrickletGPSV2.SATELLITE_SYSTEM_GLONASS,), 'galileo': (BrickletGPSV2.SATELLITE_SYSTEM_GALILEO,)}, 'satellite_system_status', None),
                    ('get_fix_led_config', None, 'fix_led_config', 'config'),
                    ('get_sbas_config', None, 'sbas_config', 'sbas_config'),
                    ('get_status_led_config', None, 'status_led_config', 'config'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('restart', 'restart/set', ['restart_type']),
                    ('set_fix_led_config', 'fix_led_config/set', ['config']),
                    ('set_sbas_config', 'sbas_config/set', ['sbas_config']),
                    ('set_status_led_config', 'status_led_config/set', ['config']),
                    ('reset', 'reset/set', [])]

    def update_extra_getters(self):
        result = [[None] * 32] * 3

        for i, system in enumerate([BrickletGPSV2.SATELLITE_SYSTEM_GPS, BrickletGPSV2.SATELLITE_SYSTEM_GLONASS, BrickletGPSV2.SATELLITE_SYSTEM_GALILEO]):
            for k in range(32):
                try:
                    status = self.device.get_satellite_status(system, k + 1)
                except:
                    continue

                result[i][k] = {}

                for field in status._fields:
                    result[i][k][field] = getattr(status, field)

        payload = {
            'gps': result[0],
            'glonass': result[1],
            'galileo': result[2]
        }

        self.publish_values('satellite_status', **payload)

# FIXME: get_edge_count needs special handling
class BrickletHallEffectProxy(DeviceProxy):
    DEVICE_CLASS = BrickletHallEffect
    TOPIC_PREFIX = 'bricklet/hall_effect'
    GETTER_SPECS = [('get_value', None, 'value', 'value'),
                    ('get_edge_count_config', None, 'edge_count_config', None)]
    SETTER_SPECS = [('set_edge_count_config', 'edge_count_config/set', ['edge_type', 'debounce'])]

# FIXME: expose analog_value getter?
class BrickletHumidityProxy(DeviceProxy):
    DEVICE_CLASS = BrickletHumidity
    TOPIC_PREFIX = 'bricklet/humidity'
    GETTER_SPECS = [('get_humidity', None, 'humidity', 'humidity')]

class BrickletHumidityV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletHumidityV2
    TOPIC_PREFIX = 'bricklet/humidity_v2'
    GETTER_SPECS = [('get_humidity', None, 'humidity', 'humidity'),
                    ('get_temperature', None, 'temperature', 'temperature'),
                    ('get_heater_configuration', None, 'heater_configuration', 'heater_config'),
                    ('get_moving_average_configuration', None, 'moving_average_configuration', None),
                    ('get_status_led_config', None, 'status_led_config', 'config'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('set_heater_configuration', 'heater_configuration/set', ['heater_config']),
                    ('set_moving_average_configuration', 'moving_average_configuration/set', ['moving_average_length_humidity', 'moving_average_length_temperature']),
                    ('set_status_led_config', 'status_led_config/set', ['config']),
                    ('reset', 'reset/set', [])]

class BrickletIndustrialAnalogOutProxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialAnalogOut
    TOPIC_PREFIX = 'bricklet/industrial_analog_out'
    GETTER_SPECS = [('get_voltage', None, 'voltage', 'voltage'),
                    ('get_current', None, 'current', 'current'),
                    ('get_configuration', None, 'configuration', None),
                    ('is_enabled', None, 'enabled', 'enabled')]
    SETTER_SPECS = [('set_voltage', 'voltage/set', ['voltage']),
                    ('set_current', 'current/set', ['current']),
                    ('set_configuration', 'configuration/set', ['voltage_range', 'current_range']),
                    ('enable', 'enable/set', []),
                    ('disable', 'disable/set', [])]

# FIXME: get_edge_count and get_edge_count_config need special handling
# FIXME: handle interrupt callback, including get_interrupt and set_interrupt?
class BrickletIndustrialDigitalIn4Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialDigitalIn4
    TOPIC_PREFIX = 'bricklet/industrial_digital_in_4'
    GETTER_SPECS = [('get_value', None, 'value', 'value_mask'),
                    ('get_group', None, 'group', 'group'),
                    ('get_available_for_group', None, 'available_for_group', 'available')]
    SETTER_SPECS = [('set_edge_count_config', 'edge_count_config/set', ['edge_type', 'debounce']),
                    ('set_group', 'group/set', ['group'])]

# FIXME: get_monoflop needs special handling
# FIXME: handle monoflop_done callback?
class BrickletIndustrialDigitalOut4Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialDigitalOut4
    TOPIC_PREFIX = 'bricklet/industrial_digital_out_4'
    GETTER_SPECS = [('get_value', None, 'value', 'value_mask'),
                    ('get_group', None, 'group', 'group'),
                    ('get_available_for_group', None, 'available_for_group', 'available')]
    SETTER_SPECS = [('set_value', 'value/set', ['value_mask']),
                    ('set_selected_values', 'selected_values/set', ['selection_mask', 'value_mask']),
                    ('set_monoflop', 'monoflop/set', ['selection_mask', 'value_mask', 'time']),
                    ('set_group', 'group/set', ['group'])]

# FIXME: get_current needs special handling
class BrickletIndustrialDual020mAProxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialDual020mA
    TOPIC_PREFIX = 'bricklet/industrial_dual_0_20ma'
    GETTER_SPECS = [('get_sample_rate', None, 'sample_rate', 'rate')]
    SETTER_SPECS = [('set_sample_rate', None, 'sample_rate/set', ['rate'])]

# FIXME: get_voltage needs special handling
class BrickletIndustrialDualAnalogInProxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialDualAnalogIn
    TOPIC_PREFIX = 'bricklet/industrial_dual_analog_in'
    GETTER_SPECS = [('get_sample_rate', None, 'sample_rate', 'rate'),
                    ('get_calibration', None, 'calibration', None),
                    ('get_adc_values', None, 'adc_values', 'value')]
    SETTER_SPECS = [('set_sample_rate', 'sample_rate/set', ['rate']),
                    ('set_calibration', 'calibration/set', ['offset', 'gain'])]

# FIXME: get_monoflop needs special handling
# FIXME: handle monoflop_done callback?
class BrickletIndustrialQuadRelayProxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialQuadRelay
    TOPIC_PREFIX = 'bricklet/industrial_quad_relay'
    GETTER_SPECS = [('get_value', None, 'value', 'value_mask'),
                    ('get_group', None, 'group', 'group'),
                    ('get_available_for_group', None, 'available_for_group', 'available')]
    SETTER_SPECS = [('set_value', 'value/set', ['value_mask']),
                    ('set_selected_values', 'selected_values/set', ['selection_mask', 'value_mask']),
                    ('set_monoflop', 'monoflop/set', ['selection_mask', 'value_mask', 'time']),
                    ('set_group', 'group/set', ['group'])]

# FIXME: get_edge_count, get_port_monoflop and get_edge_count_config need special handling
# FIXME: handle monoflop_done callback?
# FIXME: handle interrupt callback, including get_port_interrupt and set_port_interrupt?
class BrickletIO16Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletIO16
    TOPIC_PREFIX = 'bricklet/io16'
    GETTER_SPECS = [('get_port', {'a': ('a',), 'b': ('b',)}, 'port', 'value_mask'),
                    ('get_port_configuration', {'a': ('a',), 'b': ('b',)}, 'port_configuration', None)]
    SETTER_SPECS = [('set_port', 'port/set', ['port', 'value_mask']),
                    ('set_port_configuration', 'port_configuration/set', ['port', 'selection_mask', 'direction', 'value']),
                    ('set_port_monoflop', 'port_monoflop/set', ['port', 'selection_mask', 'value_mask', 'time']),
                    ('set_selected_values', 'selected_values/set', ['port', 'selection_mask', 'value_mask']),
                    ('set_edge_count_config', 'edge_count_config/set', ['port', 'edge_type', 'debounce'])]

# FIXME: get_edge_count, get_monoflop and get_edge_count_config need special handling
# FIXME: handle monoflop_done callback?
# FIXME: handle interrupt callback, including get_interrupt and set_interrupt?
class BrickletIO4Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletIO4
    TOPIC_PREFIX = 'bricklet/io4'
    GETTER_SPECS = [('get_value', None, 'value', 'value_mask'),
                    ('get_configuration', None, 'configuration', None)]
    SETTER_SPECS = [('set_value', 'value/set', ['value_mask']),
                    ('set_configuration', 'configuration/set', ['selection_mask', 'direction', 'value']),
                    ('set_monoflop', 'monoflop/set', ['selection_mask', 'value_mask', 'time']),
                    ('set_selected_values', 'selected_values/set', ['selection_mask', 'value_mask']),
                    ('set_edge_count_config', 'edge_count_config/set', ['edge_type', 'debounce'])]

# FIXME: expose analog_value getter?
class BrickletJoystickProxy(DeviceProxy):
    DEVICE_CLASS = BrickletJoystick
    TOPIC_PREFIX = 'bricklet/joystick'
    GETTER_SPECS = [('get_position', None, 'position', None)]
    SETTER_SPECS = [('calibrate', 'calibrate/set', [])]

    def cb_pressed(self):
        self.publish_values('pressed', pressed=True)

    def cb_released(self):
        self.publish_values('pressed', pressed=False)

    def setup_callbacks(self):
        try:
            self.publish_values('pressed', pressed=self.device.is_pressed())
        except:
            pass

        self.device.register_callback(BrickletJoystick.CALLBACK_PRESSED,
                                      self.cb_pressed)
        self.device.register_callback(BrickletJoystick.CALLBACK_RELEASED,
                                      self.cb_released)

class BrickletLaserRangeFinderProxy(DeviceProxy):
    DEVICE_CLASS = BrickletLaserRangeFinder
    TOPIC_PREFIX = 'bricklet/laser_range_finder'
    GETTER_SPECS = [('get_distance', None, 'distance', 'distance'),
                    ('get_velocity', None, 'velocity', 'velocity'),
                    ('get_mode', None, 'mode', 'mode'),
                    ('is_laser_enabled', None, 'laser_enabled', 'laser_enabled'),
                    ('get_moving_average', None, 'moving_average', None)]
    SETTER_SPECS = [('set_mode', 'mode/set', ['mode']),
                    ('enable_laser', 'enable_laser/set', []),
                    ('disable_laser', 'disable_laser/set', []),
                    ('set_moving_average', 'moving_average/set', ['distance_average_length', 'velocity_average_length'])]

class BrickletLCD16x2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletLCD16x2
    TOPIC_PREFIX = 'bricklet/lcd_16x2'
    GETTER_SPECS = [('is_backlight_on', None, 'backlight_on', 'backlight'),
                    ('get_config', None, 'config', None),
                    ('get_custom_character', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,), '7': (7,)}, 'custom_character', 'character')]
    SETTER_SPECS = [('write_line', 'write_line/set', ['line', 'position', 'text']),
                    ('clear_display', 'clear_display/set', []),
                    ('backlight_on', 'backlight_on/set', []),
                    ('backlight_off', 'backlight_off/set', []),
                    ('set_config', 'config/set', ['cursor', 'blinking']),
                    ('set_custom_character', 'custom_character/set', ['index', 'character'])]

    def cb_button_pressed(self, button):
        self.last_button_pressed[str(button)] = True
        self.publish_values('button_pressed', **self.last_button_pressed)

    def cb_button_released(self, button):
        self.last_button_pressed[str(button)] = False
        self.publish_values('button_pressed', **self.last_button_pressed)

    def setup_callbacks(self):
        self.last_button_pressed = {'0': False, '1': False, '2': False}

        for button in range(3):
            try:
                self.last_button_pressed[str(button)] = self.device.is_button_pressed(button)
            except:
                pass

        self.publish_values('button_pressed', **self.last_button_pressed)

        self.device.register_callback(BrickletLCD16x2.CALLBACK_BUTTON_PRESSED,
                                      self.cb_button_pressed)
        self.device.register_callback(BrickletLCD16x2.CALLBACK_BUTTON_RELEASED,
                                      self.cb_button_released)

class BrickletLCD20x4Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletLCD20x4
    TOPIC_PREFIX = 'bricklet/lcd_20x4'
    GETTER_SPECS = [('is_backlight_on', None, 'backlight_on', 'backlight'),
                    ('get_config', None, 'config', None),
                    ('get_custom_character', {'0': (0,), '1': (1,), '2': (2,), '3': (3,), '4': (4,), '5': (5,), '6': (6,), '7': (7,)}, 'custom_character', 'character'),
                    ('get_default_text', {'0': (0,), '1': (1,), '2': (2,), '3': (3,)}, 'default_text', 'text'),
                    ('get_default_text_counter', None, 'default_text_counter', 'counter')]
    SETTER_SPECS = [('write_line', 'write_line/set', ['line', 'position', 'text']),
                    ('clear_display', 'clear_display/set', []),
                    ('backlight_on', 'backlight_on/set', []),
                    ('backlight_off', 'backlight_off/set', []),
                    ('set_config', 'config/set', ['cursor', 'blinking']),
                    ('set_custom_character', 'custom_character/set', ['index', 'character']),
                    ('set_default_text', 'default_text/set', ['line', 'text']),
                    ('set_default_text_counter', 'default_text_counter/set', ['counter'])]

    def cb_button_pressed(self, button):
        self.last_button_pressed[str(button)] = True
        self.publish_values('button_pressed', **self.last_button_pressed)

    def cb_button_released(self, button):
        self.last_button_pressed[str(button)] = False
        self.publish_values('button_pressed', **self.last_button_pressed)

    def setup_callbacks(self):
        self.last_button_pressed = {'0': False, '1': False, '2': False, '3': False}

        for button in range(4):
            try:
                self.last_button_pressed[str(button)] = self.device.is_button_pressed(button)
            except:
                pass

        self.publish_values('button_pressed', **self.last_button_pressed)

        self.device.register_callback(BrickletLCD20x4.CALLBACK_BUTTON_PRESSED,
                                      self.cb_button_pressed)
        self.device.register_callback(BrickletLCD20x4.CALLBACK_BUTTON_RELEASED,
                                      self.cb_button_released)

class BrickletLEDStripProxy(DeviceProxy):
    DEVICE_CLASS = BrickletLEDStrip
    TOPIC_PREFIX = 'bricklet/led_strip'
    GETTER_SPECS = [('get_rgb_values', None, 'rgb_values', None),
                    ('get_frame_duration', None, 'frame_duration', 'duration'),
                    ('get_supply_voltage', None, 'supply_voltage', 'voltage'),
                    ('get_clock_frequency', None, 'clock_frequency', 'frequency'),
                    ('get_chip_type', None, 'chip_type', 'chip')]
    SETTER_SPECS = [('set_rgb_values', 'rgb_values/set', ['index', 'length', 'r', 'g', 'b']),
                    ('set_frame_duration', 'frame_duration/set', ['duration']),
                    ('set_clock_frequency', 'clock_frequency/set', ['frequency']),
                    ('set_chip_type', 'chip_type/set', ['chip'])]

class BrickletLineProxy(DeviceProxy):
    DEVICE_CLASS = BrickletLine
    TOPIC_PREFIX = 'bricklet/line'
    GETTER_SPECS = [('get_reflectivity', None, 'reflectivity', 'reflectivity')]

# FIXME: expose analog_value getter?
class BrickletLinearPotiProxy(DeviceProxy):
    DEVICE_CLASS = BrickletLinearPoti
    TOPIC_PREFIX = 'bricklet/linear_poti'
    GETTER_SPECS = [('get_position', None, 'position', 'position')]

class BrickletLoadCellProxy(DeviceProxy):
    DEVICE_CLASS = BrickletLoadCell
    TOPIC_PREFIX = 'bricklet/load_cell'
    GETTER_SPECS = [('get_weight', None, 'weight', 'weight'),
                    ('is_led_on', None, 'led_on', 'on'),
                    ('get_moving_average', None, 'moving_average', 'average'),
                    ('get_configuration', None, 'configuration', None)]
    SETTER_SPECS = [('led_on', 'led_on/set', []),
                    ('led_off', 'led_off/set', []),
                    ('set_moving_average', 'moving_average/set', ['average']),
                    ('set_configuration', 'configuration/set', ['rate', 'gain']),
                    ('tare', 'tare/set', [])]

class BrickletMoistureProxy(DeviceProxy):
    DEVICE_CLASS = BrickletMoisture
    TOPIC_PREFIX = 'bricklet/moisture'
    GETTER_SPECS = [('get_moisture_value', None, 'moisture_value', 'moisture'),
                    ('get_moving_average', None, 'moving_average', 'average')]
    SETTER_SPECS = [('set_moving_average', 'moving_average/set', ['average'])]

# FIXME: handle motion_detected and detection_cycle_ended callbacks?
class BrickletMotionDetectorProxy(DeviceProxy):
    DEVICE_CLASS = BrickletMotionDetector
    TOPIC_PREFIX = 'bricklet/motion_detector'
    GETTER_SPECS = [('get_motion_detected', None, 'motion_detected', 'motion')]

class BrickletMotionDetectorV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletMotionDetectorV2
    TOPIC_PREFIX = 'bricklet/motion_detector_v2'
    GETTER_SPECS = [('get_motion_detected', None, 'motion_detected', 'motion')]

class BrickletMotorizedLinearPotiProxy(DeviceProxy):
    DEVICE_CLASS = BrickletMotorizedLinearPoti
    TOPIC_PREFIX = 'bricklet/motorized_linear_poti'
    GETTER_SPECS = [('get_position', None, 'position', 'position'),
                    ('get_motor_position', None, 'motor_position', None),
                    ('get_status_led_config', None, 'status_led_config', ['config']),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('set_motor_position', 'motor_position/set', ['position', 'drive_mode', 'hold_position']),
                    ('calibrate', 'calibrate/set', []),
                    ('set_status_led_config', 'status_led_config/set', ['config']),
                    ('reset', 'reset/set', [])]

class BrickletMultiTouchProxy(DeviceProxy):
    DEVICE_CLASS = BrickletMultiTouch
    TOPIC_PREFIX = 'bricklet/multi_touch'
    GETTER_SPECS = [('get_electrode_config', None, 'electrode_config', 'enabled_electrodes'),
                    ('get_electrode_sensitivity', None, 'electrode_sensitivity', 'sensitivity')]
    SETTER_SPECS = [('recalibrate', 'recalibrate/set', []),
                    ('set_electrode_config', 'electrode_config/set', ['enabled_electrodes']),
                    ('set_electrode_sensitivity', 'electrode_sensitivity/set', ['sensitivity'])]

    def cb_touch_state(self, state):
        self.publish_values('touch_state', state=state)

    def setup_callbacks(self):
        try:
            self.publish_values('touch_state', state=self.device.get_touch_state())
        except:
            pass

        self.device.register_callback(BrickletMultiTouch.CALLBACK_TOUCH_STATE,
                                      self.cb_touch_state)

class BrickletNFCRFIDProxy(DeviceProxy):
    DEVICE_CLASS = BrickletNFCRFID
    TOPIC_PREFIX = 'bricklet/nfc_rfid'
    GETTER_SPECS = [('get_tag_id', None, 'tag_id', None),
                    ('get_state', None, 'state', None),
                    ('get_page', None, 'page', 'page')]
    SETTER_SPECS = [('request_tag_id', 'request_tag_id/set', ['tag_type']),
                    ('authenticate_mifare_classic_page', 'authenticate_mifare_classic_page/set', ['page', 'key_number', 'key']),
                    ('write_page', 'write_page/set', ['page', 'data']),
                    ('request_page', 'request_page/set', ['page'])]

class BrickletOLED128x64Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletOLED128x64
    TOPIC_PREFIX = 'bricklet/oled_128x64'
    GETTER_SPECS = [('get_display_configuration', None, 'display_configuration', None)]
    SETTER_SPECS = [('write', 'write/set', ['data']),
                    ('new_window', 'new_window/set', ['column_from', 'column_to', 'row_from', 'row_to']),
                    ('clear_display', 'clear_display/set', []),
                    ('write_line', 'write_line/set', ['line', 'position', 'text']),
                    ('set_display_configuration', 'display_configuration/set', ['contrast', 'invert'])]

class BrickletOLED64x48Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletOLED64x48
    TOPIC_PREFIX = 'bricklet/oled_64x48'
    GETTER_SPECS = [('get_display_configuration', None, 'display_configuration', None)]
    SETTER_SPECS = [('write', 'write/set', ['data']),
                    ('new_window', 'new_window/set', ['column_from', 'column_to', 'row_from', 'row_to']),
                    ('clear_display', 'clear_display/set', []),
                    ('write_line', 'write_line/set', ['line', 'position', 'text']),
                    ('set_display_configuration', 'display_configuration/set', ['contrast', 'invert'])]

class BrickletPiezoBuzzerProxy(DeviceProxy):
    DEVICE_CLASS = BrickletPiezoBuzzer
    TOPIC_PREFIX = 'bricklet/piezo_buzzer'
    SETTER_SPECS = [('beep', 'beep/set', ['duration']),
                    ('morse_code', 'morse_code/set', ['morse'])]

# FIXME: handle beep_finished and morse_code_finished callback?
# FIXME: expose calibrate setter?
class BrickletPiezoSpeakerProxy(DeviceProxy):
    DEVICE_CLASS = BrickletPiezoSpeaker
    TOPIC_PREFIX = 'bricklet/piezo_speaker'
    SETTER_SPECS = [('beep', 'beep/set', ['duration', 'frequency']),
                    ('morse_code', 'morse_code/set', ['morse', 'frequency'])]

class BrickletOutdoorWeatherProxy(DeviceProxy):
    DEVICE_CLASS = BrickletOutdoorWeather
    TOPIC_PREFIX = 'bricklet/outdoor_weather'

    def update_extra_getters(self):
        # stations
        try:
            identifiers = self.device.get_station_identifiers()
        except:
            identifiers = []

        payload = {}

        for identifier in identifiers:
            data = self.device.get_station_data(identifier)
            payload[str(identifier)] = {}

            for field in data._fields:
                payload[str(identifier)][field] = getattr(data, field)

        self.publish_values('station_data', **payload)

        # sensors
        try:
            identifiers = self.device.get_sensor_identifiers()
        except:
            identifiers = []

        payload = {}

        for identifier in identifiers:
            data = self.device.get_sensor_data(identifier)
            payload[str(identifier)] = {}

            for field in data._fields:
                payload[str(identifier)][field] = getattr(data, field)

        self.publish_values('sensor_data', **payload)

class BrickletPTCProxy(DeviceProxy):
    DEVICE_CLASS = BrickletPTC
    TOPIC_PREFIX = 'bricklet/ptc'
    GETTER_SPECS = [('get_temperature', None, 'temperature', 'temperature'),
                    ('get_resistance', None, 'resistance', 'resistance'),
                    ('is_sensor_connected', None, 'sensor_connected', 'connected'),
                    ('get_wire_mode', None, 'wire_mode', 'mode'),
                    ('get_noise_rejection_filter', None, 'noise_rejection_filter', 'filter')]
    SETTER_SPECS = [('set_wire_mode', 'wire_mode/set', ['mode']),
                    ('set_noise_rejection_filter', 'noise_rejection_filter/set', ['filter'])]

class BrickletRealTimeClockProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRealTimeClock
    TOPIC_PREFIX = 'bricklet/real_time_clock'
    GETTER_SPECS = [('get_date_time', None, 'date_time', None),
                    ('get_timestamp', None, 'timestamp', 'timestamp'),
                    ('get_offset', None, 'offset', 'offset')]
    SETTER_SPECS = [('set_date_time', 'date_time/set', ['year', 'month', 'day', 'hour', 'minute', 'second', 'centisecond', 'weekday']),
                    ('set_offset', 'offset/set', ['offset'])]

# FIXME: handle switching_done callback?
class BrickletRemoteSwitchProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRemoteSwitch
    TOPIC_PREFIX = 'bricklet/remote_switch'
    GETTER_SPECS = [('get_switching_state', None, 'switching_state', 'state'),
                    ('get_repeats', None, 'repeats', 'repeats')]
    SETTER_SPECS = [('switch_socket_a', 'switch_socket_a/set', ['house_code', 'receiver_code', 'switch_to']),
                    ('switch_socket_b', 'switch_socket_b/set', ['address', 'unit', 'switch_to']),
                    ('dim_socket_b', 'dim_socket_b/set', ['address', 'unit', 'dim_value']),
                    ('switch_socket_c', 'switch_socket_c/set', ['system_code', 'device_code', 'switch_to']),
                    ('set_repeats', 'repeats/set', ['repeats'])]

class BrickletRemoteSwitchV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletRemoteSwitchV2
    TOPIC_PREFIX = 'bricklet/remote_switch_v2'
    GETTER_SPECS = [('get_switching_state', None, 'switching_state', 'state'),
                    ('get_repeats', None, 'repeats', 'repeats')]
    SETTER_SPECS = [('switch_socket_a', 'switch_socket_a/set', ['house_code', 'receiver_code', 'switch_to']),
                    ('switch_socket_b', 'switch_socket_b/set', ['address', 'unit', 'switch_to']),
                    ('dim_socket_b', 'dim_socket_b/set', ['address', 'unit', 'dim_value']),
                    ('switch_socket_c', 'switch_socket_c/set', ['system_code', 'device_code', 'switch_to']),
                    ('set_repeats', 'repeats/set', ['repeats'])]

class BrickletRGBLEDProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRGBLED
    TOPIC_PREFIX = 'bricklet/rgb_led'
    GETTER_SPECS = [('get_rgb_value', None, 'rgb_value', None)]
    SETTER_SPECS = [('set_rgb_value', 'rgb_value/set', ['r', 'g', 'b'])]

class BrickletRGBLEDButtonProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRGBLEDButton
    TOPIC_PREFIX = 'bricklet/rgb_led_button'
    GETTER_SPECS = [('get_color', None, 'color', None),
                    ('get_button_state', None, 'button_state', 'state'),
                    ('get_color_calibration', None, 'color_calibration', None),
                    ('get_status_led_config', None, 'status_led_config', 'config'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('set_color', 'color/set', ['red', 'green', 'blue']),
                    ('set_color_calibration', 'color_calibration/set', ['red', 'green', 'blue']),
                    ('set_status_led_config', 'status_led_config/set', 'config'),
                    ('reset', 'reset/set', [])]

    def cb_button_state_changed(self, button_state):
        self.publish_values('button_state', state = button_state)

    def setup_callbacks(self):
        try:
            button_state = self.device.get_button_state()
            self.publish_values('button_state', state = button_state)
        except:
            pass

        self.device.register_callback(BrickletRGBLEDButton.CALLBACK_BUTTON_STATE_CHANGED,
                                      self.cb_button_state_changed)

class BrickletRGBLEDMatrixProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRGBLEDMatrix
    TOPIC_PREFIX = 'bricklet/rgb_led_matrix'
    GETTER_SPECS = [('get_red', None, 'red', 'red'),
                    ('get_green', None, 'green', 'green'),
                    ('get_blue', None, 'blue', 'blue'),
                    ('get_frame_duration', None, 'frame_duration', 'frame_duration'),
                    ('get_supply_voltage', None, 'supply_voltage', 'voltage'),
                    ('get_status_led_config', None, 'status_led_config', 'config'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [('set_red', 'red/set', ['red']),
                    ('set_green', 'green/set', ['green']),
                    ('set_blue', 'blue/set', ['blue']),
                    ('set_frame_duration', 'frame_duration/set', ['frame_duration']),
                    ('draw_frame', 'draw_frame/set', []),
                    ('set_status_led_config', 'status_led_config/set', ['config']),
                    ('reset', 'reset/set', [])]

class BrickletRotaryEncoderProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRotaryEncoder
    TOPIC_PREFIX = 'bricklet/rotary_encoder'
    GETTER_SPECS = [('get_count', (False,), 'count', 'count')]
    SETTER_SPECS = [(None, 'get_count/set', ['reset'], {'getter_name': 'get_count', 'getter_publish_topic': 'count', 'getter_return_value': 'count'})]

    # Arguments required for a getter must be published to "<GETTER-NAME>/set"
    # topic which will execute the getter with the provided arguments.
    # The output of the getter then will be published on the "<GETTER-NAME>"
    # topic.

    def cb_pressed(self):
        self.publish_values('pressed', pressed=True)

    def cb_released(self):
        self.publish_values('pressed', pressed=False)

    def setup_callbacks(self):
        try:
            self.publish_values('pressed', pressed=self.device.is_pressed())
        except:
            pass

        self.device.register_callback(BrickletRotaryEncoder.CALLBACK_PRESSED,
                                      self.cb_pressed)
        self.device.register_callback(BrickletRotaryEncoder.CALLBACK_RELEASED,
                                      self.cb_released)

class BrickletRotaryEncoderV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletRotaryEncoderV2
    TOPIC_PREFIX = 'bricklet/rotary_encoder_v2'
    GETTER_SPECS = [('get_count', (False,), 'count', 'count')]
    SETTER_SPECS = [(None, 'get_count/set', ['reset'], {'getter_name': 'get_count', 'getter_publish_topic': 'count', 'getter_return_value': 'count'})]

    # Arguments required for a getter must be published to "<GETTER-NAME>/set"
    # topic which will execute the getter with the provided arguments.
    # The output of the getter then will be published on the "<GETTER-NAME>"
    # topic.

    def cb_pressed(self):
        self.publish_values('pressed', pressed=True)

    def cb_released(self):
        self.publish_values('pressed', pressed=False)

    def setup_callbacks(self):
        try:
            self.publish_values('pressed', pressed=self.device.is_pressed())
        except:
            pass

        self.device.register_callback(BrickletRotaryEncoderV2.CALLBACK_PRESSED,
                                      self.cb_pressed)
        self.device.register_callback(BrickletRotaryEncoderV2.CALLBACK_RELEASED,
                                      self.cb_released)

# FIXME: expose analog_value getter?
class BrickletRotaryPotiProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRotaryPoti
    TOPIC_PREFIX = 'bricklet/rotary_poti'
    GETTER_SPECS = [('get_position', None, 'position', 'position')]

class BrickletRS232Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletRS232
    TOPIC_PREFIX = 'bricklet/rs232'
    GETTER_SPECS = [('read', None, 'read', None),
                    ('get_configuration', None, 'configuration', None)]
    SETTER_SPECS = [(None, 'write/set', ['message'], {'getter_name': 'write', 'getter_publish_topic': 'write', 'getter_return_value': 'written'}),
                    ('set_configuration', 'configuration/set', ['baudrate', 'parity', 'stopbits', 'wordlength', 'hardware_flowcontrol', 'software_flowcontrol']),
                    ('set_break_condition', 'break_condition/set', ['break_time'])]

    # Arguments required for a getter must be published to "<GETTER-NAME>/set"
    # topic which will execute the getter with the provided arguments.
    # The output of the getter then will be published on the "<GETTER-NAME>"
    # topic.

class BrickletRS485Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletRS485
    TOPIC_PREFIX = 'bricklet/rs485'
    GETTER_SPECS = [('get_rs485_configuration', None, 'rs485_configuration', None),
                    ('get_modbus_configuration', None, 'modbus_configuration', None),
                    ('get_mode', None, 'mode', 'mode'),
                    ('get_communication_led_config', None, 'communication_led_config', 'config'),
                    ('get_error_led_config', None, 'error_led_config', 'config'),
                    ('get_buffer_config', None, 'buffer_config', None),
                    ('get_buffer_status', None, 'buffer_status', None),
                    ('get_error_count', None, 'error_count', None),
                    ('get_modbus_common_error_count', None, 'modbus_common_error_count', None),
                    ('get_status_led_config', None, 'status_led_config', 'config'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature')]
    SETTER_SPECS = [(None, 'write/set', ['message'], {'getter_name': 'write', 'getter_publish_topic': 'write', 'getter_return_value': 'written'}),
                    (None, 'read/set', ['length'], {'getter_name': 'read', 'getter_publish_topic': 'read', 'getter_return_value': 'message'}),
                    ('set_rs485_configuration', 'rs485_configuration/set', ['baudrate', 'parity', 'stopbits', 'wordlength', 'duplex']),
                    ('set_modbus_configuration', 'modbus_configuration/set', ['slave_address', 'master_request_timeout']),
                    ('set_mode', 'mode/set', ['mode']),
                    ('set_communication_led_config', 'communication_led_config/set', ['config']),
                    ('set_error_led_config', 'error_led_config/set', ['config']),
                    ('set_buffer_config', 'buffer_config/set', ['send_buffer_size', 'receive_buffer_size']),
                    ('set_status_led_config', 'status_led_config/set', ['config']),
                    ('reset', 'reset/set', [])]

    # Arguments required for a getter must be published to "<GETTER-NAME>/set"
    # topic which will execute the getter with the provided arguments.
    # The output of the getter then will be published on the "<GETTER-NAME>"
    # topic.

class BrickletSegmentDisplay4x7Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletSegmentDisplay4x7
    TOPIC_PREFIX = 'bricklet/segment_display_4x7'
    GETTER_SPECS = [('get_segments', None, 'segments', None),
                    ('get_counter_value', None, 'counter_value', 'value')]
    SETTER_SPECS = [('set_segments', 'segments/set', ['segments', 'brightness', 'colon']),
                    ('start_counter', 'start_counter/set', ['value_from', 'value_to', 'increment', 'length'])]

# FIXME: handle monoflop_done callback?
class BrickletSolidStateRelayProxy(DeviceProxy):
    DEVICE_CLASS = BrickletSolidStateRelay
    TOPIC_PREFIX = 'bricklet/solid_state_relay'
    GETTER_SPECS = [('get_state', None, 'state', 'state'),
                    ('get_monoflop', None, 'monoflop', None)]
    SETTER_SPECS = [('set_state', 'state/set', ['state']),
                    ('set_monoflop', 'monoflop/set', ['state', 'time'])]

class BrickletSolidStateRelayV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletSolidStateRelayV2
    TOPIC_PREFIX = 'bricklet/solid_state_relay_v2'
    GETTER_SPECS = [('get_state', None, 'state', 'state'),
                    ('get_monoflop', None, 'monoflop', None)]
    SETTER_SPECS = [('set_state', 'state/set', ['state']),
                    ('set_monoflop', 'monoflop/set', ['state', 'time'])]

class BrickletSoundIntensityProxy(DeviceProxy):
    DEVICE_CLASS = BrickletSoundIntensity
    TOPIC_PREFIX = 'bricklet/sound_intensity'
    GETTER_SPECS = [('get_intensity', None, 'intensity', 'intensity')]

class BrickletTemperatureProxy(DeviceProxy):
    DEVICE_CLASS = BrickletTemperature
    TOPIC_PREFIX = 'bricklet/temperature'
    GETTER_SPECS = [('get_temperature', None, 'temperature', 'temperature'),
                    ('get_i2c_mode', None, 'i2c_mode', 'mode')]
    SETTER_SPECS = [('set_i2c_mode', 'i2c_mode/set', ['mode'])]

class BrickletTemperatureIRProxy(DeviceProxy):
    DEVICE_CLASS = BrickletTemperatureIR
    TOPIC_PREFIX = 'bricklet/temperature_ir'
    GETTER_SPECS = [('get_ambient_temperature', None, 'ambient_temperature', 'temperature'),
                    ('get_object_temperature', None, 'object_temperature', 'temperature'),
                    ('get_emissivity', None, 'emissivity', 'emissivity')]
    SETTER_SPECS = [('set_emissivity', 'emissivity/set', ['emissivity'])]


class BrickletTemperatureIRV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletTemperatureIRV2
    TOPIC_PREFIX = 'bricklet/temperature_ir'
    GETTER_SPECS = [('get_ambient_temperature', None, 'ambient_temperature', 'temperature'),
                    ('get_object_temperature', None, 'object_temperature', 'temperature'),
                    ('get_emissivity', None, 'emissivity', 'emissivity')]
    SETTER_SPECS = [('set_emissivity', 'emissivity/set', ['emissivity'])]

class BrickletThermalImagingProxy(DeviceProxy):
    DEVICE_CLASS = BrickletThermalImaging
    TOPIC_PREFIX = 'bricklet/thermal_imaging'
    GETTER_SPECS = [('get_high_contrast_image', None, 'high_contrast_image', 'image'),
                    ('get_temperature_image', None, 'temperature_image', 'image'),
                    ('get_statistics', None, 'statistics', None),
                    ('get_resolution', None, 'resolution', 'resolution'),
                    ('get_spotmeter_config', None, 'spotmeter_config', 'region_of_interest'),
                    ('get_high_contrast_config', None, 'high_contrast_config', None),
                    ('get_status_led_config', None, 'status_led_config', 'config'),
                    ('get_chip_temperature', None, 'chip_temperature', 'temperature'),
                    ('get_image_transfer_config', None, 'image_transfer_config', 'config')]
    SETTER_SPECS = [('set_resolution', 'resolution/set', ['resolution']),
                    ('set_spotmeter_config', 'spotmeter_config/set', ['region_of_interest']),
                    ('set_high_contrast_config', 'high_contrast_config/set', ['region_of_interest', 'dampening_factor', 'clip_limit', 'empty_counts']),
                    ('set_status_led_config', 'status_led_config/set', ['config']),
                    ('reset', 'reset/set', []),
                    ('set_image_transfer_config', 'image_transfer_config/set', ['config'])]

class BrickletThermocoupleProxy(DeviceProxy):
    DEVICE_CLASS = BrickletThermocouple
    TOPIC_PREFIX = 'bricklet/thermocouple'
    GETTER_SPECS = [('get_temperature', None, 'temperature', 'temperature'),
                    ('get_configuration', None, 'configuration', None),
                    ('get_error_state', None, 'error_state', None)]
    SETTER_SPECS = [('set_configuration', 'configuration/set', ['averaging', 'thermocouple_type', 'filter'])]

# FIXME: handle tilt_state callback, including enable_tilt_state_callback, disable_tilt_state_callback and is_tilt_state_callback_enabled?
class BrickletTiltProxy(DeviceProxy):
    DEVICE_CLASS = BrickletTilt
    TOPIC_PREFIX = 'bricklet/tilt'
    GETTER_SPECS = [('get_tilt_state', None, 'tilt_state', 'state')]

class BrickletUVLightProxy(DeviceProxy):
    DEVICE_CLASS = BrickletUVLight
    TOPIC_PREFIX = 'bricklet/uv_light'
    GETTER_SPECS = [('get_uv_light', None, 'uv_light', 'uv_light')]

# FIXME: expose analog_value getter?
class BrickletVoltageProxy(DeviceProxy):
    DEVICE_CLASS = BrickletVoltage
    TOPIC_PREFIX = 'bricklet/voltage'
    GETTER_SPECS = [('get_voltage', None, 'voltage', 'voltage')]

class BrickletVoltageCurrentProxy(DeviceProxy):
    DEVICE_CLASS = BrickletVoltageCurrent
    TOPIC_PREFIX = 'bricklet/voltage_current'
    GETTER_SPECS = [('get_voltage', None, 'voltage', 'voltage'),
                    ('get_current', None, 'current', 'current'),
                    ('get_power', None, 'power', 'power'),
                    ('get_configuration', None, 'configuration', None),
                    ('get_calibration', None, 'calibration', None)]
    SETTER_SPECS = [('set_configuration', 'configuration/set', ['averaging', 'voltage_conversion_time', 'current_conversion_time']),
                    ('set_calibration', 'calibration/set', ['gain_multiplier', 'gain_divisor'])]

class Proxy(object):
    def __init__(self, brickd_host, brickd_port, broker_host, broker_port,
                 broker_username, broker_password, broker_certificate, broker_tls_insecure,
                 update_interval, global_topic_prefix):
        self.brickd_host = brickd_host
        self.brickd_port = brickd_port
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.broker_username = broker_username
        self.broker_password = broker_password
        self.broker_certificate = broker_certificate
        self.broker_tls_insecure = broker_tls_insecure
        self.update_interval = update_interval
        self.global_topic_prefix = global_topic_prefix

        self.ipcon = IPConnection()
        self.ipcon.register_callback(IPConnection.CALLBACK_CONNECTED, self.ipcon_cb_connected)
        self.ipcon.register_callback(IPConnection.CALLBACK_ENUMERATE, self.ipcon_cb_enumerate)

        self.client = mqtt.Client()

        self.client.on_connect = self.mqtt_on_connect
        self.client.on_disconnect = self.mqtt_on_disconnect
        self.client.on_message = self.mqtt_on_message

        self.device_proxies = {}
        self.device_proxy_classes = {}

        for subclass in DeviceProxy.__subclasses__():
            self.device_proxy_classes[subclass.DEVICE_CLASS.DEVICE_IDENTIFIER] = subclass

    def connect(self):
        if self.broker_username is not None:
            self.client.username_pw_set(self.broker_username, self.broker_password)

        if self.broker_certificate is not None:
            self.client.tls_set(self.broker_certificate)

        if self.broker_tls_insecure:
            self.client.tls_insecure_set(True)

        self.client.connect(self.broker_host, self.broker_port)
        self.client.loop_start()

        while True:
            try:
                time.sleep(ENUMERATE_INTERVAL)
                self.ipcon.enumerate()
            except KeyboardInterrupt:
                self.client.disconnect()
                break
            except:
                pass

        self.client.loop_stop()

    def publish_as_json(self, topic, payload, *args, **kwargs):
        self.client.publish(self.global_topic_prefix + topic,
                            json.dumps(payload, separators=(',',':')),
                            *args, **kwargs)

    def publish_enumerate(self, changed_uid, connected):
        device_proxy = self.device_proxies[changed_uid]
        topic_prefix = device_proxy.TOPIC_PREFIX

        if connected:
            topic = 'enumerate/connected/' + topic_prefix
        else:
            topic = 'enumerate/disconnected/' + topic_prefix

        self.publish_as_json(topic, device_proxy.get_enumerate_entry())

        enumerate_entries = []

        for uid, device_proxy in self.device_proxies.items():
            if not connected and uid == changed_uid or device_proxy.TOPIC_PREFIX != topic_prefix:
                continue

            enumerate_entries.append(device_proxy.get_enumerate_entry())

        self.publish_as_json('enumerate/available/' + topic_prefix, enumerate_entries, retain=True)

    def ipcon_cb_connected(self, connect_reason):
        self.ipcon.enumerate()

    def ipcon_cb_enumerate(self, uid, connected_uid, position, hardware_version,
                           firmware_version, device_identifier, enumeration_type):
        if enumeration_type == IPConnection.ENUMERATION_TYPE_DISCONNECTED:
            if uid in self.device_proxies:
                self.publish_enumerate(uid, False)
                self.device_proxies[uid].destroy()
                del self.device_proxies[uid]
        elif device_identifier in self.device_proxy_classes and uid not in self.device_proxies:
            self.device_proxies[uid] = self.device_proxy_classes[device_identifier](uid, connected_uid, position, hardware_version,
                                                                                    firmware_version, self.ipcon, self.client,
                                                                                    self.update_interval, self.global_topic_prefix)
            self.publish_enumerate(uid, True)

    def mqtt_on_connect(self, client, user_data, flags, result_code):
        if result_code == 0:
            self.ipcon.connect(self.brickd_host, self.brickd_port)

    def mqtt_on_disconnect(self, client, user_data, result_code):
        self.ipcon.disconnect()

        for uid in self.device_proxies:
            self.device_proxies[uid].destroy()

        self.device_proxies = {}

    def mqtt_on_message(self, client, user_data, message):
        logging.debug('Received message for topic ' + message.topic)

        topic = message.topic[len(self.global_topic_prefix):]

        if topic.startswith('brick/') or topic.startswith('bricklet/'):
            topic_prefix1, topic_prefix2, uid, topic_suffix = topic.split('/', 3)
            topic_prefix = topic_prefix1 + '/' + topic_prefix2

            if uid in self.device_proxies and topic_prefix == self.device_proxies[uid].TOPIC_PREFIX:
                payload = message.payload.strip()

                if len(payload) > 0:
                    try:
                        payload = json.loads(message.payload.decode('UTF-8'))
                    except Exception as e:
                        logging.warn('Received message with invalid JSON payload for topic ' + message.topic + ': ' + str(e))
                        return
                else:
                    payload = {}

                self.device_proxies[uid].handle_message(topic_suffix, payload)
                return

        logging.debug('Unknown topic ' + message.topic)

def parse_positive_int(value):
    value = int(value)

    if value < 0:
        raise ValueError()

    return value

parse_positive_int.__name__ = 'positive-int'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Brick MQTT Proxy')
    parser.add_argument('--brickd-host', dest='brickd_host', type=str, default=BRICKD_HOST,
                        help='hostname or IP address of Brick Daemon, WIFI or Ethernet Extension (default: {0})'.format(BRICKD_HOST))
    parser.add_argument('--brickd-port', dest='brickd_port', type=int, default=BRICKD_PORT,
                        help='port number of Brick Daemon, WIFI or Ethernet Extension (default: {0})'.format(BRICKD_PORT))
    parser.add_argument('--broker-host', dest='broker_host', type=str, default=BROKER_HOST,
                        help='hostname or IP address of MQTT broker (default: {0})'.format(BROKER_HOST))
    parser.add_argument('--broker-port', dest='broker_port', type=int, default=BROKER_PORT,
                        help='port number of MQTT broker (default: {0})'.format(BROKER_PORT))
    parser.add_argument('--broker-username', dest='broker_username', type=str, default=None,
                        help='username for the MQTT broker connection')
    parser.add_argument('--broker-password', dest='broker_password', type=str, default=None,
                        help='password for the MQTT broker connection')
    parser.add_argument('--broker-certificate', dest='broker_certificate', type=str, default=None,
                        help='Certificate Authority certificate file used for SSL/TLS connections')
    parser.add_argument('--broker-tls-insecure', dest='broker_tls_insecure', action='store_true',
                        help='disable verification of the server hostname in the server certificate for the MQTT broker connection')
    parser.add_argument('--update-interval', dest='update_interval', type=parse_positive_int, default=UPDATE_INTERVAL,
                        help='update interval in seconds (default: {0})'.format(UPDATE_INTERVAL))
    parser.add_argument('--global-topic-prefix', dest='global_topic_prefix', type=str, default=GLOBAL_TOPIC_PREFIX,
                        help='global MQTT topic prefix for this proxy instance (default: {0})'.format(GLOBAL_TOPIC_PREFIX))
    parser.add_argument('--debug', dest='debug', action='store_true', help='enable debug output')

    args = parser.parse_args(sys.argv[1:])

    if args.broker_username is None and args.broker_password is not None:
        parser.error('--broker-password cannot be used without --broker-username')

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    global_topic_prefix = args.global_topic_prefix

    if len(global_topic_prefix) > 0 and not global_topic_prefix.endswith('/'):
        global_topic_prefix += '/'

    proxy = Proxy(args.brickd_host, args.brickd_port, args.broker_host,
                  args.broker_port, args.broker_username, args.broker_password,
                  args.broker_certificate, args.broker_tls_insecure,
                  args.update_interval, global_topic_prefix)

    proxy.connect()
