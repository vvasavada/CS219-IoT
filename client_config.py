import logging
import asyncio
import sys

from hbmqtt.client import MQTTClient
from hbmqtt.mqtt.constants import QOS_1, QOS_2

logger = logging.getLogger(__name__)

config = {
    'will': {
        'topic': '/will/client',
        'message': b'Dead or alive',
        'qos': 0x01,
        'retain': True,
    },
}
C = MQTTClient(config=config)

@asyncio.coroutine
def test_coro():
    yield from C.connect('mqtts://vaibhavagg2-device1:password-device1@0.0.0.0:8883', cafile='ca.crt')
    tasks = [
        asyncio.ensure_future(C.publish('vaibhavagg2/config', ' '.join(sys.argv[1:]).encode())),
    ]
    yield from asyncio.wait(tasks)
    logger.info("messages published")
    yield from C.disconnect()


if __name__ == '__main__':
    if (len(sys.argv) < 2):
        print(f"Usage: {sys.argv[0]} cmd")
        exit()
    formatter = "[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=formatter)
    asyncio.get_event_loop().run_until_complete(test_coro())

