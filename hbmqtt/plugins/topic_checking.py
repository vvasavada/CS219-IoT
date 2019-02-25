import asyncio
from hbmqtt.utils import read_yaml_config

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
                acl_file = self.topic_config['acl'].get('file', None)
                if not acl_file:
                    self.context.logger.warning("'file' acl parameter not found")
                    return False
                acl_configs = read_yaml_config(acl_file)
                allowed_topics = acl_configs['acl'].get(username, None)
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
