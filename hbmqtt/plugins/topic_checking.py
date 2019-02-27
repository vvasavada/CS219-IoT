import asyncio
from hbmqtt.utils import read_yaml_config, write_yaml_config
import os

class BaseTopicPlugin:
    def __init__(self, context):
        self.context = context
        try:
            self.topic_config = self.context.config['topic-check']
            self.enabled = self.topic_config['enabled']
        except KeyError:
            self.context.logger.warning("'topic-check' section not found in context configuration")

    def topic_filtering(self, *args, **kwargs):
        if not self.topic_config:
            # auth config section not found
            self.context.logger.warning("'topic-check' section not found in context configuration")
            return False
        if not self.enabled:
            # enabled flag false
            self.context.logger.warning("'topic-check' disabled in context configuration")
            return False
        return True


class TopicTabooPlugin(BaseTopicPlugin):
    def __init__(self, context):
        super().__init__(context)
        self._taboo = ['prohibited', 'top-secret', 'data/classified']

    @asyncio.coroutine
    def topic_filtering(self, *args, **kwargs):
        filter_result = super().topic_filtering(*args, **kwargs)
        if filter_result:
            session = kwargs.get('session', None)
            topic = kwargs.get('topic', None)
            if topic:
                if session.username != 'admin' and topic in self._taboo:
                    return False
                return True
            else:
                return False
        else:
            return True

class TopicAccessControlListPlugin(BaseTopicPlugin):
    def __init__(self, context):
        super().__init__(context)
        if 'file' not in self.topic_config['acl']:
            self.context.logger.error("ACL plugin: no 'file' parameter defined")
            os.exit(1)

        self.acl_file = self.topic_config['acl']['file']
        self._users = dict()

    @asyncio.coroutine
    def write_acl_file(self):
        if not self.acl_file:
            self.context.logger.warning("'file' acl parameter not found")
            return

        if len(self._users.keys()) == 0:
            return

        self.context.logger.debug("ACL plugin: writing ACL")
        write_yaml_config(self._users, self.acl_file)

    @staticmethod
    def topic_ac(topic_requested, topic_allowed):
        req_split = topic_requested.split('/')
        allowed_split = topic_allowed.split('/')
        ret = True
        for i in range(max(len(req_split), len(allowed_split))):
            try:
                a_aux = req_split[i]
                b_aux = allowed_split[i]
            except IndexError:
                ret = False
                break
            if b_aux == '#':
                break
            elif (b_aux == '+') or (b_aux == a_aux):
                continue
            else:
                ret = False
                break
        return ret

    @asyncio.coroutine
    def topic_filtering(self, *args, **kwargs):
        if len(self._users.keys()) == 0:
            return True
        filter_result = super().topic_filtering(*args, **kwargs)
        if filter_result:
            session = kwargs.get('session', None)
            req_topic = kwargs.get('topic', None)
            publish = kwargs.get('publish', None)
            if req_topic:
                if session.username is None:
                    username = 'anonymous'
                else:
                    try:
                        username = session.username.split('-')[0]
                        deviceid = session.username/split('-')[1]
                    except IndexError:
                        self.context.logger.error("topic_check failed: invalid username-deviceid format")
                        return False
                self.context.logger.debug(f"topic_check: checking ACL for topic {req_topic} for user {username}")
                if publish:
                    allowed_topics = self._users[username]['acl_publish_all'].extend(self._users[username]['acl_publish'][deviceid])
                else:
                    allowed_topics = self._users[username]['acl_subscribe_all'].extend(self._users[username]['acl_subscribe'][deviceid])
                if allowed_topics:
                    for allowed_topic in allowed_topics:
                        if self.topic_ac(req_topic, allowed_topic):
                            return True
                    return False
                else:
                    return False
            else:
                return False
        else:
            return True

    @asyncio.coroutine
    def add_user_acl(self, *args, **kwargs):
        if len(self._users.keys()) == 0:
            self._users = read_yaml_config(self.acl_file)
        username = kwargs.get('username', "")
        device = kwargs.get('device', "")
        topics = kwargs.get('topics', {})
        if (len(topics) == 0 or len(username) == 0 or len(device) == 0):
            self.context.logger.warning(f"topic_check: invalid format in adding ACL for topics {topics} for user {username} and device {device}")
            return False

        # so we can do an atomic modification in case of taken topics
        topics_pub_all_to_add = []
        topics_sub_all_to_add = []
        topics_pub_to_add = {}
        topics_sub_to_add = {}

        if username not in self._users:
            self.context.logger.error(f"topic_check: user {username} not found")
            return False
        else:
            topics_pub_all = topics['acl_publish_all']
            topics_sub_all = topics['acl_subscribe_all']
            topics_pub = topics['acl_publish']
            topics_sub = topics['acl_subscribe']

            for topic in topics_pub_all:
                if topic in self._users[username]['acl_publish_all']:
                    self.context.logger.error(f"topic_check: topic {topic} already exists for user {username}")
                    return False
                else:
                    topics_pub_all_to_add.append(topic)
            for topic in topics_sub_all:
                if topic in self._users[username]['acl_subscribe_all']:
                    self.context.logger.error(f"topic_check: topic {topic} already exists for user {username}")
                    return False
                else:
                    topics_sub_all_to_add.append(topic)
            for device, topics in topics_pub.items():
                for topic in topics:
                    if topic in self._users[username]['acl_publish'][device]:
                        self.context.logger.error(f"topic_check: topic {topic} already exists for device {device}")
                        return False
                    else:
                        if device in topics_pub_to_add:
                            topics_pub_to_add[device].append(topic)
                        else:
                            topics_pub_to_add[device] = [topic]
            for device, topics in topics_sub.items():
                for topic in topics:
                    if topic in self._users[username]['acl_subscribe'][device]:
                        self.context.logger.error(f"topic_check: topic {topic} already exists for device {device}")
                        return False
                    else:
                        if device in topics_sub_to_add:
                            topics_sub_to_add[device].append(topic)
                        else:
                            topics_sub_to_add[device] = [topic]
            
            self._users[username]['acl_publish_all'].extend(topics_pub_all_to_add)
            self._users[username]['acl_subscribe_all'].extend(topics_sub_all_to_add)

            for device, topics in topics_pub_to_add.items():
                self._users[username]['acl_publish'][device].extend(topics)

            for device, topics in topics_sub_to_add.items():
                self._users[username]['acl_subscribe'][device].extend(topics)

        yield from self.write_acl_file()

        self.context.logger.info(f"topic_check: added ACL for topics {topics} for user {username}")

        return True

    @asyncio.coroutine
    def on_broker_post_shutdown(self, *args, **kwargs):
        yield from self.write_acl_file()
