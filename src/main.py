import base64
import datetime
import io
import json
import time
from typing import Dict, Any

import paho.mqtt.client as mqtt
import pytz
from PIL import Image, ImageOps

from edge_interface import EdgeInterface
from ie_databus import IEDatabus

interface = EdgeInterface(__name__)

ie_broker = IEDatabus('edge', 'edge')
ie_broker.start()

est = pytz.timezone('US/Eastern')
utc = pytz.utc
start_date = datetime.datetime(2001, 1, 1, tzinfo=utc)


class Flowcharts:
    edge_device = './static/flowcharts/edge_device.png'
    iphone_inspection = './static/flowcharts/iphone_inspection.png'
    inspection_pass = './static/flowcharts/inspection_pass.png'
    inspection_fail = './static/flowcharts/inspection_fail.png'


def on_page_load():
    interface.pages['/'].set_image_src('flowchart', Flowcharts.iphone_inspection)


def create_image(image_data: str, is_pass: bool) -> str:
    # add white margin to base_image
    old_base_image = Image.open(io.BytesIO(base64.b64decode(image_data)))
    old_bordered_base_image = ImageOps.expand(old_base_image, border=7, fill='#00B14F' if is_pass else 'red')
    base_image = ImageOps.expand(old_bordered_base_image, border=50, fill='white')

    # create overlay
    overlay = Image.open('static/symbols/pass.png' if is_pass else 'static/symbols/fail.png')
    overlay = overlay.resize((150, 150))

    # add overlay
    base_image.paste(overlay, (base_image.size[0] - overlay.size[0], 0), overlay)

    # re-encode image to base64
    with io.BytesIO() as buffer:
        base_image.save(buffer, format='png')
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode()


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("ibmvi/threshold/FFLAB/USC001")


def on_message(client, userdata, msg):
    data: Dict[str, Any] = json.loads(msg.payload)

    # inspection image (with check or X)
    inspection_image = create_image(data['base64InspectionImage'], data['isPass'])
    interface.pages['/'].set_image_base64('inspection_image', inspection_image, 'png')

    # battery life indicator
    interface.pages['/'].set_text('battery_life', str(round(data['deviceInfo']['battery'] * 100)) + '%')

    # date and time of packet indicator
    date = (start_date + datetime.timedelta(seconds=data['time'])).astimezone(est)
    interface.pages['/'].set_text('date_time', date.strftime('%Y-%m-%d %H:%M:%S'))

    # flowchart displaying current process
    interface.pages['/'].set_image_src('flowchart', Flowcharts.edge_device)

    # raw json from IBMMVI without the really long keys
    new_data = {key: value for key, value in data.items() if
                key not in ['base64InspectionImage', 'scoresAndThresholds']}
    interface.pages['/'].set_text('raw_json_text', str(new_data))

    # decide if stop is necessary
    time.sleep(2)
    if data['isPass']:
        interface.pages['/'].set_image_src('flowchart', Flowcharts.inspection_pass)
    else:
        interface.pages['/'].set_image_src('flowchart', Flowcharts.inspection_fail)
        # tell PLC to stop
        ie_broker.write_to_tag('I_TwoWayCommunicator', 1)


if __name__ == '__main__':
    interface.add_page('/', 'index.html')
    interface.pages['/'].on_load = on_page_load
    interface.start_server()

    public_broker = mqtt.Client()
    public_broker.on_connect = on_connect
    public_broker.on_message = on_message
    public_broker.username_pw_set('FFLAB', 'passw0rd')
    public_broker.connect('test.mosquitto.org')
    public_broker.loop_start()

    interface.wait_forever()
