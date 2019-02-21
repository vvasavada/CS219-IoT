import logging
import asyncio
from passlib.hash import sha256_crypt

class RegistrationPlugin:
    def __init__(self, context):
        self.context = context
        self._users = dict()
        try:
            self.auth_config = self.context.config['auth']
        except KeyError:
            self.context.logger.warning("'auth' section not found in context configuration")


    def _read_password_file(self):
        password_file = self.auth_config.get('password-file', None)
        if password_file:
            try:
                with open(password_file) as f:
                    self.context.logger.debug("Reading user database from %s" % password_file)
                    for l in f:
                        line = l.strip()
                        if not line.startswith('#'):    # Allow comments in files
                            (username, pwd_hash) = line.split(sep=":", maxsplit=3)
                            if username:
                                self._users[username] = pwd_hash
                                self.context.logger.debug("user %s , hash=%s" % (username, pwd_hash))
                self.context.logger.debug("%d user(s) read from file %s" % (len(self._users), password_file))
            except FileNotFoundError:
                self.context.logger.warning("Password file %s not found" % password_file)
        else:
            self.context.logger.debug("Configuration parameter 'password_file' not found")

    @asyncio.coroutine
    def register(self, *args, **kwargs):
        self._read_password_file()
        topic = kwargs.get('topic', None)
        username = topic.split('/')[1]
        password = topic.split('/')[2]
        if username in self._users:
            self.context.logger.debug("Registration failed: user already exists")
            return False
        password_file = self.auth_config.get('password-file', None)
        with open(password_file, 'a+') as f:
            pwd_hash = sha256_crypt.hash(password)
            f.write(username + ':' + pwd_hash + '\n')
            self._users[username] = pwd_hash
        return True
