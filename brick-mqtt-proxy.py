#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Brick MQTT Proxy
Copyright (C) 2015-2017 Matthias Bolte <matthias@tinkerforge.com>

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
BROKER_PORT = 1883
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
from tinkerforge.ip_connection import IPConnection
from tinkerforge.bricklet_accelerometer import BrickletAccelerometer
from tinkerforge.bricklet_ambient_light import BrickletAmbientLight
from tinkerforge.bricklet_ambient_light_v2 import BrickletAmbientLightV2
from tinkerforge.bricklet_analog_in import BrickletAnalogIn
from tinkerforge.bricklet_analog_in_v2 import BrickletAnalogInV2
from tinkerforge.bricklet_analog_out import BrickletAnalogOut
from tinkerforge.bricklet_analog_out_v2 import BrickletAnalogOutV2
from tinkerforge.bricklet_barometer import BrickletBarometer
# FIXME: CAN Bricklet not handled yet
from tinkerforge.bricklet_co2 import BrickletCO2
from tinkerforge.bricklet_color import BrickletColor
from tinkerforge.bricklet_current12 import BrickletCurrent12
from tinkerforge.bricklet_current25 import BrickletCurrent25
from tinkerforge.bricklet_distance_ir import BrickletDistanceIR
from tinkerforge.bricklet_distance_us import BrickletDistanceUS
from tinkerforge.bricklet_dual_button import BrickletDualButton
from tinkerforge.bricklet_dual_relay import BrickletDualRelay
from tinkerforge.bricklet_dust_detector import BrickletDustDetector
from tinkerforge.bricklet_gps import BrickletGPS
from tinkerforge.bricklet_hall_effect import BrickletHallEffect
from tinkerforge.bricklet_humidity import BrickletHumidity
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
from tinkerforge.bricklet_multi_touch import BrickletMultiTouch
# FIXME: NFC/RFID Bricklet not handled yet
from tinkerforge.bricklet_oled_128x64 import BrickletOLED128x64
from tinkerforge.bricklet_oled_64x48 import BrickletOLED64x48
# FIXME: Piezo Buzzer Bricklet not handled yet
from tinkerforge.bricklet_piezo_speaker import BrickletPiezoSpeaker
from tinkerforge.bricklet_ptc import BrickletPTC
from tinkerforge.bricklet_real_time_clock import BrickletRealTimeClock
from tinkerforge.bricklet_remote_switch import BrickletRemoteSwitch
from tinkerforge.bricklet_rgb_led import BrickletRGBLED
from tinkerforge.bricklet_rotary_encoder import BrickletRotaryEncoder
from tinkerforge.bricklet_rotary_poti import BrickletRotaryPoti
# FIXME: RS232 Bricklet not handled yet
from tinkerforge.bricklet_segment_display_4x7 import BrickletSegmentDisplay4x7
from tinkerforge.bricklet_solid_state_relay import BrickletSolidStateRelay
from tinkerforge.bricklet_sound_intensity import BrickletSoundIntensity
from tinkerforge.bricklet_temperature import BrickletTemperature
from tinkerforge.bricklet_temperature_ir import BrickletTemperatureIR
from tinkerforge.bricklet_tilt import BrickletTilt
from tinkerforge.bricklet_uv_light import BrickletUVLight
from tinkerforge.bricklet_voltage import BrickletVoltage
from tinkerforge.bricklet_voltage_current import BrickletVoltageCurrent

class Getter(object):
    def __init__(self, proxy, getter_name, topic_suffix, result_name):
        self.proxy = proxy
        self.getter = getattr(proxy.device, getter_name)
        self.topic_suffix = topic_suffix
        self.result_name = result_name
        self.last_result = None

    def update(self):
        try:
            result = self.getter()
        except:
            result = self.last_result

        if result != None and result != self.last_result:
            payload = {}

            if isinstance(result, tuple) and hasattr(result, '_fields'): # assume it is a namedtuple
                for field in result._fields:
                    payload[field] = getattr(result, field)
            else:
                payload[self.result_name] = result

            self.proxy.publish_values(self.topic_suffix, **payload)

        self.last_result = result

