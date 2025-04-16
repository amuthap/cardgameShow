import pygame
import os
import socket
import pickle
import threading
import time

# --- Networking Client ---
SERVER_HOST = '127.0.0.1' # Connect to localhost (change if server is elsewhere)
SERVER_PORT = 5555
BUFFER_SIZE = 4096

client_socket = None
network_lock = threading.Lock()
latest_game_state = None # Store the most recent state received from server
client_id = None # Will be assigned by server (or derived)
unexpected_disconnect = False # Flag for reconnection logic
is_reconnecting = False # Flag to manage reconnection state

def connect_to_server():
    global client_socket, client_id, unexpected_disconnect, is_reconnecting
    # Reset client_id on new connection attempt
    client_id = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set a timeout for the connection attempt (e.g., 5 seconds)
        client_socket.settimeout(5.0)
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        client_socket.settimeout(None) # Reset timeout after connection
        print("Connected to server.")
        unexpected_disconnect = False # Reset flag on successful connection
        is_reconnecting = False
        return True
    except socket.timeout:
        print("Connection attempt timed out.")
        client_socket = None
        return False
    except socket.error as e:
        print(f"Failed to connect to server: {e}")
        client_socket = None
        return False
    except Exception as e:
        print(f"An unexpected error occurred during connection: {e}")
        client_socket = None
        return False

def send_action(action_data):
    """Send an action to the server."""
    if client_socket:
        try:
            data = pickle.dumps(action_data)
            client_socket.sendall(data)
            print(f"Sent action: {action_data}")
        except (socket.error, BrokenPipeError) as e:
            print(f"Error sending action: {e}")
            disconnect(caller="send_action")
        except Exception as e:
            print(f"Unexpected error sending action: {e}")

def receive_updates():
    global latest_game_state, client_id, client_socket, unexpected_disconnect
    print("Receiver thread started.") # Added print
    while client_socket:
        try:
            print("Receiver waiting for data...") # Added print
            data = client_socket.recv(BUFFER_SIZE)
            print(f"Receiver received {len(data)} bytes.") # Added print
            if not data:
                print("Receiver: Server disconnected (received empty data). Setting unexpected_disconnect.") # Added print
                unexpected_disconnect = True # Treat as unexpected
                disconnect(caller="receive_updates_empty_data") # Pass caller info
                break
            with network_lock:
                print("Receiver attempting to load pickled data...") # Added print
                latest_game_state = pickle.loads(data)
                print("Receiver successfully loaded pickled data.") # Added print
                if client_id is None and latest_game_state: # Assign client_id on first state receive
                    # Ensure my_id exists before accessing
                    if "my_id" in latest_game_state:
                        client_id = latest_game_state.get("my_id")
                    else:
                        print("Warning: 'my_id' not found in initial game state.")
                # print(f"Received state: {latest_game_state}") # Debug: print received state
        except (socket.error, EOFError, pickle.UnpicklingError, ConnectionResetError, BrokenPipeError) as e:
            print(f"Receiver: Error receiving data: {e}. Setting unexpected_disconnect.") # Added print
            unexpected_disconnect = True # Mark as unexpected for reconnection
            disconnect(caller=f"receive_updates_exception: {e}") # Pass caller info
            break
        except Exception as e:
            print(f"Receiver: Unexpected error: {e}. Setting unexpected_disconnect.") # Added print
            unexpected_disconnect = True # Mark as unexpected for reconnection
            disconnect(caller=f"receive_updates_unexpected_exception: {e}") # Pass caller info
            break
    print("Receiver thread finished.") # Added print

def disconnect(caller="unknown"): # Add caller parameter with default
    global client_socket
    if client_socket:
        print(f"Disconnecting from server (called by: {caller})...")
        try:
            client_socket.close()
        except socket.error as e:
            print(f"Error closing socket: {e}")
        finally:
            client_socket = None
            print("Client socket set to None.")

