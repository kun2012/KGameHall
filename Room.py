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

	def boardcast(self, msg):
		for p in self.players:
			p.sock.sendall(msg.encode())

