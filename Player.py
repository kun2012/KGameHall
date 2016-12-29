import datetime


class Player:
    def __init__(self, sock):
        sock.setblocking(0)
        self.sock = sock
        self.username = None
        self.login_time = None

    def fileno(self):
        return self.sock.fileno()

    def login(self, username):
        self.username = username
        self.login_time = datetime.datetime.now()

    def logout(self):
        self.username = None
        self.login_time = None

    def get_online_time(self):
        return (datetime.datetime.now() - self.login_time).seconds

    def set_username(self, username):
        self.username = username

    def get_username(self):
        return self.username

    def is_already_login(self):
        return self.login_time is not None
