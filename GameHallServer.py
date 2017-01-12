import socket
import select
import sqlite3
import Player
import Room
import argparse
import sys


class GameHall:

    def __init__(self, host, port, max_connect_num, dbname, game_time_delta, game_time_duration):
        """ Initialize GameHall class"""
        self.max_connect_num = max_connect_num
        self.dbname = dbname
        self.buffer_len = 2048
        self.game_time_delta = game_time_delta # means game start at every GAME_TIME_DELTA minutes, GAME_TIME_DELTA=30 means game start at 00:00, 00:30, 01:00, ... , 23:30
        self.game_time_duration = game_time_duration
        self.conn = None
        self.server_sock = None
        self.host = host
        self.port = port
        self.all_socks = []
        self.room_map = {} # mapping from room name to room object
        self.player_map = {} # mapping from player name to player object
        self.player_to_room = {} # mapping from player name to room name

    def run(self):
        """
        Start the game hall server
        """
        import datetime
        self.check_and_create_user_login_table()
        self.create_server_socket((self.host, self.port))
        self.all_socks.append(self.server_sock)
        is_game_start = False
        game_start_time = None
        # start the server
        while True:
            tim = datetime.datetime.now()
            if not is_game_start and tim.minute % self.game_time_delta == 0 and tim.second == 0 \
                    and (game_start_time is None or (tim - game_start_time).seconds >= self.game_time_delta * 60):  # game may be finished in less than 1 seconds
                is_game_start = True
                game_start_time = tim
                for r in self.room_map.values():
                    r.start_21game()
            if is_game_start and (tim - game_start_time).seconds >= self.game_time_duration: # game end
                is_game_start = False
                for r in self.room_map.values():
                    r.end_21game()
            # Get message from players
            read_socks, write_socks, error_socks = select.select(self.all_socks, [], self.all_socks, 0.5)
            for player in read_socks:
                if player is self.server_sock:  # a new connection request received
                    new_sock, address = player.accept()
                    self.handle_new_player(new_sock)
                else:  # receive message from a player
                    msg = player.sock.recv(self.buffer_len)
                    if msg:
                        self.handle_msg(player, msg)
                    else:  # close socket
                        self.handle_player_disconnect(player)
            for player in error_socks:
                self.handle_player_disconnect(player)

    def handle_player_disconnect(self, player):
        """
        Player client disconnect
        """
        self.quit(player, player_disconnect=True)


    def send_msg_to_player(self, player, msg):
        try:
            player.sock.sendall(msg)
        except Exception: # ignore send error
            pass

    def handle_msg(self, player, msg):
        msg = msg.lstrip()
        msg_list = msg.split()
        if len(msg_list) <= 0:
            self.send_msg_to_player(player, "Empty command, type $help to get instructions\n")
        elif msg_list[0] == '$help' and len(msg_list) == 1:
            self.send_help_msg(player)
        elif msg_list[0] == '$register' and len(msg_list) == 3:
            self.register(player, msg_list[1], msg_list[2])
        elif msg_list[0] == '$login' and len(msg_list) == 3:
            self.login(player, msg_list[1], msg_list[2])
        elif msg_list[0] == '$logout' and len(msg_list) == 1:
            if player.is_already_login():
                self.logout(player)
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0] == '$quit' and len(msg_list) == 1:
            self.quit(player)
        elif msg_list[0] == '$online_time' and len(msg_list) == 1:
            if player.is_already_login():
                self.send_msg_to_player(player, "Online time: %d seconds\n" % player.get_online_time())
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0] == '$history_online_time' and len(msg_list) == 1:
            if player.is_already_login():
                self.send_msg_to_player(player, "History online time: %d seconds\n" % self.get_history_online_time(player.get_username()))
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0] == '$chat':
            if player.is_already_login():
                self.handle_player_chat(player, msg)
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0] == '$chatall':
            if player.is_already_login():
                self.chat_to_hall(player, msg)
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0].startswith('$chat@'):
            if player.is_already_login():
                self.chat_to_other_player(player, msg)
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0] == '$build' and len(msg_list) == 2:
            if player.is_already_login():
                self.build_room(player, msg_list[1])
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0] == '$join' and len(msg_list) == 2:
            if player.is_already_login():
                self.join_room(player, msg_list[1])
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0] == '$rooms' and len(msg_list) == 1:
            if player.is_already_login():
                self.show_rooms(player)
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0] == '$leave' and len(msg_list) == 1:
            if player.is_already_login():
                name = player.get_username()
                if name in self.player_to_room:
                    self.leave_room(player)
                else:
                    self.send_msg_to_player(player, "You are not in any room\n")
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        elif msg_list[0] == '$21game' and len(msg_list) > 1:
            if player.is_already_login():
                player_name = player.get_username()
                if player_name in self.player_to_room:
                    self.room_map[self.player_to_room[player_name]].handle_21game_player_answer(player, msg[len('$21game'):])
                else:
                    self.send_msg_to_player(player, "You are not in any room\n")
            else:
                self.send_msg_to_player(player, "You are not yet logged in\n")
        else: # command error
            self.send_msg_to_player(player, "Wrong command, type $help to get instructions\n")

    def build_room(self, player, roomname):
        if player.get_username() in self.player_to_room:
            self.send_msg_to_player(player, "You are already in a room, please leave first\n")
        elif roomname in self.room_map:
            self.send_msg_to_player(player, "Room %s already exist, try other room name\n" % roomname)
        else:
            r = Room.Room(roomname)
            r.add_player(player)
            self.player_to_room[player.get_username()] = roomname
            self.room_map[roomname] = r
            self.send_msg_to_player(player, "Build room %s success\n" % roomname)

    def show_rooms(self, player):
        self.send_msg_to_player(player, "Num of rooms: %d\n" % len(self.room_map))
        for k, v in self.room_map.iteritems():
            self.send_msg_to_player(player, k + "(" + str(v.num_of_players()) + " players)\n")

    def join_room(self, player, roomname):
        if roomname not in self.room_map:
            self.send_msg_to_player(player, "Room %s does not exist\n" % roomname)
        else:
            player_name = player.get_username()
            if player_name in self.player_to_room:
                # player is already in a room
                old_roomname = self.player_to_room[player_name]
                if old_roomname == roomname:  # in the same room
                    self.send_msg_to_player(player, "You are already in room %s\n" % roomname)
                else:
                    self.leave_room(player)
                    r = self.room_map[roomname]
                    r.add_player(player)
                    self.player_to_room[player_name] = roomname
                    r.boardcast("Welcome to room %s, %s\n" % (roomname, player_name))
            else: # player not in any room
                r = self.room_map[roomname]
                r.add_player(player)
                self.player_to_room[player_name] = roomname
                r.boardcast("Welcome to room %s, %s\n" % (roomname, player_name))

    def leave_room(self, player):
        """
        Leave current room and back into game hall
        """
        player_name = player.get_username()
        roomname = self.player_to_room[player_name]
        del self.player_to_room[player_name]
        r = self.room_map[roomname]
        r.remove_player(player)
        if r.num_of_players() == 0:
            del self.room_map[roomname]
        else:
            r.boardcast("Player %s has already left the room\n" % player_name)

    def handle_player_chat(self, player, msg):
        new_msg = player.get_username() + ': ' + msg[len('$chat'):].lstrip()
        if new_msg[-1] != '\n':
            new_msg += '\n'
        if player.get_username() in self.player_to_room: # player in a room, just chat in this room
            r = self.room_map[self.player_to_room[player.get_username()]]
            r.boardcast(new_msg, except_player=player)
        else: # player is in game hall, talk to other player who is in game hall
            for name, other in self.player_map.iteritems():
                if name not in self.player_to_room and other != player:
                    self.send_msg_to_player(other, new_msg)

    def chat_to_hall(self, player, msg):
        new_msg = player.get_username() + ': ' + msg[len('$chatall'):].lstrip()
        if new_msg[-1] != '\n':
            new_msg += '\n'
        # send message to other players
        for other in self.all_socks:
            if other is not player and other is not self.server_sock:
                self.send_msg_to_player(other, new_msg)

    def chat_to_other_player(self, player, msg):
        msg_list = msg.split()
        other_name = msg_list[0][len('$chat@'):]
        if other_name not in self.player_map:
            self.send_msg_to_player(player, "Player %s is not yet logged in\n" % other_name)
        else:
            new_msg = player.get_username() + ': ' + msg[len('$chat@' + other_name):].lstrip()
            if new_msg[-1] != '\n':
                new_msg += '\n'
            self.send_msg_to_player(self.player_map[other_name], new_msg)

    def handle_new_player(self, new_sock):
        new_player = Player.Player(new_sock)
        self.all_socks.append(new_player)
        self.send_msg_to_player(new_player, "Welcome to KGameHall\nType $help to get instructions\n")

    def send_help_msg(self, player):
        self.send_msg_to_player(player, "Commands:\n" +
                            "\t$register username password\n" +
                            "\t$login username password\n" +
                            "\t$chat message\n" +
                            "\t$chat@username message\n" +
                            "\t$chatall message\n" +
                            "\t$logout\n" +
                            "\t$quit\n" +
                            "\t$online_time\n" +
                            "\t$history_online_time\n" +
                            "\t$build roomname\n" +
                            "\t$join roomname\n" +
                            "\t$leave\n" +
                            "\t$rooms\n" +
                            "\t$21game math_expression\n")

    def create_server_socket(self, address):
        """
        Create the server socket and bind to the address
        """
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(address)
        self.server_sock.listen(self.max_connect_num)
        self.server_sock.setblocking(0)
        print "Server is listening at ", address

    def register(self, player, username, password):
        """
        Create a new account
        """
        if player.is_already_login():
            self.send_msg_to_player(player, "You are already logged in, logout out first\n")
            return
        if self.add_user_to_database(username, password):
            self.login(player, username, password)
        else:
            self.send_msg_to_player(player, "Player %s already exist\n" % username)

    def login(self, player, username, password, is_already_register=False):
        """
        Handle user login
        """
        if player.is_already_login():
            self.send_msg_to_player(player, "You are already logged in, logout out first\n")
            return
        # user already login in
        if username in self.player_map:
            self.send_msg_to_player(player, "%s is already logged in\n" % username)
            return
        if not is_already_register:
            msg = self.user_authentication(username, password)
            if msg:  # login fail
                self.send_msg_to_player(player, msg)
                return
        # valid player
        player.login(username)
        self.player_map[username] = player
        if is_already_register:
            self.send_msg_to_player(player, "Register and login success, you are now in game hall\n")
        else:
            self.send_msg_to_player(player, "Login success\n")

    def logout(self, player, player_disconnect=False):
        """
        Handle player logout, leave room first if player is already in a room
        """
        name = player.get_username()
        if name in self.player_to_room: # in a room, leave first
            self.leave_room(player)
        time_to_add = player.get_online_time()
        self.update_history_online_time(player.get_username(), time_to_add)
        del self.player_map[player.get_username()]
        player.logout()
        if not player_disconnect:
            self.send_msg_to_player(player, "Logout success, online time: %d seconds\n" % time_to_add)

    def quit(self, player, player_disconnect=False):
        """
        Logout and destroy socket
        """
        if player.is_already_login():
            self.logout(player, player_disconnect)
        player.sock.close()
        self.all_socks.remove(player)

    def check_and_create_user_login_table(self):
        """
         Create the user login table if it does not exist
        """
        self.conn = sqlite3.connect(self.dbname)  # connect to the user information database
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
            return "Player %s doesn't exist\n" % username
        if str(res[1]) != encrypt_password:
            return "Invalid password\n"
        return None

    def update_history_online_time(self, username, time_to_add):
        """
        Update user online time
        """
        c = self.conn.cursor()
        c.execute("SELECT * FROM user_login WHERE username=?", (username,))
        res = c.fetchone()
        new_online_time = res[2] + time_to_add
        c.execute("UPDATE user_login SET online_time=? WHERE username=?", (new_online_time, username))
        self.conn.commit()

    def get_history_online_time(self, username):
        """
        Get user online time
        """
        c = self.conn.cursor()
        c.execute("SELECT * FROM user_login WHERE username=?", (username,))
        res = c.fetchone()
        return res[2]


def main(sys_args):
    host = ""
    port = 34567
    max_connect_num = 1000
    dbname = 'player_info.db'
    game_time_delta = 1
    game_time_duration = 30
    parser = argparse.ArgumentParser(description="A game hall server support talking and playing games")
    parser.add_argument("-o", "--host", help="Host name")
    parser.add_argument("-p", "--port", help="Server port")
    parser.add_argument("-n", "--dbname", help="Player database name")
    parser.add_argument("-u", "--connectnum", help="Number of client connection")
    parser.add_argument("-d", "--time_delta", help="21 point game time delta(in minutes)")
    parser.add_argument("-l", "--time_duration", help = "21 point game time duration(in seconds)")
    args = parser.parse_args(args=sys_args)
    if args.host:
        host = args.host
    if args.port:
        port = int(args.port)
    if args.dbname:
        dbname = args.dbname
    if args.connectnum:
        max_connect_num = int(args.connectnum)
    if args.time_delta:
        game_time_delta = int(args.time_delta)
    if args.time_duration:
        game_time_duration = int(args.time_duration)
    # start game hall server
    gh = GameHall(host, port, max_connect_num, dbname, game_time_delta, game_time_duration)
    gh.run()

if __name__ == '__main__':
    main(sys.argv[1:])

