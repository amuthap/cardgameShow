import socket
import threading
import pickle
import random
import time

# --- Re-use Card Game Logic Classes (or import if separated) ---
# (Including Card, Deck, Player, Game classes here for simplicity)

class Card:
    """Represents a standard playing card."""
    SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
    RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]

    def __init__(self, suit, rank):
        if suit not in self.SUITS:
            raise ValueError(f"Invalid suit: {suit}")
        if rank not in self.RANKS:
            raise ValueError(f"Invalid rank: {rank}")
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return f"{self.rank} of {self.suit}"

    def __repr__(self):
        return f"Card('{self.suit}', '{self.rank}')"

class Deck:
    """Represents a deck of 52 playing cards."""
    def __init__(self):
        self.cards = [Card(suit, rank) for suit in Card.SUITS for rank in Card.RANKS]
        self.shuffle()

    def shuffle(self):
        """Shuffles the deck."""
        random.shuffle(self.cards)
        print("Deck shuffled.")

    def deal_card(self):
        """Deals a single card from the top of the deck."""
        if not self.cards:
            return None
        return self.cards.pop()

    def __len__(self):
        return len(self.cards)

class Player:
    """Represents a player in the card game (Server-side)."""
    def __init__(self, name, player_id):
        self.name = name
        self.id = player_id # Unique ID for the player/client
        self.hand = []
        # No hand_rects needed on server

    def add_card(self, card):
        if card:
            self.hand.append(card)

    def play_card(self, card_index):
        if 0 <= card_index < len(self.hand):
            return self.hand.pop(card_index)
        else:
            print(f"Player {self.name}: Invalid card index {card_index} for hand size {len(self.hand)}")
            return None

    def __str__(self):
        return self.name

