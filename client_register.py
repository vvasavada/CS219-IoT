import logging
import asyncio

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
    yield from C.connect('mqtts://0.0.0.0:8883', cafile='ca.crt')
    tasks = [
        asyncio.ensure_future(C.publish('registration/test2/test', b'TEST MESSAGE WITH QOS_0')),
    ]
    yield from asyncio.wait(tasks)
    logger.info("messages published")
    yield from C.disconnect()


if __name__ == '__main__':
    formatter = "[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=formatter)
    asyncio.get_event_loop().run_until_complete(test_coro())
