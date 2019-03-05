# Copyright (c) 2015 Nicolas JOUANIN
#
# See the file license.txt for copying permission.
import logging
import asyncio
from passlib.apps import custom_app_context as pwd_context
from hbmqtt.utils import read_yaml_config, write_yaml_config

class BaseAuthPlugin:
    def __init__(self, context):
        self.context = context
        try:
            self.auth_config = self.context.config['auth']
        except KeyError:
            self.context.logger.warning("'auth' section not found in context configuration")

    def authenticate(self, *args, **kwargs):
        if not self.auth_config:
            # auth config section not found
            self.context.logger.warning("'auth' section not found in context configuration")
            return False
        return True


class AnonymousAuthPlugin(BaseAuthPlugin):
    def __init__(self, context):
        super().__init__(context)

    @asyncio.coroutine
    def authenticate(self, *args, **kwargs):
        authenticated = super().authenticate(*args, **kwargs)
        if authenticated:
            allow_anonymous = self.auth_config.get('allow-anonymous', True)  # allow anonymous by default
            if allow_anonymous:
                authenticated = True
                self.context.logger.debug("Authentication success: config allows anonymous")
            else:
                try:
                    session = kwargs.get('session', None)
                    authenticated = True if session.username else False
                    if self.context.logger.isEnabledFor(logging.DEBUG):
                        if authenticated:
                            self.context.logger.debug("Authentication success: session has a non empty username")
                        else:
                            self.context.logger.debug("Authentication failure: session has an empty username")
                except KeyError:
                    self.context.logger.warning("Session informations not available")
                    authenticated = False
        return authenticated


class FileAuthPlugin(BaseAuthPlugin):
    def __init__(self, context):
        super().__init__(context)
        self._users = dict()
        self._read_password_file()

    def _read_password_file(self):
        try:
            password_file = self.auth_config.get('password-file', None)
            if password_file:
                self._users = read_yaml_config(password_file)
            else:
                self.context.logger.debug("Configuration parameter 'password_file' not found")
        except FileNotFoundError:
            pass

    @asyncio.coroutine
    def authenticate(self, *args, **kwargs):
        try:
            self._read_password_file()
        except:
            self.context.logger.warning("Password file not found")
        authenticated = super().authenticate(*args, **kwargs)
        if authenticated:
            session = kwargs.get('session', None)
            if session.username:
                try:
                    username = session.username.split('-')[0]
                    deviceid = session.username.split('-')[1]
                    password = session.password.split('-')[0]
                    devicekey = session.password.split('-')[1]
                except IndexError:
                    self.context.logger.error("Authentication failed: Credentials not in proper format")
                    return False

                authenticated_user = False
                pwd_hash = self._users[username]['password']
                if not pwd_hash:
                    self.context.logger.debug("No hash found for user '%s'" % username)
                else:
                    authenticated_user = pwd_context.verify(password, pwd_hash)

                authenticated_device = False
                key_hash = self._users[username]['devices'][deviceid]['key']
                if not key_hash:
                    self.context.logger.debug("No key found for device '%s'" % deviceid)
                else:
                    authenticated_device = pwd_context.verify(devicekey, key_hash)
            else:
                return None
        return authenticated_user and authenticated_device
