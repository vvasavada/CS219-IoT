import sys
import logging
import asyncio
import os
from hbmqtt.broker import Broker
from hbmqtt.version import get_version
from docopt import docopt
from hbmqtt.utils import read_yaml_config
import pkg_resources
logger = logging.getLogger(__name__)


def main(*args, **kwargs):
    if sys.version_info[:2] < (3, 4):
        logger.fatal("Error: Python 3.4+ is required")
        sys.exit(-1)

    distribution = pkg_resources.Distribution(__file__)
    entry_point = pkg_resources.EntryPoint.parse('persistence = hbmqtt.plugins.persistence:SQLitePlugin', dist=distribution)
    distribution._ep_map = {'hbmqtt.plugins': {'persistence': entry_point}}
    pkg_resources.working_set.add(distribution)

    formatter = "[%(asctime)s] :: %(levelname)s - %(message)s"
    level = logging.DEBUG
    logging.basicConfig(level=level, format=formatter)

    config = read_yaml_config(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'broker_config.yaml'))
    logger.debug("Using default configuration")

    print(config)

    loop = asyncio.get_event_loop()
    broker = Broker(config)
    try:
        loop.run_until_complete(broker.start())
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(broker.shutdown())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