# --- Pygame Setup (Restore original constants) ---
pygame.init()
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 700
CARD_WIDTH = 71
CARD_HEIGHT = 100
HAND_Y_OFFSET = 500
DECK_POS = (50, 50)
DISCARD_POS = (200, 50)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN_TABLE = (7, 99, 36)
RED = (200, 0, 0)
FONT = pygame.font.Font(None, 36)
SMALL_FONT = pygame.font.Font(None, 24)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Multiplayer Card Game Client")
clock = pygame.time.Clock()
IMAGE_DIR = "images/cards" # Define the image directory

# --- Load Card Images ---
def load_card_images():
    """Load card images using filename stems as keys."""
    card_images = {}
    try:
        print(f"Loading images from: {os.path.abspath(IMAGE_DIR)}")
        if not os.path.isdir(IMAGE_DIR):
            print(f"Error: Image directory not found: {IMAGE_DIR}")
            return card_images

        for filename in os.listdir(IMAGE_DIR):
            if filename.endswith(".png"):
                # Use the filename stem (lowercase, no .png, no trailing 2) as the key
                name_part = filename.replace(".png", "")
                if name_part == "card_back":
                    card_key = "back"
                else:
                    # Remove trailing '2' if present (e.g., jack_of_clubs2 -> jack_of_clubs)
                    card_key = name_part.rstrip('2').lower()

                image_path = os.path.join(IMAGE_DIR, filename)
                try:
                    image = pygame.image.load(image_path).convert_alpha()
                    image = pygame.transform.scale(image, (CARD_WIDTH, CARD_HEIGHT))
                    card_images[card_key] = image
                    # print(f"Loaded: {filename} as key '{card_key}'") # Debug print
                except pygame.error as e:
                    print(f"Error loading image {filename}: {e}")
                except Exception as e:
                    print(f"Unexpected error loading image {filename}: {e}")

        if "back" not in card_images:
            print("Warning: Card back image ('card_back.png') not found or failed to load.")

        print(f"Loaded {len(card_images)} card images.")
        print(f"Available image keys (filename based): {list(card_images.keys())}") # Debug: List loaded keys

    except Exception as e:
        print(f"An error occurred in load_card_images: {e}")

    return card_images

# --- Drawing Functions (Restore original functions) ---
def draw_text(text, font, color, surface, x, y):
    """Draw text on the given surface at the specified position."""
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)

def draw_button(text, rect, color, font=FONT):
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, BLACK, rect, 2)
    draw_text(text, font, WHITE, screen, rect.x + 10, rect.y + 5)

# --- Helper Functions ---
def get_card_key_from_display_name(display_name):
    """Converts a display name (e.g., 'Ace of Spades') to a filename key (e.g., 'ace_of_spades')."""
    if not display_name or not isinstance(display_name, str):
        return None # Handle invalid input

    # Convert to lowercase and replace spaces with underscores
    key = display_name.lower().replace(' ', '_')

    # Special handling for numeric ranks (ensure they are part of the key)
    # e.g., "10 of hearts" -> "10_of_hearts"
    # This logic assumes the input format is consistent (e.g., "10 of Hearts")
    # No specific change needed here as the replace already handles it.

    # print(f"Converted '{display_name}' to key '{key}'") # Optional debug
    return key

def get_card_value(card_str):
    # Extract rank from card string (e.g., 'Jack of Clubs')
    if not card_str or not isinstance(card_str, str):
        return ""
    rank = card_str.split(' ')[0]
    if rank.isdigit():
        return int(rank)
    rank = rank.lower()
    if rank == 'jack':
        return 11
    elif rank == 'queen':
        return 12
    elif rank == 'king':
        return 13
    elif rank == 'ace':
        return 1
    else:
        return ""

# Store card rects locally for click detection
my_hand_rects = []

