class Room:
    def __init__(self, name):
        self.name = name
        self.players = []
        self.is_game_start = False
        self.already_has_a_winner = False
        self.game_msg = ""
        self.game_number = set()
        self.player_point = {} # mapping from players to 21 game points
        self.valid_math_expression_symbol = '0123456789+-*/)('

    def start_21game(self):
        """
        Start the 21 points game, generate 4 random numbers and send to players in this room
        """
        self.is_game_start = True
        self.already_has_a_winner = False
        self.player_point = {}
        self.generate_21game_number()
        self.boardcast(self.game_msg)

    def end_21game(self):
        """
        Current game end
        """
        if not self.is_game_start: # the game in this room is not yet started
            return
        max_point = None
        winner = None
        if not self.already_has_a_winner:
            for k, v in self.player_point.iteritems():
                if v[0] > 21: # answer exceed 21
                    continue
                if max_point is None or v[0] > max_point:
                    max_point = v[0]
                    winner = k
            if max_point is None:
                self.boardcast("21 point game: what a pity, nobody wins the game\n")
            else:
                self.boardcast("21 point game: " + winner.get_username() + " is the winner(" +
                               self.player_point[winner][1] + "=" + str(max_point) + ")\n")
        self.is_game_start = False

    def handle_21game_player_answer(self, player, msg):
        """
        Handle the 21 point game answer of a player
        """
        import string
        if not self.is_game_start:
            self.send_msg_to_player(player, "The 21 point game is not yet started\n")
            return
        if self.already_has_a_winner:
            self.send_msg_to_player(player, "Current game already has a winner\n")
            return
        if player in self.player_point: # player can only submit answer once
            self.send_msg_to_player(player, "You have already submit an answer\n")
            return
        # check to see whether the answer is valid
        math_exp = msg.strip()
        for c in math_exp:
            if c not in string.whitespace and c not in self.valid_math_expression_symbol:
                self.send_msg_to_player(player, "Invalid symbols\n")
                return
        # extract numbers from math_exp
        ans_nums = []
        i = 0
        sl = len(math_exp)
        while i < sl:
            while i < sl and math_exp[i] not in string.digits:
                i += 1
            if i >= sl:
                break
            x = 0
            while i < sl and math_exp[i] in string.digits:
                x = x * 10 + ord(math_exp[i]) - ord('0')
                i += 1
            ans_nums.append(x)
        ans_nums.sort()
        # test if two sets are equal
        if len(ans_nums) != 4:
            self.send_msg_to_player(player, "21 point game: use less than 4 numbers\n")
            return
        for i in range(4):
            if self.game_number[i] != ans_nums[i]:
                self.send_msg_to_player(player, "21 point game: use invalid numbers\n")
                return
        try:
            ans = eval(math_exp)
            if ans == 21: # the player wins
                self.already_has_a_winner = True
                self.boardcast("21 point game: " + player.get_username() + \
                               " wins(" + math_exp + "=" + str(ans) + ")\n")
            elif ans > 21:
                self.send_msg_to_player(player, "21 point game: invalid answer(>21)\n")
            else:
                self.player_point[player] = (ans, math_exp)
        except SyntaxError:
            self.send_msg_to_player(player, "21 point game: invalid math expression\n")

    @staticmethod
    def send_msg_to_player(player, msg):
        try:
            player.sock.sendall(msg.encode())
        except Exception:  # ignore send error
            pass

    def generate_21game_number(self):
        """
        Generate 4 number for the 21 point game
        """
        import random
        self.game_number = []
        for i in range(4):
            self.game_number.append(random.randint(1, 10))
        self.game_number.sort()
        self.game_msg = "21 point game: " + " ".join(str(x) for x in self.game_number) \
            + "(python math expression, valid symbols are '" \
            + self.valid_math_expression_symbol + "')\n"

    def get_name(self):
        return self.name

    def add_player(self, player):
        self.players.append(player)

    def remove_player(self, player):
        self.players.remove(player)

    def num_of_players(self):
        return len(self.players)

    def boardcast(self, msg, except_player=None):
        for p in self.players:
            if except_player is None or p != except_player:
                self.send_msg_to_player(p, msg)

