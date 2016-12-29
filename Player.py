class Player:
    def __init__(self, sock):
        sock.setblocking(0)
        self.sock = sock
        self.username = None
        self.login_time = None

    def fileno(self):
        return self.sock.fileno()

    def set_login_time(self, login_time):
        self.login_time = login_time

    def get_login_time(self):
        return self.login_time

    def set_username(self, username):
        self.username = username

    def get_username(self):
        return self.username

    def is_already_login(self):
        return self.login_time is not None
