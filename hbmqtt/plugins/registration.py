import logging
import asyncio
from passlib.hash import sha256_crypt
import os
from hbmqtt.utils import read_yaml_config, write_yaml_config

class RegistrationPlugin:
    def __init__(self, context):
        self.context = context
        self._users = dict()
        try:
            self.auth_config = self.context.config['auth']
        except KeyError:
            self.context.logger.warning("'auth' section not found in context configuration")

        try:
            self.password_file = self.auth_config['password-file']
        except KeyError:
            self.context.logger.error("Registration plugin: no 'password-file' parameter defined")
            os.exit(1)

        self._read_password_file()


    def _read_password_file(self):
        try:
            self._users = read_yaml_config(self.password_file)
        except:
            pass

    @asyncio.coroutine
    def write_password_file(self, *args, **kwargs):
        self.context.logger.debug("Registration user persistence: starting")
        password_file_backup = self.password_file + ".bck"
        # save a backup of our old user database just in case
        if (os.path.isfile(password_file_backup)):
            os.remove(password_file_backup)
        if (os.path.isfile(self.password_file)):
            os.rename(self.password_file, password_file_backup)
        write_yaml_config(self._users, self.password_file)
        self.context.logger.debug("Registration user persistence: success")

    @asyncio.coroutine
    def register(self, *args, **kwargs):
        if 'data' not in kwargs:
            self.context.logger.error("Registration failed: no data provided")
            return None, None

        data = str(kwargs['data'], 'UTF-8')
        try:
            username = data.split()[0].split('/')[0]
            password = data.split()[0].split('/')[1]
            deviceid = data.split()[1].split('/')[0]
            devicekey = data.split()[1].split('/')[1]
            self.context.logger.info(f"Registering user {username}...")
        except IndexError:
            self.context.logger.error("Registration failed: invalid registration format")
            return None, None
        if username in self._users:
            self.context.logger.error("Registration failed: user already exists")
            return None, None

        self._read_password_file()

        pwd_hash = sha256_crypt.hash(password)
        self._users[username] = {'password': pwd_hash}

        key_hash = sha256_crypt.hash(devicekey)
        self._users[username]['devices'] = {deviceid : {'key' : key_hash}}
        self._users[username]['acl_publish_all'] = []
        self._users[username]['acl_subscribe_all'] = []
        self._users[username]['acl_publish'] =  {deviceid : []}
        self._users[username]['acl_subscribe'] = {deviceid : []}
        self.context.logger.info(f"Registered user {username}")
        return username, deviceid

    @asyncio.coroutine
    def register_device(self, *args, **kwargs):
        username = kwargs['username']
        deviceid = kwargs['deviceid']
        devicekey = kwargs['devicekey']

        self._read_password_file()
        
        if deviceid in self._users[username]['devices']:
            self.context.logger.error("Device registration failed: device already exists")
            return None, None

        key_hash = sha256_crypt.hash(devicekey)
        self._users[username]['devices'][deviceid] = {'key' : key_hash}
        self._users[username]['acl_publish'][deviceid] = []
        self._users[username]['acl_subscribe'][deviceid] = []
        self.context.logger.info(f"Registed device {deviceid}")
        return username, deviceid

    @asyncio.coroutine
    def on_broker_post_shutdown(self, *args, **kwargs):
        yield from self.write_password_file()
