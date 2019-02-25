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
        self.acl = {'anonymous': ['registration']}

        self.read_acl_file()

    def read_acl_file(self):
        if not self.acl_file:
            self.context.logger.warning("'file' acl parameter not found")
            return

        if not os.path.isfile(self.acl_file):
            self.context.logger.warning("acl file does not exist")
            return

        self.context.logger.debug("ACL plugin: reading ACL")

        acl_configs = read_yaml_config(self.acl_file)
        try:
            self.acl = acl_configs['acl']
        except:
            self.context.logger.error("ACL plugin: invalid ACL file format")

        self.context.logger.info(f"ACL plugin: read ACL for {len(self.acl)} users")

    @asyncio.coroutine
    def write_acl_file(self):
        if not self.acl_file:
            self.context.logger.warning("'file' acl parameter not found")
            return

        data = {'acl': self.acl}
        self.context.logger.debug("ACL plugin: writing ACL")
        write_yaml_config(data, self.acl_file)

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
        filter_result = super().topic_filtering(*args, **kwargs)
        if filter_result:
            session = kwargs.get('session', None)
            req_topic = kwargs.get('topic', None)
            if req_topic:
                username = session.username
                if username is None:
                    username = 'anonymous'
                self.context.logger.debug(f"topic_check: checking ACL for topic {req_topic} for user {username}")
                allowed_topics = self.acl.get(username, None)
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
        username = kwargs.get('username', "")
        topics = kwargs.get('topics', [])
        if (len(topics) == 0 or len(username) == 0):
            self.context.logger.warning(f"topic_check: invalid format in adding ACL for topics {topics} for user {username}")
            return False

        # so we can do an atomic modification in case of taken topics
        topics_to_add = []

        if username not in self.acl:
            self.acl[username] = topics
        else:
            for topic in topics:
                if (topic in self.acl[username]):
                    self.context.logger.error(f"topic_check: topic {topic} already exists for user {username}")
                    return False
                else:
                    topics_to_add.append(topic)
            
            self.acl[username].extend(topics_to_add)

        yield from self.write_acl_file()

        self.context.logger.info(f"topic_check: added ACL for topics {topics} for user {username}")

        return True

    @asyncio.coroutine
    def on_broker_post_shutdown(self, *args, **kwargs):
        yield from self.write_acl_file()
