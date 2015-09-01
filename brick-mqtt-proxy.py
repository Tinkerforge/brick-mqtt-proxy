#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Brick MQTT Proxy
Copyright (C) 2015 Matthias Bolte <matthias@tinkerforge.com>

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
ENUMERATE_INTERVAL = 15.0 # seconds
UPDATE_INTERVAL = 3.0 # seconds

import argparse
import json
import struct
import sys
import time
import threading
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
from tinkerforge.bricklet_color import BrickletColor
from tinkerforge.bricklet_current12 import BrickletCurrent12
from tinkerforge.bricklet_current25 import BrickletCurrent25
from tinkerforge.bricklet_distance_ir import BrickletDistanceIR
from tinkerforge.bricklet_distance_us import BrickletDistanceUS
from tinkerforge.bricklet_dual_button import BrickletDualButton
from tinkerforge.bricklet_dual_relay import BrickletDualRelay
from tinkerforge.bricklet_dust_detector import BrickletDustDetector
from tinkerforge.bricklet_humidity import BrickletHumidity
from tinkerforge.bricklet_lcd_20x4 import BrickletLCD20x4
from tinkerforge.bricklet_temperature import BrickletTemperature
from tinkerforge.bricklet_temperature_ir import BrickletTemperatureIR

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
                 ipcon, client, update_interval):
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
        self.update_interval = 0 # seconds
        self.update_timer = None
        self.update_lock = threading.Lock()

        for getter_spec in self.GETTER_SPECS:
            self.getters.append(Getter(self, *getter_spec))

        for setter_spec in self.SETTER_SPECS:
            self.setters[setter_spec[1]] = Setter(self, *setter_spec)
            self.client.subscribe(self.topic_prefix + setter_spec[1])

        for topic_suffix in self.EXTRA_SUBSCRIPTIONS:
            self.client.subscribe(self.topic_prefix + topic_suffix)

        self.client.subscribe(self.topic_prefix + '_update_interval/set')

        self.set_update_interval(update_interval)
        self.update_locked()

    def handle_extra_message(self, topic_suffix, payload): # to be implemented by subclasses
        pass

    def handle_message(self, topic_suffix, payload):
        if topic_suffix == '_update_interval/set':
            try:
                self.set_update_interval(float(payload['_update_interval']))
            except:
                pass
        elif topic_suffix in self.setters:
            self.setters[topic_suffix].handle_message(payload)
        else:
            self.handle_extra_message(topic_suffix, payload)

        self.update_locked()

    def publish_as_json(self, topic, payload, *args, **kwargs):
        self.client.publish(topic, json.dumps(payload, separators=(',', ':')), *args, **kwargs)

    def publish_values(self, topic_suffix, **kwargs):
        payload = {'_timestamp': time.time()}

        for key, value in kwargs.items():
            payload[key] = value

        self.publish_as_json(self.topic_prefix + topic_suffix, payload, retain=True)

    def set_update_interval(self, update_interval): # in seconds
        if self.update_interval != update_interval:
            self.publish_values('_update_interval', _update_interval=float(update_interval))

        self.update_interval = update_interval

        if self.update_interval > 0 and self.update_timer == None:
            self.update_timer = threading.Timer(self.update_interval, self.update)
            self.update_timer.start()

    def update_extra(self): # to be implemented by subclasses
        pass

    def update_getters(self):
        for getter in self.getters:
            getter.update()

    def update_locked(self):
        with self.update_lock:
            self.update_getters()
            self.update_extra()

    def update(self):
        self.update_timer = None

        if self.update_interval < 1:
            return

        self.update_locked()

        if self.update_interval > 0:
            self.update_timer = threading.Timer(self.update_interval, self.update)
            self.update_timer.start()

    def get_enumerate_entry(self):
        return {'_timestamp': self.timestamp,
                'uid': self.uid,
                'connected_uid': self.connected_uid,
                'position': self.position,
                'hardware_version': self.hardware_version,
                'firmware_version': self.firmware_version,
                'device_identifier': self.DEVICE_CLASS.DEVICE_IDENTIFIER}

    def destroy(self):
        self.set_update_interval(0)

        for setter_spec in self.SETTER_SPECS:
            self.client.unsubscribe(self.topic_prefix + setter_spec[1])

        self.client.unsubscribe(self.topic_prefix + '_update_interval/set')

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
#     <topic-prefix>/<uid>/<topic-suffix>
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
# - update_extra (optional): A bound function taking no arguments. This can be
#   used to implement things that don't fit into a getter specification. The
#   DeviceProxy instance automatically calls this function with the configured
#   update interval. Inside this function the publish_values function of the
#   DeviceProxy class can be used to publish a dict formatted as JSON to a
#   specified topic suffix.
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
#   passed to the bound handle_message function.
#
# - handle_extra_message (optional): A bound function taking two arguments: the
#   topic suffix as str and the decoded JSON payload as dict.
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

