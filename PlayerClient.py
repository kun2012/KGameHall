import socket
import select
import sys
import GameHallServer

MAX_MESSAGE_LENGTH = 2048


class PlayerClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_sock = None

    def run(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.connect((self.host, self.port))
        all_socks = [sys.stdin, self.server_sock]
        while True:
            read_socks, write_socks, error_socks = select.select(all_socks, [], [])
            for sock in read_socks:
                if sock is self.server_sock:  # message from server
                    msg = sock.recv(MAX_MESSAGE_LENGTH)
                    if not msg:
                        sys.exit(1)
                    else:
                        sys.stdout.write(msg)
                        # if not msg.startswith('logout'):
                        #    sys.stdout.write('> ')
                        #    sys.stdout.flush()
                else:
                    msg = sys.stdin.readline()
                    self.server_sock.sendall(msg)


def main():
    if len(sys.argv) < 2:
        print "Usage: python PlayerClient.py [hostname]"
        sys.exit(1)
    pc = PlayerClient(sys.argv[1], GameHallServer.SERVER_PORT)
    pc.run()

if __name__ == '__main__':
    main()