def draw_my_hand(hand_cards, card_images, x_start, y_pos):
    """Draw the player's hand on the screen."""
    global my_hand_rects
    # Check if the hand has changed before updating
    # Convert display names to keys for comparison and drawing
    current_hand_keys = [get_card_key_from_display_name(card) for card in hand_cards if card]

    # Determine if rects need updating (simple length check for now)
    needs_update = len(my_hand_rects) != len(current_hand_keys)

    if needs_update:
        my_hand_rects = []  # Clear old rects
        overlap = 20
        for i, card_str in enumerate(hand_cards):
            card_key = get_card_key_from_display_name(card_str) # Use helper function
            if card_key:
                image = card_images.get(card_key, card_images.get("back"))
                if image:
                    card_x = x_start + i * (CARD_WIDTH - overlap)
                    card_rect = pygame.Rect(card_x, y_pos, CARD_WIDTH, CARD_HEIGHT)
                    my_hand_rects.append(card_rect)
                    screen.blit(image, card_rect.topleft)
                    # Draw value below the card
                    value = get_card_value(card_str)
                    draw_text(str(value), SMALL_FONT, WHITE, screen, card_x + CARD_WIDTH // 2 - 8, y_pos + CARD_HEIGHT + 5)
                else:
                    print(f"Error: Image not found for card '{card_str}' (key: '{card_key}')")
            else:
                print(f"Warning: Could not generate key for card '{card_str}'")
        # print(f"Updated my_hand_rects: {my_hand_rects}")
    else:
        # Draw using existing rects
        overlap = 20
        for i, card_str in enumerate(hand_cards):
            card_key = get_card_key_from_display_name(card_str) # Use helper function
            if card_key and i < len(my_hand_rects):
                image = card_images.get(card_key, card_images.get("back"))
                if image:
                    card_rect = my_hand_rects[i]
                    screen.blit(image, card_rect.topleft)
                    value = get_card_value(card_str)
                    draw_text(str(value), SMALL_FONT, WHITE, screen, card_rect.x + CARD_WIDTH // 2 - 8, card_rect.y + CARD_HEIGHT + 5)
                else:
                    print(f"Error: Image not found for card '{card_str}' (key: '{card_key}')")
            elif not card_key:
                 print(f"Warning: Could not generate key for card '{card_str}' during redraw")

def draw_other_players(players_data, my_id, card_images):
    """Draw other players' information and their card backs."""
    y_offset = 10
    x_pos = SCREEN_WIDTH - 160  # Position for opponent info
    for pid, data in players_data.items():
        if pid != my_id:
            draw_text(f"{data.get('name', 'Unknown')}: {data.get('hand_size', '?')} cards", SMALL_FONT, WHITE, screen, x_pos, y_offset)
            # Draw card backs for their hand (optional visual)
            if 'back' in card_images:
                hand_size = data.get('hand_size', 0)
                for i in range(hand_size):
                    screen.blit(card_images['back'], (x_pos + i * 10, y_offset + 20))  # Simple overlap
            y_offset += 60  # Space out players

def draw_deck(deck_size, card_images, position):
    """Draw the deck with the number of cards remaining."""
    if deck_size > 0 and 'back' in card_images:
        screen.blit(card_images['back'], position)
        if deck_size > 1:
            screen.blit(card_images['back'], (position[0] + 2, position[1] + 2))  # Slight offset for visual effect
    draw_text(f"{deck_size}", FONT, WHITE, screen, position[0] + CARD_WIDTH + 5, position[1] + CARD_HEIGHT // 2 - 18)

def draw_discard_pile(top_card_str, card_images, position):
    """Draw the top card of the discard pile."""
    if top_card_str:
        card_key = get_card_key_from_display_name(top_card_str) # Use helper function
        if card_key:
            image = card_images.get(card_key, card_images.get("back"))
            if image:
                screen.blit(image, position)
            else:
                print(f"Error: Image not found for discard card '{top_card_str}' (key: '{card_key}')")
                pygame.draw.rect(screen, BLACK, (position[0], position[1], CARD_WIDTH, CARD_HEIGHT), 1) # Placeholder
        else:
            print(f"Warning: Could not generate key for discard card '{top_card_str}'")
            pygame.draw.rect(screen, BLACK, (position[0], position[1], CARD_WIDTH, CARD_HEIGHT), 1) # Placeholder
    else:
        # Draw empty discard pile placeholder
        pygame.draw.rect(screen, BLACK, (position[0], position[1], CARD_WIDTH, CARD_HEIGHT), 1)
        draw_text("Discard", FONT, WHITE, screen, position[0] + 5, position[1] + 5)

# --- Main Game Loop (Client) ---
def main():
    global client_socket, latest_game_state, client_id, unexpected_disconnect, is_reconnecting

    running = True
    card_images = load_card_images()
    deck_rect = pygame.Rect(DECK_POS[0], DECK_POS[1], CARD_WIDTH, CARD_HEIGHT)
    pending_rect = pygame.Rect(DISCARD_POS[0] + CARD_WIDTH + 30, DISCARD_POS[1], CARD_WIDTH, CARD_HEIGHT)
    same_number_btn_rect = pygame.Rect(pending_rect.x, pending_rect.y + CARD_HEIGHT + 20, 140, 40)
    show_btn_rect = pygame.Rect(SCREEN_WIDTH - 200, SCREEN_HEIGHT - 80, 120, 50)
    new_game_btn_rect = pygame.Rect(SCREEN_WIDTH//2 - 60, 180, 180, 50)
    has_discarded_this_turn = False
    show_result = None
    show_result_time = 0

    if not connect_to_server():
        print("Failed to connect to server. Exiting.")
        return

    threading.Thread(target=receive_updates, daemon=True).start()

    print("Waiting for initial game state from server...")
    while latest_game_state is None and client_socket is not None:
        if unexpected_disconnect:
             print("Disconnected while waiting for initial state.")
             break
        time.sleep(0.1)

    if latest_game_state is None:
        print("Failed to receive initial game state. Exiting.")
        if client_socket:
            disconnect(caller="main_initial_state_fail")
        pygame.quit()
        return
    print("Initial game state received.")
    if client_id is None:
        print("Warning: client_id not set after receiving initial state.")
        with network_lock:
            client_id = latest_game_state.get("my_id")
        if client_id is None:
            print("Error: Could not determine client_id. Exiting.")
            disconnect(caller="main_client_id_fail")
            pygame.quit()
            return

    while running:
        clicked = False
        mouse_pos = pygame.mouse.get_pos()
        same_number_btn_clicked = False
        show_btn_clicked = False
        new_game_btn_clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
                if pending_discard and same_number_btn_rect.collidepoint(mouse_pos):
                    same_number_btn_clicked = True
                if show_btn_rect.collidepoint(mouse_pos):
                    show_btn_clicked = True
                if show_result and new_game_btn_rect.collidepoint(mouse_pos):
                    new_game_btn_clicked = True

        screen.fill(GREEN_TABLE)

        current_state = None
        with network_lock:
            if latest_game_state:
                current_state = latest_game_state.copy()
                if current_state.get("current_turn_player_id") != client_id:
                    has_discarded_this_turn = False

        if current_state and client_id is not None:
            my_turn = current_state.get("current_turn_player_id") == client_id
            my_hand = current_state.get("my_hand", [])
            deck_size = current_state.get("deck_size", 0)
            discard_pile_top = current_state.get("discard_pile_top", None)
            pending_discard = current_state.get("pending_discard", None)
            pending_discard_player = current_state.get("pending_discard_player", None)

            if my_turn and clicked and not show_result:
                # If not yet discarded, allow discard
                if not has_discarded_this_turn and not pending_discard:
                    for i, card_rect in enumerate(my_hand_rects):
                        if card_rect.collidepoint(mouse_pos):
                            if i < len(my_hand):
                                discard_card = my_hand[i]
                                send_action({"action": "discard_card", "card": discard_card})
                                print(f"Attempting to discard card: {discard_card}")
                                has_discarded_this_turn = True
                                clicked = False
                                break
                # If pending discard exists and player has discarded, allow draw from deck or discard pile
                elif has_discarded_this_turn and pending_discard:
                    if same_number_btn_clicked:
                        send_action({"action": "same_number_skip"})
                        print("Attempting Same Number skip")
                    elif deck_rect.collidepoint(mouse_pos) and deck_size > 0:
                        send_action({"action": "draw_card"})
                        print("Attempting to draw a card from deck")
                        has_discarded_this_turn = False
                        clicked = False
                    elif pygame.Rect(DISCARD_POS[0], DISCARD_POS[1], CARD_WIDTH, CARD_HEIGHT).collidepoint(mouse_pos):
                        send_action({"action": "draw_from_discard_pile"})
                        print("Attempting to draw the top card from discard pile")
                        has_discarded_this_turn = False
                        clicked = False

            if show_btn_clicked and not show_result:
                send_action({"action": "show"})
                print("SHOW button clicked!")
                show_btn_clicked = False

            # Draw hand, other players, deck, discard pile
            draw_my_hand(my_hand, card_images, 50, 400)
            draw_other_players(current_state.get("players", {}), client_id, card_images)
            draw_deck(deck_size, card_images, DECK_POS)
            draw_discard_pile(discard_pile_top, card_images, DISCARD_POS)

            # Draw pending discard visually (support multiple cards)
            if pending_discard:
                for idx, pending_card in enumerate(pending_discard):
                    card_key = get_card_key_from_display_name(pending_card)
                    image = card_images.get(card_key, card_images.get("back"))
                    if image:
                        # Offset each pending card horizontally
                        x_offset = pending_rect.x + idx * (CARD_WIDTH + 10)
                        screen.blit(image, (x_offset, pending_rect.y))
                        pygame.draw.rect(screen, (255, 215, 0), (x_offset, pending_rect.y, CARD_WIDTH, CARD_HEIGHT), 3)
                        draw_text("Pending", SMALL_FONT, WHITE, screen, x_offset, pending_rect.y - 20)
                # Draw Same Number button below the first pending card
                draw_button("Same Number", same_number_btn_rect, (0, 128, 255), SMALL_FONT)

            # Draw SHOW button only if game not ended
            if not show_result:
                draw_button("SHOW", show_btn_rect, (255, 100, 0), FONT)

            # Display result if available
            if current_state.get("show_result"):
                show_result = current_state["show_result"]
                show_result_time = time.time()
            if show_result:
                color = (0, 200, 0) if show_result == "Winner" else (200, 0, 0)
                draw_text(f"You are a {show_result}!", FONT, color, screen, SCREEN_WIDTH//2 - 100, 100)
                # Draw New Game button
                draw_button("New Game", new_game_btn_rect, (0, 180, 0), FONT)
                # Block all other actions until new game
                if new_game_btn_clicked:
                    send_action({"action": "new_game"})
                    show_result = None
                    print("New Game button clicked!")
                    # Optionally reset local state
                    has_discarded_this_turn = False
                    continue

            # Draw turn status
            if my_turn and not show_result:
                status_text = "Your turn - "
                if not has_discarded_this_turn and not pending_discard:
                    status_text += "Discard a card"
                elif has_discarded_this_turn and pending_discard:
                    status_text += "Draw from deck or pending discard"
                else:
                    status_text += "Waiting..."
                draw_text(status_text, FONT, WHITE, screen, 10, 10)
            elif not show_result:
                draw_text(f"Waiting for other player", FONT, WHITE, screen, 10, 10)

            # Block all game actions if show_result is set
            if show_result:
                pygame.display.flip()
                clock.tick(60)
                continue

        pygame.display.flip()
        clock.tick(60)

    disconnect(caller="main_cleanup")
    pygame.quit()

# --- Run the Client ---
if __name__ == "__main__":
    main()