class Game:
    """Manages the card game state on the server."""
    def __init__(self):
        self.players = {} # Dictionary: player_id -> Player object
        self.deck = Deck()
        self.current_turn_player_id = None
        self.discard_pile = []
        self.player_order = [] # List of player_ids in turn order
        self.lock = threading.RLock() # Use RLock for re-entrant locking
        self.game_started = False
        self.min_players = 2 # Minimum players to start
        self.has_discarded = False  # Track if current player has discarded

    def add_player(self, player_id, name="Player"):
        with self.lock:
            if not self.game_started and player_id not in self.players:
                new_player = Player(f"{name} {len(self.players) + 1}", player_id)
                self.players[player_id] = new_player
                self.player_order.append(player_id)
                print(f"Player {new_player.name} (ID: {player_id}) connected.")
                return new_player
            return None

    def remove_player(self, player_id):
         with self.lock:
            if player_id in self.players:
                print(f"Player {self.players[player_id].name} (ID: {player_id}) disconnected.")
                # Handle turn if it was their turn (simple skip for now)
                if self.current_turn_player_id == player_id:
                    self.next_turn()
                # Remove from player order and players dict
                if player_id in self.player_order:
                    self.player_order.remove(player_id)
                del self.players[player_id]
                # Reset game if not enough players? (Optional)
                if self.game_started and len(self.players) < self.min_players:
                    print("Not enough players, resetting game.")
                    # self.reset_game() # Implement reset logic if needed
                    self.game_started = False # Simple stop for now


    def start_game(self, cards_per_player=7):
        with self.lock:
            if not self.game_started and len(self.players) >= self.min_players:
                print("Starting game...")
                self.deck = Deck() # New shuffled deck
                self.discard_pile = []
                self.has_discarded = False  # Reset discard flag
                # Deal cards
                for _ in range(cards_per_player):
                    for player_id in self.player_order:
                        card = self.deck.deal_card()
                        if card:
                            self.players[player_id].add_card(card)
                # Set first player's turn
                if self.player_order:
                    self.current_turn_player_id = self.player_order[0]
                self.game_started = True
                print(f"Game started. Current turn: {self.players[self.current_turn_player_id].name}")
                return True
            else:
                print(f"Cannot start game. Need at least {self.min_players} players. Currently {len(self.players)}.")
                return False

    def next_turn(self):
        print("[next_turn] Method entered.") # Log right at the start
        with self.lock: # RLock acquired
            print("[next_turn] Lock acquired. Attempting to advance turn...") # Updated log
            if not self.game_started or not self.player_order or self.current_turn_player_id is None:
                print("[next_turn] Cannot advance turn (pre-condition failed).")
                return

            # --- Simplified Core Logic ---
            try:
                current_index = self.player_order.index(self.current_turn_player_id)
                next_index = (current_index + 1) % len(self.player_order)
                self.current_turn_player_id = self.player_order[next_index]
                self.has_discarded = False  # Reset discard flag for new turn
                print(f"[next_turn] Turn advanced. New turn ID: {self.current_turn_player_id}") # Simple success log
            except ValueError:
                # This case should ideally not happen if player removal is handled correctly
                print(f"[next_turn] Error: Current player {self.current_turn_player_id} not in order {self.player_order}. Resetting turn.")
                if self.player_order:
                    self.current_turn_player_id = self.player_order[0]
                    self.has_discarded = False  # Reset discard flag
                else:
                    self.current_turn_player_id = None
            except Exception as e:
                # Catch any other unexpected error during the core logic
                print(f"[next_turn] Unexpected error during core logic: {e}")
                self.current_turn_player_id = None # Fallback

            # --- Log final result ---
            if self.current_turn_player_id and self.current_turn_player_id in self.players:
                 print(f"Next turn: {self.players[self.current_turn_player_id].name} (ID: {self.current_turn_player_id})")
            elif self.current_turn_player_id:
                 print(f"[next_turn] Warning: Next turn player ID {self.current_turn_player_id} not found in players dict.")
            else:
                 print("[next_turn] Turn could not be advanced or was reset.")

    def get_game_state(self, player_id):
        """Prepares the game state to be sent to a specific client."""
        with self.lock:
            if player_id not in self.players:
                return None # Player not in game

            player = self.players[player_id]
            other_players_hands = {
                pid: len(p.hand) for pid, p in self.players.items() if pid != player_id
            }

            state = {
                "my_hand": [str(card) for card in player.hand],
                "my_id": player_id,
                "players": {pid: {"name": p.name, "hand_size": len(p.hand)} for pid, p in self.players.items()}, # Send names and hand sizes
                "deck_size": len(self.deck),
                "discard_pile_top": str(self.discard_pile[-1]) if self.discard_pile else None,
                "current_turn_player_id": self.current_turn_player_id,
                "game_started": self.game_started,
                "player_order": self.player_order # Send order for UI if needed
            }
            return state

    def handle_action(self, player_id, action_data):
        """Handles actions received from a client."""
        with self.lock:
            if not self.game_started:
                print(f"Action rejected: Game not started.")
                return False, False  # Action not processed, don't advance turn

            if self.current_turn_player_id != player_id:
                print(f"Action rejected: Not player {player_id}'s turn.")
                return False, False  # Action not processed, don't advance turn

            action = action_data.get("action")
            player = self.players[player_id]
            action_processed = False
            advance_turn = False

            if action == "discard_card":
                # Can only discard if haven't already discarded this turn
                if not self.has_discarded:
                    card_str = action_data.get("card")
                    if card_str:
                        # Find the card in the player's hand
                        card_to_remove = None
                        for card in player.hand:
                            if str(card) == card_str:
                                card_to_remove = card
                                break

                        if card_to_remove:
                            try:
                                player.hand.remove(card_to_remove)
                                self.discard_pile.append(card_to_remove)
                                print(f"Player {player.name} discarded {card_to_remove}.")
                                self.has_discarded = True  # Mark that player has discarded
                                action_processed = True
                                advance_turn = False  # Don't advance turn after discard, wait for draw
                            except Exception as e:
                                print(f"[handle_action] Error processing discard: {e}")
                        else:
                            print(f"Player {player.name} attempted to discard card not in hand: {card_str}")
                    else:
                        print(f"Player {player.name}: Invalid discard_card action data.")
                else:
                    print(f"Action rejected: Player {player.name} has already discarded this turn.")

            elif action == "draw_card":
                # Can only draw if already discarded this turn
                if self.has_discarded:
                    if len(self.deck) > 0:
                        drawn_card = self.deck.deal_card()
                        player.add_card(drawn_card)
                        print(f"Player {player.name} drew a card: {drawn_card}")
                        action_processed = True
                        advance_turn = True  # Advance turn after successful draw
                        self.has_discarded = False  # Reset for next turn
                    else:
                        print("Deck is empty! Cannot draw a card.")
                else:
                    print(f"Action rejected: Player {player.name} must discard before drawing.")

            return action_processed, advance_turn


# --- Networking Server ---
SERVER_HOST = '127.0.0.1' # Listen only on the loopback interface
SERVER_PORT = 5555
BUFFER_SIZE = 4096

clients = {} # Dictionary: client_socket -> player_id
game = Game()