class Setter(object):
    def __init__(self, proxy, setter_name, topic_suffix, parameter_names):
        self.setter = getattr(proxy.device, setter_name)
        self.topic_suffix = topic_suffix
        self.parameter_names = parameter_names

    def handle_message(self, payload):
        args = []

        for parameter_name in self.parameter_names:
            try:
                args.append(payload[parameter_name])
            except:
                return

        try:
            self.setter(*tuple(args))
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
#   Each getter specification is a 3-tuple:
#
#     (<getter-name>, <topic-suffix>, <value-name>)
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

class BrickletAccelerometerProxy(DeviceProxy):
    DEVICE_CLASS = BrickletAccelerometer
    TOPIC_PREFIX = 'bricklet/accelerometer'
    GETTER_SPECS = [('get_acceleration', 'acceleration', None),
                    ('get_temperature', 'temperature', 'temperature'),
                    ('get_configuration', 'configuration', None),
                    ('is_led_on', 'led_on', 'on')]
    SETTER_SPECS = [('set_configuration', 'configuration/set', ['data_rate', 'full_scale', 'filter_bandwidth']),
                    ('led_on', 'led_on/set', []),
                    ('led_off', 'led_off/set', [])]

# FIXME: expose analog_value getter?
class BrickletAmbientLightProxy(DeviceProxy):
    DEVICE_CLASS = BrickletAmbientLight
    TOPIC_PREFIX = 'bricklet/ambient_light'
    GETTER_SPECS = [('get_illuminance', 'illuminance', 'illuminance')]

class BrickletAmbientLightV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletAmbientLightV2
    TOPIC_PREFIX = 'bricklet/ambient_light_v2'
    GETTER_SPECS = [('get_illuminance', 'illuminance', 'illuminance'),
                    ('get_configuration', 'configuration', None)]
    SETTER_SPECS = [('set_configuration', 'configuration/set', ['illuminance_range', 'integration_time'])]

# FIXME: expose analog_value getter?
class BrickletAnalogInProxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogIn
    TOPIC_PREFIX = 'bricklet/analog_in'
    GETTER_SPECS = [('get_voltage', 'voltage', 'voltage'),
                    ('get_range', 'range', 'range'),
                    ('get_averaging', 'averaging', 'average')]
    SETTER_SPECS = [('set_range', 'range/set', ['range']),
                    ('set_averaging', 'averaging/set', ['average'])]

# FIXME: expose analog_value getter?
class BrickletAnalogInV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogInV2
    TOPIC_PREFIX = 'bricklet/analog_in_v2'
    GETTER_SPECS = [('get_voltage', 'voltage', 'voltage'),
                    ('get_moving_average', 'moving_average', 'average')]
    SETTER_SPECS = [('set_moving_average', 'moving_average/set', ['average'])]

class BrickletAnalogOutProxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogOut
    TOPIC_PREFIX = 'bricklet/analog_out'
    GETTER_SPECS = [('get_voltage', 'voltage', 'voltage'),
                    ('get_mode', 'mode', 'mode')]
    SETTER_SPECS = [('set_voltage', 'voltage/set', ['voltage']),
                    ('set_mode', 'mode/set', ['mode'])]

class BrickletAnalogOutV2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogOutV2
    TOPIC_PREFIX = 'bricklet/analog_out_v2'
    GETTER_SPECS = [('get_output_voltage', 'output_voltage', 'voltage'),
                    ('get_input_voltage', 'input_voltage', 'voltage')]
    SETTER_SPECS = [('set_output_voltage', 'output_voltage/set', ['voltage'])]

class BrickletBarometerProxy(DeviceProxy):
    DEVICE_CLASS = BrickletBarometer
    TOPIC_PREFIX = 'bricklet/barometer'
    GETTER_SPECS = [('get_air_pressure', 'air_pressure', 'air_pressure'),
                    ('get_altitude', 'altitude', 'altitude'),
                    ('get_chip_temperature', 'chip_temperature', 'temperature'),
                    ('get_reference_air_pressure', 'reference_air_pressure', 'air_pressure'),
                    ('get_averaging', 'averaging', None)]
    SETTER_SPECS = [('set_reference_air_pressure', 'reference_air_pressure/set', ['air_pressure']),
                    ('set_averaging', 'averaging/set', ['moving_average_pressure', 'average_pressure', 'average_temperature'])]

# FIXME: CAN Bricklet not handled yet