class BrickletAnalogInProxy(DeviceProxy):
    DEVICE_CLASS = BrickletAnalogIn
    TOPIC_PREFIX = 'bricklet/analog_in'
    GETTER_SPECS = [('get_voltage', 'voltage', 'voltage'),
                    ('get_range', 'range', 'range'),
                    ('get_averaging', 'averaging', 'average')]
    SETTER_SPECS = [('set_range', 'range/set', ['range']),
                    ('set_averaging', 'averaging/set', ['average'])]

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

class BrickletCurrent12Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletCurrent12
    TOPIC_PREFIX = 'bricklet/current12'
    GETTER_SPECS = [('get_current', 'current', 'current')]

class BrickletCurrent25Proxy(DeviceProxy):
    DEVICE_CLASS = BrickletCurrent25
    TOPIC_PREFIX = 'bricklet/current25'
    GETTER_SPECS = [('get_current', 'current', 'current')]

class BrickletDistanceIRProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDistanceIR
    TOPIC_PREFIX = 'bricklet/distance_ir'
    GETTER_SPECS = [('get_distance', 'distance', 'distance')]

class BrickletDistanceUSProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDistanceUS
    TOPIC_PREFIX = 'bricklet/distance_us'
    GETTER_SPECS = [('get_distance_value', 'distance_value', 'distance')]

class BrickletDualButtonProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDualButton
    TOPIC_PREFIX = 'bricklet/dual_button'
    GETTER_SPECS = [('get_led_state', 'led_state', None)]
    SETTER_SPECS = [('set_led_state', 'led_state/set', ['led_l', 'led_r']),
                    ('set_selected_led_state', 'selected_led_state/set', ['led', 'state'])]

class BrickletDualRelayProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDualRelay
    TOPIC_PREFIX = 'bricklet/dual_relay'
    GETTER_SPECS = [('get_state', 'state', None),
                    ('get_monoflop', 'monoflop', None)]
    SETTER_SPECS = [('set_state', 'state/set', ['relay1', 'relay2']),
                    ('set_monoflop', 'monoflop/set', ['relay', 'state', 'time']),
                    ('set_selected_state', 'selected_state/set', ['relay', 'state'])]

class BrickletDustDetectorProxy(DeviceProxy):
    DEVICE_CLASS = BrickletDustDetector
    TOPIC_PREFIX = 'bricklet/dust_detector'
    GETTER_SPECS = [('get_dust_density', 'dust_density', 'dust_density'),
                    ('get_moving_average', 'moving_average', 'average')]
    SETTER_SPECS = [('set_moving_average', 'moving_average/set', ['average'])]

class BrickletHumidityProxy(DeviceProxy):
    DEVICE_CLASS = BrickletHumidity
    TOPIC_PREFIX = 'bricklet/humidity'
    GETTER_SPECS = [('get_humidity', 'humidity', 'humidity')]

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

class BrickletTemperatureProxy(DeviceProxy):
    DEVICE_CLASS = BrickletTemperature
    TOPIC_PREFIX = 'bricklet/temperature'
    GETTER_SPECS = [('get_temperature', 'temperature', 'temperature')]

class BrickletTemperatureIRProxy(DeviceProxy):
    DEVICE_CLASS = BrickletTemperatureIR
    TOPIC_PREFIX = 'bricklet/temperature_ir'
    GETTER_SPECS = [('get_ambient_temperature', 'ambient_temperature', 'temperature'),
                    ('get_object_temperature', 'object_temperature', 'temperature'),
                    ('get_emissivity', 'emissivity', 'emissivity')]
    SETTER_SPECS = [('set_emissivity', 'emissivity/set', ['emissivity'])]

class Proxy(object):
    def __init__(self, brickd_host, brickd_port, broker_host, broker_port, update_interval):
        self.brickd_host = brickd_host
        self.brickd_port = brickd_port
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.update_interval = update_interval

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
        self.client.publish(topic, json.dumps(payload, separators=(',',':')), *args, **kwargs)

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
                                                                                    self.update_interval)
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
        if message.topic.startswith('bricklet/'):
            topic_prefix1, topic_prefix2, uid, topic_suffix = message.topic.split('/', 3)
            topic_prefix = topic_prefix1 + '/' + topic_prefix2

            if uid in self.device_proxies and topic_prefix == self.device_proxies[uid].TOPIC_PREFIX:
                payload = message.payload.strip()

                if len(payload) > 0:
                    try:
                        payload = json.loads(message.payload)
                    except:
                        print 'invalid payload' # FIXME
                        return
                else:
                    payload = {}

                self.device_proxies[uid].handle_message(topic_suffix, payload)

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
    parser.add_argument('--update-interval', dest='update_interval', type=int, default=UPDATE_INTERVAL,
                        help='update interval in seconds (default: {0})'.format(UPDATE_INTERVAL))

    args = parser.parse_args(sys.argv[1:])

    proxy = Proxy(args.brickd_host, args.brickd_port, args.broker_host, args.broker_port, args.update_interval)
    proxy.connect()