def broadcast_state():
    """Sends the current game state to all connected clients."""
    # Use list to avoid issues if clients disconnect during iteration
    current_clients = list(clients.items())
    print(f"[Broadcast] Broadcasting state to {len(current_clients)} client(s).") # Log start
    for client_socket, player_id in current_clients:
        print(f"[Broadcast] Preparing state for player {player_id}...") # Log player
        try:
            state = game.get_game_state(player_id)
            if state:
                print(f"[Broadcast] State for player {player_id} obtained. Pickling...") # Log state obtained
                try:
                    data = pickle.dumps(state)
                    print(f"[Broadcast] Pickling successful. Sending {len(data)} bytes to player {player_id}...") # Log pickle success
                    client_socket.sendall(data)
                    print(f"[Broadcast] Successfully sent state to player {player_id}.") # Log send success
                except Exception as pickle_send_err:
                    print(f"[Broadcast] Error pickling or sending state to player {player_id}: {pickle_send_err}")
                    # Consider removing client here if send fails repeatedly
                    # remove_client(client_socket)
            else:
                print(f"[Broadcast] Could not get game state for player {player_id}. Skipping broadcast to this client.") # Log state fail
        except (socket.error, EOFError, BrokenPipeError) as e:
            print(f"[Broadcast] Socket error broadcasting to player {player_id}: {e}. Removing client.")
            remove_client(client_socket) # Remove on socket errors
        except Exception as e:
             print(f"[Broadcast] Unexpected error broadcasting to player {player_id}: {e}")
             # Decide if unexpected errors should remove the client
             # remove_client(client_socket)
    print("[Broadcast] Finished broadcasting.") # Log end


def remove_client(client_socket):
    """Removes a client and associated player."""
    player_id = clients.get(client_socket)
    if player_id:
        game.remove_player(player_id)
        del clients[client_socket]
    try:
        client_socket.close()
    except socket.error:
        pass # Socket might already be closed
    # Broadcast updated state after removal
    broadcast_state()


def client_handler(client_socket, addr):
    """Handles communication with a single client."""
    print(f"Connection from {addr}")
    player_id = addr # Use address as unique ID for simplicity
    player = game.add_player(player_id)

    if not player:
        print(f"Failed to add player for {addr}. Disconnecting.")
        client_socket.close()
        return

    clients[client_socket] = player_id
    print(f"Current players: {len(game.players)}")

    # Try starting the game if enough players joined
    if not game.game_started and len(game.players) >= game.min_players:
        game.start_game()

    # Send initial state
    broadcast_state()

    try:
        while True:
            # Receive data from client
            try:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    print(f"Client {addr} (Player {player_id}) disconnected (no data).")
                    break # Connection closed by client

                action_data = pickle.loads(data)
                print(f"Received from {player.name}: {action_data}")

                # Process action
                print(f"[client_handler] Calling game.handle_action for player {player_id}...")
                action_processed, advance_turn = game.handle_action(player_id, action_data)
                print(f"[client_handler] game.handle_action returned: processed={action_processed}, advance_turn={advance_turn}")

                if action_processed:
                    # Advance turn if flag is set
                    if advance_turn:
                        print(f"[client_handler] Action successful and advance_turn is True. Calling next_turn()...")
                        game.next_turn() # Call next_turn here
                        print(f"[client_handler] next_turn() completed.")
                    else:
                        print(f"[client_handler] Action successful but advance_turn is False.")

                    # Broadcast updated state to all clients after successful action
                    print(f"[client_handler] Broadcasting state...")
                    broadcast_state()
                    print(f"[client_handler] Broadcast complete.")
                else:
                    print(f"[client_handler] Action was not successful. No turn advance or broadcast.")
                    # Optionally send an error message back to the specific client?
                    pass

            except (socket.error, EOFError, pickle.UnpicklingError, ConnectionResetError) as e:
                print(f"Error receiving/processing data from {addr} (Player {player_id}): {e}")
                break # Error or client disconnected abruptly
            except Exception as e:
                 print(f"Unexpected error in client handler for {addr} (Player {player_id}): {e}")
                 break

    finally:
        print(f"Closing connection for {addr} (Player {player_id})")
        remove_client(client_socket)


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Allow address reuse
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen(5) # Allow up to 5 connections in the backlog
        # Explicitly ensure the socket is in blocking mode (default, but good to be sure)
        server_socket.setblocking(True)
        print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")

        while True:
            print("Server waiting to accept a connection...") # Add log before accept
            client_socket, addr = server_socket.accept()
            print(f"Server accepted connection from {addr}") # Add log after accept
            # Start a new thread for each client
            thread = threading.Thread(target=client_handler, args=(client_socket, addr))
            thread.daemon = True # Allows server to exit even if threads are running
            thread.start()

    except socket.error as e:
        print(f"Server socket error: {e}")
    except KeyboardInterrupt:
        print("Server shutting down.")
    finally:
        print("Closing server socket.")
        server_socket.close()
        # Optionally notify connected clients about shutdown
        for sock in clients.keys():
            try:
                sock.close()
            except:
                pass


if __name__ == "__main__":
    start_server()