class BrickletCO2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletCO2
    TOPIC_PREFIX = 'bricklet/co2'
    GETTER_SPECS = [('get_co2_concentration', 'co2_concentration', 'co2_concentration')]

class BrickletColorProxy(DeviceProxy):
    DEVICE_CLASS = BrickletColor
    TOPIC_PREFIX = 'bricklet/color'
    GETTER_SPECS = [('get_color', 'color', None),
                    ('get_illuminance', 'illuminance', 'illuminance'),
                    ('get_color_temperature', 'color_temperature', 'color_temperature'),
                    ('get_config', 'config', None),
                    ('is_light_on', 'light_on', 'light')]
    SETTER_SPECS = [('set_config', 'config/set', ['gain', 'integration_time']),
                    ('light_on', 'light_on/set', []),
                    ('light_off', 'light_off/set', [])]

# FIXME: expose analog_value getter?
# FIXME: handle over_current callback?
class BrickletCurrent12Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletCurrent12
    TOPIC_PREFIX = 'bricklet/current12'
    GETTER_SPECS = [('get_current', 'current', 'current'),
                    ('is_over_current', 'over_current', 'over')]
    SETTER_SPECS = [('calibrate', 'calibrate/set', [])]

# FIXME: expose analog_value getter?
# FIXME: handle over_current callback?
class BrickletCurrent25Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletCurrent25
    TOPIC_PREFIX = 'bricklet/current25'
    GETTER_SPECS = [('get_current', 'current', 'current'),
                    ('is_over_current', 'over_current', 'over')]
    SETTER_SPECS = [('calibrate', 'calibrate/set', [])]

# FIXME: expose analog_value getter?
# FIXME: expose sampling_point getter/setter?
class BrickletDistanceIRProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDistanceIR
    TOPIC_PREFIX = 'bricklet/distance_ir'
    GETTER_SPECS = [('get_distance', 'distance', 'distance')]

class BrickletDistanceUSProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDistanceUS
    TOPIC_PREFIX = 'bricklet/distance_us'
    GETTER_SPECS = [('get_distance_value', 'distance_value', 'distance'),
                    ('get_moving_average', 'moving_average', 'average')]
    SETTER_SPECS = [('set_moving_average', 'moving_average/set', ['average'])]

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
    GETTER_SPECS = [('get_state', 'state', None)]
    SETTER_SPECS = [('set_state', 'state/set', ['relay1', 'relay2']),
                    ('set_monoflop', 'monoflop/set', ['relay', 'state', 'time']),
                    ('set_selected_state', 'selected_state/set', ['relay', 'state'])]

class BrickletDustDetectorProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDustDetector
    TOPIC_PREFIX = 'bricklet/dust_detector'
    GETTER_SPECS = [('get_dust_density', 'dust_density', 'dust_density'),
                    ('get_moving_average', 'moving_average', 'average')]
    SETTER_SPECS = [('set_moving_average', 'moving_average/set', ['average'])]

# FIXME: get_coordinates, get_altitude and get_motion need special status handling to avoid publishing invalid data
class BrickletGPSProxy(DeviceProxy):
    DEVICE_CLASS = BrickletGPS
    TOPIC_PREFIX = 'bricklet/gps'
    GETTER_SPECS = [('get_status', 'status', None),
                    ('get_coordinates', 'coordinates', None),
                    ('get_altitude', 'altitude', None),
                    ('get_motion', 'motion', None),
                    ('get_date_time', 'date_time', 'date_time')]
    SETTER_SPECS = [('restart', 'restart/set', ['restart_type'])]

# FIXME: get_edge_count needs special handling
class BrickletHallEffectProxy(DeviceProxy):
    DEVICE_CLASS = BrickletHallEffect
    TOPIC_PREFIX = 'bricklet/hall_effect'
    GETTER_SPECS = [('get_value', 'value', 'value'),
                    ('get_edge_count_config', 'edge_count_config', None)]
    SETTER_SPECS = [('set_edge_count_config', 'edge_count_config/set', ['edge_type', 'debounce'])]

# FIXME: expose analog_value getter?
class BrickletHumidityProxy(DeviceProxy):
    DEVICE_CLASS = BrickletHumidity
    TOPIC_PREFIX = 'bricklet/humidity'
    GETTER_SPECS = [('get_humidity', 'humidity', 'humidity')]

class BrickletIndustrialAnalogOutProxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialAnalogOut
    TOPIC_PREFIX = 'bricklet/industrial_analog_out'
    GETTER_SPECS = [('get_voltage', 'voltage', 'voltage'),
                    ('get_current', 'current', 'current'),
                    ('get_configuration', 'configuration', None),
                    ('is_enabled', 'enabled', 'enabled')]
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
    GETTER_SPECS = [('get_value', 'value', 'value_mask'),
                    ('get_group', 'group', 'group'),
                    ('get_available_for_group', 'available_for_group', 'available')]
    SETTER_SPECS = [('set_edge_count_config', 'edge_count_config/set', ['edge_type', 'debounce']),
                    ('set_group', 'group/set', ['group'])]

# FIXME: get_monoflop needs special handling
# FIXME: handle monoflop_done callback?
class BrickletIndustrialDigitalOut4Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialDigitalOut4
    TOPIC_PREFIX = 'bricklet/industrial_digital_out_4'
    GETTER_SPECS = [('get_value', 'value', 'value_mask'),
                    ('get_group', 'group', 'group'),
                    ('get_available_for_group', 'available_for_group', 'available')]
    SETTER_SPECS = [('set_value', 'value/set', ['value_mask']),
                    ('set_selected_values', 'selected_values/set', ['selection_mask', 'value_mask']),
                    ('set_monoflop', 'monoflop/set', ['selection_mask', 'value_mask', 'time']),
                    ('set_group', 'group/set', ['group'])]

# FIXME: get_current needs special handling
class BrickletIndustrialDual020mAProxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialDual020mA
    TOPIC_PREFIX = 'bricklet/industrial_dual_0_20ma'
    GETTER_SPECS = [('get_sample_rate', 'sample_rate', 'rate')]
    SETTER_SPECS = [('set_sample_rate', 'sample_rate/set', ['rate'])]

# FIXME: get_voltage needs special handling
class BrickletIndustrialDualAnalogInProxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialDualAnalogIn
    TOPIC_PREFIX = 'bricklet/industrial_dual_analog_in'
    GETTER_SPECS = [('get_sample_rate', 'sample_rate', 'rate'),
                    ('get_calibration', 'calibration', None),
                    ('get_adc_values', 'adc_values', 'value')]
    SETTER_SPECS = [('set_sample_rate', 'sample_rate/set', ['rate']),
                    ('set_calibration', 'calibration/set', ['offset', 'gain'])]

# FIXME: get_monoflop needs special handling
# FIXME: handle monoflop_done callback?
class BrickletIndustrialQuadRelayProxy(DeviceProxy):
    DEVICE_CLASS = BrickletIndustrialQuadRelay
    TOPIC_PREFIX = 'bricklet/industrial_quad_relay'
    GETTER_SPECS = [('get_value', 'value', 'value_mask'),
                    ('get_group', 'group', 'group'),
                    ('get_available_for_group', 'available_for_group', 'available')]
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
    SETTER_SPECS = [('set_port', 'port/set', ['port', 'value_mask']),
                    ('set_port_configuration', 'port_configuration/set', ['port', 'selection_mask', 'direction', 'value']),
                    ('set_port_monoflop', 'port_monoflop/set', ['port', 'selection_mask', 'value_mask', 'time']),
                    ('set_selected_values', 'selected_values/set', ['port', 'selection_mask', 'value_mask']),
                    ('set_edge_count_config', 'edge_count_config/set', ['port', 'edge_type', 'debounce'])]

    def update_extra_getters(self):
        port = {'a': 0, 'b': 0}
        port_configuration = {'a': {'direction_mask': 0, 'value_mask': 0}, 'b': {'direction_mask': 0, 'value_mask': 0}}

        for c in ['a', 'b']:
            try:
                port[c] = self.device.get_port(c)
            except:
                pass

            try:
                config = self.device.get_port_configuration(c)

                port_configuration[c]['direction_mask'] = config.direction_mask
                port_configuration[c]['value_mask'] = config.value_mask
            except:
                pass

        self.publish_values('port', **port)
        self.publish_values('port_configuration', **port_configuration)

