import socket
import select
import sqlite3
import Player

"""
Problems:
1. Online time in seconds exceeds Long
2. encoding problem: chinese
"""

SERVER_PORT = 34567
MAX_USER_NUM = 100
MAX_MESSAGE_LENGTH = 2048
USER_DB_NAME = 'user_information.db'


class GameHall:

    def __init__(self, host, port):
        """ Initialize GameHall class"""
        self.conn = None
        self.login_time = {}  # store the time when user login
        self.server_sock = None
        self.host = host
        self.port = port
        self.all_sock = []

    def run(self):
        """
        Start the game hall server
        """
        self.check_and_create_user_login_table()
        self.create_server_socket((self.host, self.port))
        self.all_sock.append(self.server_sock)
        # start the server
        while True:
            read_socks, write_socks, error_socks = select.select(self.all_sock, [], [])
            for player in read_socks:
                if player is self.server_sock:  # a new connection request received
                    new_sock, address = player.accept()
                    self.handle_new_player(new_sock)
                else:  # receive message from a player
                    msg = player.sock.recv(MAX_MESSAGE_LENGTH)
                    if msg:
                        self.handle_msg(player, msg)
                    else:  # close socket
                        player.sock.close()
                        self.all_sock.remove(player)
            for sock in error_socks:
                sock.close()
                self.all_sock.remove(sock)

    def send_msg_to_player(self, player, msg):
        player.sock.sendall(msg + '\n\r')

    def handle_msg(self, player, msg):
        msg = msg.lstrip()
        print msg
        if msg.startswith('$register'):
            msg_list = msg.split()
            print msg_list
            if len(msg_list) == 3:
                self.register(player, msg_list[1], msg_list[2])
                return True
        if msg.startswith('$login'):
            msg_list = msg.split()
            if len(msg_list) == 3:
                is_ok, msg = self.login(player, msg_list[1], msg_list[2])
                self.send_msg_to_player(player, msg)
                return True
        # check to see if player is logged in
        if not player.is_already_login():
            self.send_msg_to_player(player, "sorry, you are not logged in")
            return False
        if msg.startswith('$logout'):
            msg_list = msg.split()
            if len(msg_list) == 1:
                self.logout(player)
                return True
        if msg.startswith('$chat'):
            msg_list = msg.split()
            if len(msg_list) == 2:
                pass
        # command error
        self.send_msg_to_player(player, "command error")
        self.send_help_msg(player)
        return False

    def handle_new_player(self, new_sock):
        new_player = Player.Player(new_sock)
        self.all_sock.append(new_player)
        self.send_msg_to_player(new_player, "Welcome to KGameHall")
        self.send_help_msg(new_player)

    def send_help_msg(self, player):
        player.sock.sendall("Commands:\n\r" +
                            "$register username password\n\r" +
                            "$login username password\n\r" +
                            "$chat message\n\r" +
                            "$logout\n\r")

    def create_server_socket(self, address):
        """
        Create the server socket and bind to the address
        """
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(address)
        self.server_sock.listen(MAX_USER_NUM)
        self.server_sock.setblocking(0)
        print "Server is listening at ", address

    def register(self, player, username, password):
        """
        Create a new account
        """
        if self.add_user_to_database(username, password):
            self.login(player, username, password)
            self.send_msg_to_player(player, "register and login success, you are now in game hall")
        else:
            self.send_msg_to_player(player, "username already exist")

    def login(self, player, username, password, is_already_register=False):
        """
        Handle user login
        """
        import datetime
        if not is_already_register:
            is_ok, msg = self.user_authentication(username, password)
            if not is_ok:  # login fail
                return False, msg
        player.set_username(username)
        player.set_login_time(datetime.datetime.now())
        return True, "login success"

    def logout(self, player):
        """
        Handle user logout
        """
        import datetime
        time_to_add = (datetime.datetime.now() - player.get_login_time()).seconds
        self.update_user_online_time(player.get_username(), time_to_add)
        self.send_msg_to_player(player, "logout success, online time: %d seconds" % time_to_add)
        player.sock.close()
        self.all_sock.remove(player)

    def check_and_create_user_login_table(self):
        """
         Create the user login table if it does not exist
        """
        self.conn = sqlite3.connect(USER_DB_NAME)  # connect to the user information database
        c = self.conn.cursor()
        try:
            # try to create the user_login table
            c.execute("CREATE TABLE user_login ( username TEXT PRIMARY KEY, password TEXT, online_time INTEGER)")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # user_login table already exist

    def add_user_to_database(self, username, password):
        """
        Add a new user into the database
        """
        import hashlib
        c = self.conn.cursor()
        encrypt_password = hashlib.sha256(password).hexdigest()
        try:
            c.execute("INSERT INTO user_login VALUES (?, ?, ?)", (username, encrypt_password, 0))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # user already exist

    def user_authentication(self, username, password):
        """
        Check to see if the user is valid
        """
        import hashlib
        encrypt_password = hashlib.sha256(password).hexdigest()
        c = self.conn.cursor()
        c.execute("SELECT * FROM user_login WHERE username=?", (username, ))
        res = c.fetchone()
        if res is None:
            return False, "%s not exist" % username
        if str(res[1]) != encrypt_password:
            return False, "invalid password"
        return True, ""

    def update_user_online_time(self, username, time_to_add):
        """
        Update user online time
        """
        c = self.conn.cursor()
        c.execute("SELECT * FROM user_login WHERE username=?", (username,))
        res = c.fetchone()
        new_online_time = res[2] + time_to_add
        c.execute("UPDATE user_login SET online_time=? WHERE username=?", (new_online_time, username))
        self.conn.commit()

    def get_user_online_time(self, username):
        """
        Get user online time
        """
        c = self.conn.cursor()
        c.execute("SELECT * FROM user_login WHERE username=?", (username,))
        res = c.fetchone()
        return res[2]


def main():
    import sys
    host = sys.argv[1] if len(sys.argv) >= 2 else ''
    gh = GameHall(host, SERVER_PORT)
    gh.run()

if __name__ == '__main__':
    main()

