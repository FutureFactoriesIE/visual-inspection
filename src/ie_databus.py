from threading import Event, Lock
import paho.mqtt.client as mqtt
import json
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Sensor:
    name: str
    id: str
    data_type: str
    qc: int
    ts: str
    val: float


class IEDatabus:
    def __init__(self, username: str, password: str):
        # mqtt client setup
        self._client = mqtt.Client()
        self._client.username_pw_set(username, password)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect('ie-databus')

        # setup sensor access vars
        self._sensors = {}
        self._sensors_lock = Lock()
        self._sensor_headers = {}
        self._ready_event = Event()

        # public class vars
        self.write_topic = 'ie/d/j/simatic/v1/s7c1/dp/w/USC_PLC'

    @property
    def sensors(self) -> Dict[str, Sensor]:
        with self._sensors_lock:
            value = self._sensors.copy()
        return value

    @sensors.setter
    def sensors(self, value: Dict[str, Sensor]):
        with self._sensors_lock:
            self._sensors = value

    def start(self):
        self._client.loop_start()
        self._ready_event.wait()

    def stop(self):
        self._client.loop_stop()

    def reinit(self):
        self._sensor_headers.clear()
        self._sensors.clear()
        self._ready_event.clear()
        self._client.reconnect()

    def write_to_tag(self, tag: str, data: Any):
        # tag parameter should be the tag id (a str)
        payload = {'seq': 1, 'vals': [{'id': self.sensors[tag].id, 'val': data}]}
        msg_info = self._client.publish(self.write_topic, json.dumps(payload))
        msg_info.wait_for_publish()

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print('Connected successfully')
        else:
            print('Error: ' + str(rc))
        client.subscribe('ie/#')

    def _on_message(self, client, userdata, msg):
        data = json.loads(msg.payload.decode())
        if len(self._sensor_headers) == 0:
            try:
                dpds = data['connections'][0]['dataPoints'][0][
                    'dataPointDefinitions']
            except KeyError:
                pass
            else:
                for data_point in dpds:
                    self._sensor_headers[data_point['id']] = data_point
        else:
            # create sensors
            sensors = {}
            for value_dict in data['vals']:
                header = self._sensor_headers[value_dict['id']]
                sensors[header['name']] = Sensor(name=header['name'],
                                                 id=header['id'],
                                                 data_type=header['dataType'],
                                                 qc=value_dict['qc'],
                                                 ts=value_dict['ts'],
                                                 val=value_dict['val'])
            self.sensors = sensors
            self._ready_event.set()


if __name__ == '__main__':
    databus = IEDatabus('edge', 'edge')
    databus.start()

    for key, sensor in databus.sensors.items():
        print(f'{key}: {sensor.val}')