# FIXME: get_edge_count, get_monoflop and get_edge_count_config need special handling
# FIXME: handle monoflop_done callback?
# FIXME: handle interrupt callback, including get_interrupt and set_interrupt?
class BrickletIO4Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletIO4
    TOPIC_PREFIX = 'bricklet/io4'
    GETTER_SPECS = [('get_value', 'value', 'value_mask'),
                    ('get_configuration', 'configuration', None)]
    SETTER_SPECS = [('set_value', 'value/set', ['value_mask']),
                    ('set_configuration', 'configuration/set', ['selection_mask', 'direction', 'value']),
                    ('set_monoflop', 'monoflop/set', ['selection_mask', 'value_mask', 'time']),
                    ('set_selected_values', 'selected_values/set', ['selection_mask', 'value_mask']),
                    ('set_edge_count_config', 'edge_count_config/set', ['edge_type', 'debounce'])]

# FIXME: expose analog_value getter?
class BrickletJoystickProxy(DeviceProxy):
    DEVICE_CLASS = BrickletJoystick
    TOPIC_PREFIX = 'bricklet/joystick'
    GETTER_SPECS = [('get_position', 'position', None)]
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
    GETTER_SPECS = [('get_distance', 'distance', 'distance'),
                    ('get_velocity', 'velocity', 'velocity'),
                    ('get_mode', 'mode', 'mode'),
                    ('is_laser_enabled', 'laser_enabled', 'laser_enabled'),
                    ('get_moving_average', 'moving_average', None)]
    SETTER_SPECS = [('set_mode', 'mode/set', ['mode']),
                    ('enable_laser', 'enable_laser/set', []),
                    ('disable_laser', 'disable_laser/set', []),
                    ('set_moving_average', 'moving_average/set', ['distance_average_length', 'velocity_average_length'])]

class BrickletLCD16x2Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletLCD16x2
    TOPIC_PREFIX = 'bricklet/lcd_16x2'
    GETTER_SPECS = [('is_backlight_on', 'backlight_on', 'backlight'),
                    ('get_config', 'config', None)]
    SETTER_SPECS = [('write_line', 'write_line/set', ['line', 'position', 'text']),
                    ('clear_display', 'clear_display/set', []),
                    ('backlight_on', 'backlight_on/set', []),
                    ('backlight_off', 'backlight_off/set', []),
                    ('set_config', 'config/set', ['cursor', 'blinking']),
                    ('set_custom_character', 'custom_character/set', ['index', 'character'])]

    def update_extra_getters(self):
        custom_character = {'0': [0]*8, '1': [0]*8, '2': [0]*8, '3': [0]*8, '4': [0]*8, '5': [0]*8, '6': [0]*8, '7': [0]*8}

        for index in range(8):
            try:
                custom_character[str(index)] = self.device.get_custom_character(index)
            except:
                pass

        self.publish_values('custom_character', **custom_character)

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
    GETTER_SPECS = [('is_backlight_on', 'backlight_on', 'backlight'),
                    ('get_config', 'config', None),
                    ('get_default_text_counter', 'default_text_counter', 'counter')]
    SETTER_SPECS = [('write_line', 'write_line/set', ['line', 'position', 'text']),
                    ('clear_display', 'clear_display/set', []),
                    ('backlight_on', 'backlight_on/set', []),
                    ('backlight_off', 'backlight_off/set', []),
                    ('set_config', 'config/set', ['cursor', 'blinking']),
                    ('set_custom_character', 'custom_character/set', ['index', 'character']),
                    ('set_default_text', 'default_text/set', ['line', 'text']),
                    ('set_default_text_counter', 'default_text_counter/set', ['counter'])]

    def update_extra_getters(self):
        custom_character = {'0': [0]*8, '1': [0]*8, '2': [0]*8, '3': [0]*8, '4': [0]*8, '5': [0]*8, '6': [0]*8, '7': [0]*8}

        for index in range(8):
            try:
                custom_character[str(index)] = self.device.get_custom_character(index)
            except:
                pass

        self.publish_values('custom_character', **custom_character)

        default_text = {'0': '', '1': '', '2': '', '3': ''}

        for line in range(4):
            try:
                default_text[str(line)] = self.device.get_default_text(line)
            except:
                pass

        self.publish_values('default_text', **default_text)

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
    GETTER_SPECS = [('get_rgb_values', 'rgb_values', None),
                    ('get_frame_duration', 'frame_duration', 'duration'),
                    ('get_supply_voltage', 'supply_voltage', 'voltage'),
                    ('get_clock_frequency', 'clock_frequency', 'frequency'),
                    ('get_chip_type', 'chip_type', 'chip')]
    SETTER_SPECS = [('set_rgb_values', 'rgb_values/set', ['index', 'length', 'r', 'g', 'b']),
                    ('set_frame_duration', 'frame_duration/set', ['duration']),
                    ('set_clock_frequency', 'clock_frequency/set', ['frequency']),
                    ('set_chip_type', 'chip_type/set', ['chip'])]

