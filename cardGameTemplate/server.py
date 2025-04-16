import socket
import threading
import pickle
from game_logic import Game

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5555
BUFFER_SIZE = 4096

clients = {}
game = Game()

def broadcast_state():
    """Sends the current game state to all connected clients."""
    for client_socket, player_id in list(clients.items()):
        try:
            state = game.get_game_state(player_id)
            if state:
                data = pickle.dumps(state)
                client_socket.sendall(data)
        except Exception as e:
            print(f"Error broadcasting to player {player_id}: {e}")
            remove_client(client_socket)

def remove_client(client_socket):
    """Removes a client and associated player."""
    player_id = clients.get(client_socket)
    if player_id:
        game.remove_player(player_id)
        del clients[client_socket]
    try:
        client_socket.close()
    except socket.error:
        pass
    broadcast_state()

def client_handler(client_socket, addr):
    """Handles communication with a single client."""
    print(f"Connection from {addr}")
    player_id = addr
    player = game.add_player(player_id)

    if not player:
        print(f"Failed to add player for {addr}. Disconnecting.")
        client_socket.close()
        return

    clients[client_socket] = player_id
    print(f"Current players: {len(game.players)}")

    if not game.game_started and len(game.players) >= game.min_players:
        game.start_game()

    broadcast_state()

    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                print(f"Client {addr} disconnected.")
                break

            action_data = pickle.loads(data)
            print(f"Received from {player.name}: {action_data}")

            if game.handle_action(player_id, action_data):
                broadcast_state()
    except Exception as e:
        print(f"Error with client {addr}: {e}")
    finally:
        print(f"Closing connection for {addr}")
        remove_client(client_socket)

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            threading.Thread(target=client_handler, args=(client_socket, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()
