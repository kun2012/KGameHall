class Room:
	def __init__(self, name):
		self.name = name
		self.players = []

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
				p.sock.sendall(msg.encode())