class BrickletLineProxy(DeviceProxy):
    DEVICE_CLASS = BrickletLine
    TOPIC_PREFIX = 'bricklet/line'
    GETTER_SPECS = [('get_reflectivity', 'reflectivity', 'reflectivity')]

# FIXME: expose analog_value getter?
class BrickletLinearPotiProxy(DeviceProxy):
    DEVICE_CLASS = BrickletLinearPoti
    TOPIC_PREFIX = 'bricklet/linear_poti'
    GETTER_SPECS = [('get_position', 'position', 'position')]

class BrickletLoadCellProxy(DeviceProxy):
    DEVICE_CLASS = BrickletLoadCell
    TOPIC_PREFIX = 'bricklet/load_cell'
    GETTER_SPECS = [('get_weight', 'weight', 'weight'),
                    ('is_led_on', 'led_on', 'on'),
                    ('get_moving_average', 'moving_average', 'average'),
                    ('get_configuration', 'configuration', None)]
    SETTER_SPECS = [('led_on', 'led_on/set', []),
                    ('led_off', 'led_off/set', []),
                    ('set_moving_average', 'moving_average/set', ['average']),
                    ('set_configuration', 'configuration/set', ['rate', 'gain']),
                    ('tare', 'tare/set', [])]

class BrickletMoistureProxy(DeviceProxy):
    DEVICE_CLASS = BrickletMoisture
    TOPIC_PREFIX = 'bricklet/moisture'
    GETTER_SPECS = [('get_moisture_value', 'moisture_value', 'moisture'),
                    ('get_moving_average', 'moving_average', 'average')]
    SETTER_SPECS = [('set_moving_average', 'moving_average/set', ['average'])]

# FIXME: handle motion_detected and detection_cycle_ended callbacks?
class BrickletMotionDetectorProxy(DeviceProxy):
    DEVICE_CLASS = BrickletMotionDetector
    TOPIC_PREFIX = 'bricklet/motion_detector'
    GETTER_SPECS = [('get_motion_detected', 'motion_detected', 'motion')]

class BrickletMultiTouchProxy(DeviceProxy):
    DEVICE_CLASS = BrickletMultiTouch
    TOPIC_PREFIX = 'bricklet/multi_touch'
    GETTER_SPECS = [('get_electrode_config', 'electrode_config', 'enabled_electrodes'),
                    ('get_electrode_sensitivity', 'electrode_sensitivity', 'sensitivity')]
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

# FIXME: NFC/RFID Bricklet not handled yet

class BrickletOLED128x64Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletOLED128x64
    TOPIC_PREFIX = 'bricklet/oled_128x64'
    GETTER_SPECS = [('get_display_configuration', 'display_configuration', None)]
    SETTER_SPECS = [('write', 'write/set', ['data']),
                    ('new_window', 'new_window/set', ['column_from', 'column_to', 'row_from', 'row_to']),
                    ('clear_display', 'clear_display/set', []),
                    ('write_line', 'write_line/set', ['line', 'position', 'text']),
                    ('set_display_configuration', 'display_configuration/set', ['contrast', 'invert'])]

class BrickletOLED64x48Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletOLED64x48
    TOPIC_PREFIX = 'bricklet/oled_64x48'
    GETTER_SPECS = [('get_display_configuration', 'display_configuration', None)]
    SETTER_SPECS = [('write', 'write/set', ['data']),
                    ('new_window', 'new_window/set', ['column_from', 'column_to', 'row_from', 'row_to']),
                    ('clear_display', 'clear_display/set', []),
                    ('write_line', 'write_line/set', ['line', 'position', 'text']),
                    ('set_display_configuration', 'display_configuration/set', ['contrast', 'invert'])]

# FIXME: Piezo Buzzer Bricklet not handled yet

