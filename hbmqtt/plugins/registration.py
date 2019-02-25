import logging
import asyncio
from passlib.hash import sha256_crypt
import os

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
        if self.password_file:
            try:
                with open(self.password_file) as f:
                    self.context.logger.debug("Reading user database from %s" % self.password_file)
                    for l in f:
                        line = l.strip()
                        if not line.startswith('#'):    # Allow comments in files
                            (username, pwd_hash) = line.split(sep=":", maxsplit=3)
                            if username:
                                self._users[username] = pwd_hash
                                self.context.logger.debug("user %s , hash=%s" % (username, pwd_hash))
                self.context.logger.debug("%d user(s) read from file %s" % (len(self._users), self.password_file))
            except FileNotFoundError:
                self.context.logger.warning("Password file %s not found" % self.password_file)
        else:
            self.context.logger.error("Configuration parameter 'password_file' not found")

    @asyncio.coroutine
    def write_password_file(self, *args, **kwargs):
        self.context.logger.debug("Registration user persistence: starting")
        password_file_backup = self.password_file + ".bck"
        # save a backup of our old user database just in case
        if (os.path.isfile(password_file_backup)):
            os.remove(password_file_backup)
        if (os.path.isfile(self.password_file)):
            os.rename(self.password_file, password_file_backup)
        with open(self.password_file, 'w+') as f:
            for username, pwd_hash in self._users.items():
                f.write(username + ':' + pwd_hash + '\n')
        self.context.logger.debug("Registration user persistence: success")

    @asyncio.coroutine
    def register(self, *args, **kwargs):
        if 'data' not in kwargs:
            self.context.logger.warning("Registration failed: no data provided")
            return None

        data = str(kwargs['data'], 'UTF-8')
        if ('/' not in data):
            self.context.logger.error("Registration failed: invalid registration format")
            return None

        username = data.split('/')[0]
        password = data.split('/')[1]
        self.context.logger.info(f"Registering user {username}...")
        if username in self._users:
            self.context.logger.debug("Registration failed: user already exists")
            return None

        pwd_hash = sha256_crypt.hash(password)
        self._users[username] = pwd_hash
        self.context.logger.info(f"Registered user {username}")
        return username

    @asyncio.coroutine
    def on_broker_post_shutdown(self, *args, **kwargs):
        yield from self.write_password_file()
