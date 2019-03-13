import logging
import asyncio

from hbmqtt.client import MQTTClient, ClientException
from hbmqtt.mqtt.constants import QOS_1, QOS_2

logger = logging.Logger("client_sub")

@asyncio.coroutine
def uptime_coro():
    C = MQTTClient()
    yield from C.connect('mqtts://vaibhavagg2-device2:password-device2@0.0.0.0:8883', cafile='ca.crt')
    yield from C.subscribe([
            ('vaibhavagg2/test', QOS_1),
            ('vaibhavagg2/device2/test', QOS_1)
         ])
    try:
        for i in range(1, 100):
            message = yield from C.deliver_message()
            packet = message.publish_packet
            print("%d:  %s => %s" % (i, packet.variable_header.topic_name, str(packet.payload.data)))
        yield from C.unsubscribe(['a/b', 'test_topic'])
        yield from C.disconnect()
    except ClientException as ce:
        logger.error("Client exception: %s" % ce)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(uptime_coro())