# FIXME: handle beep_finished and morse_code_finished callback?
# FIXME: expose calibrate setter?
class BrickletPiezoSpeakerProxy(DeviceProxy):
    DEVICE_CLASS = BrickletPiezoSpeaker
    TOPIC_PREFIX = 'bricklet/piezo_speaker'
    SETTER_SPECS = [('beep', 'beep/set', ['duration', 'frequency']),
                    ('morse_code', 'morse_code/set', ['morse', 'frequency'])]

class BrickletPTCProxy(DeviceProxy):
    DEVICE_CLASS = BrickletPTC
    TOPIC_PREFIX = 'bricklet/ptc'
    GETTER_SPECS = [('get_temperature', 'temperature', 'temperature'),
                    ('get_resistance', 'resistance', 'resistance'),
                    ('is_sensor_connected', 'sensor_connected', 'connected'),
                    ('get_wire_mode', 'wire_mode', 'mode'),
                    ('get_noise_rejection_filter', 'noise_rejection_filter', 'filter')]
    SETTER_SPECS = [('set_wire_mode', 'wire_mode/set', ['mode']),
                    ('set_noise_rejection_filter', 'noise_rejection_filter/set', ['filter'])]

class BrickletRealTimeClockProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRealTimeClock
    TOPIC_PREFIX = 'bricklet/real_time_clock'
    GETTER_SPECS = [('get_date_time', 'date_time', None),
                    ('get_timestamp', 'timestamp', 'timestamp'),
                    ('get_offset', 'offset', 'offset')]
    SETTER_SPECS = [('set_date_time', 'date_time/set', ['year', 'month', 'day', 'hour', 'minute', 'second', 'centisecond', 'weekday']),
                    ('set_offset', 'offset/set', ['offset'])]

# FIXME: handle switching_done callback?
class BrickletRemoteSwitchProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRemoteSwitch
    TOPIC_PREFIX = 'bricklet/remote_switch'
    GETTER_SPECS = [('get_switching_state', 'switching_state', 'state'),
                    ('get_repeats', 'repeats', 'repeats')]
    SETTER_SPECS = [('switch_socket_a', 'switch_socket_a/set', ['house_code', 'receiver_code', 'switch_to']),
                    ('switch_socket_b', 'switch_socket_b/set', ['address', 'unit', 'switch_to']),
                    ('dim_socket_b', 'dim_socket_b/set', ['address', 'unit', 'dim_value']),
                    ('switch_socket_c', 'switch_socket_c/set', ['system_code', 'device_code', 'switch_to']),
                    ('set_repeats', 'repeats/set', ['repeats'])]

class BrickletRGBLEDProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRGBLED
    TOPIC_PREFIX = 'bricklet/rgb_led'
    GETTER_SPECS = [('get_rgb_value', 'rgb_value', None)]
    SETTER_SPECS = [('set_rgb_value', 'rgb_value/set', ['r', 'g', 'b'])]

class BrickletRotaryEncoderProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRotaryEncoder
    TOPIC_PREFIX = 'bricklet/rotary_encoder'
    EXTRA_SUBSCRIPTIONS = ['_reset_count/set']

    def update_extra_getters(self):
        try:
            self.publish_values('count', count=self.device.get_count(False))
        except:
            pass

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

    def handle_extra_message(self, topic_suffix, payload):
        if topic_suffix == '_reset_count/set':
            try:
                self.publish_values('count', count=self.device.get_count(True))
            except:
                pass

# FIXME: expose analog_value getter?
class BrickletRotaryPotiProxy(DeviceProxy):
    DEVICE_CLASS = BrickletRotaryPoti
    TOPIC_PREFIX = 'bricklet/rotary_poti'
    GETTER_SPECS = [('get_position', 'position', 'position')]

# FIXME: RS232 Bricklet not handled yet

class BrickletSegmentDisplay4x7Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletSegmentDisplay4x7
    TOPIC_PREFIX = 'bricklet/segment_display_4x7'
    GETTER_SPECS = [('get_segments', 'segments', None),
                    ('get_counter_value', 'counter_value', 'value')]
    SETTER_SPECS = [('set_segments', 'segments/set', ['segments', 'brightness', 'colon']),
                    ('start_counter', 'start_counter/set', ['value_from', 'value_to', 'increment', 'length'])]

# FIXME: handle monoflop_done callback?
class BrickletSolidStateRelayProxy(DeviceProxy):
    DEVICE_CLASS = BrickletSolidStateRelay
    TOPIC_PREFIX = 'bricklet/solid_state_relay'
    GETTER_SPECS = [('get_state', 'state', 'state'),
                    ('get_monoflop', 'monoflop', None)]
    SETTER_SPECS = [('set_state', 'state/set', ['state']),
                    ('set_monoflop', 'monoflop/set', ['state', 'time'])]

class BrickletSoundIntensityProxy(DeviceProxy):
    DEVICE_CLASS = BrickletSoundIntensity
    TOPIC_PREFIX = 'bricklet/sound_intensity'
    GETTER_SPECS = [('get_intensity', 'intensity', 'intensity')]

class BrickletTemperatureProxy(DeviceProxy):
    DEVICE_CLASS = BrickletTemperature
    TOPIC_PREFIX = 'bricklet/temperature'
    GETTER_SPECS = [('get_temperature', 'temperature', 'temperature'),
                    ('get_i2c_mode', 'i2c_mode', 'mode')]
    SETTER_SPECS = [('set_i2c_mode', 'i2c_mode/set', ['mode'])]

class BrickletTemperatureIRProxy(DeviceProxy):
    DEVICE_CLASS = BrickletTemperatureIR
    TOPIC_PREFIX = 'bricklet/temperature_ir'
    GETTER_SPECS = [('get_ambient_temperature', 'ambient_temperature', 'temperature'),
                    ('get_object_temperature', 'object_temperature', 'temperature'),
                    ('get_emissivity', 'emissivity', 'emissivity')]
    SETTER_SPECS = [('set_emissivity', 'emissivity/set', ['emissivity'])]

# FIXME: handle tilt_state callback, including enable_tilt_state_callback, disable_tilt_state_callback and is_tilt_state_callback_enabled?
class BrickletTiltProxy(DeviceProxy):
    DEVICE_CLASS = BrickletTilt
    TOPIC_PREFIX = 'bricklet/tilt'
    GETTER_SPECS = [('get_tilt_state', 'tilt_state', 'state')]

class BrickletUVLightProxy(DeviceProxy):
    DEVICE_CLASS = BrickletUVLight
    TOPIC_PREFIX = 'bricklet/uv_light'
    GETTER_SPECS = [('get_uv_light', 'uv_light', 'uv_light')]

# FIXME: expose analog_value getter?
class BrickletVoltageProxy(DeviceProxy):
    DEVICE_CLASS = BrickletVoltage
    TOPIC_PREFIX = 'bricklet/voltage'
    GETTER_SPECS = [('get_voltage', 'voltage', 'voltage')]

class BrickletVoltageCurrentProxy(DeviceProxy):
    DEVICE_CLASS = BrickletVoltageCurrent
    TOPIC_PREFIX = 'bricklet/voltage_current'
    GETTER_SPECS = [('get_voltage', 'voltage', 'voltage'),
                    ('get_current', 'current', 'current'),
                    ('get_power', 'power', 'power'),
                    ('get_configuration', 'configuration', None),
                    ('get_calibration', 'calibration', None)]
    SETTER_SPECS = [('set_configuration', 'configuration/set', ['averaging', 'voltage_conversion_time', 'current_conversion_time']),
                    ('set_calibration', 'calibration/set', ['gain_multiplier', 'gain_divisor'])]

class Proxy(object):
    def __init__(self, brickd_host, brickd_port, broker_host, broker_port, update_interval, global_topic_prefix, broker_username=None, broker_password=None, broker_tls_insecure=False, broker_certificate=None):
        self.brickd_host = brickd_host
        self.brickd_port = brickd_port
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.update_interval = update_interval
        self.global_topic_prefix = global_topic_prefix
        self.broker_username = broker_username
        self.broker_password = broker_password
        self.broker_tls_insecure = broker_tls_insecure
        self.broker_certificate = broker_certificate
        
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
                        help='disable verification of the server hostname in the server certificat for the MQTT broker connection')
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
                  args.broker_port, args.update_interval, global_topic_prefix,
                  args.broker_username, args.broker_password, args.broker_tls_insecure, args.broker_certificate)
    proxy.connect()
