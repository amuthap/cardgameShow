import socket
import pickle
import threading
import pygame
import os
from game_logic import Card

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5555
BUFFER_SIZE = 4096

pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Multiplayer Card Game")
clock = pygame.time.Clock()

CARD_WIDTH, CARD_HEIGHT = 71, 100  # Standard size for your images

client_socket = None
latest_game_state = None
network_lock = threading.Lock()

def connect_to_server():
    global client_socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((SERVER_HOST, SERVER_PORT))
    print("Connected to server.")

def receive_updates():
    global latest_game_state
    while True:
        try:
            data = client_socket.recv(BUFFER_SIZE)
            with network_lock:
                latest_game_state = pickle.loads(data)
        except Exception as e:
            print(f"Error receiving updates: {e}")
            break

def send_action(action_data):
    try:
        data = pickle.dumps(action_data)
        client_socket.sendall(data)
    except Exception as e:
        print(f"Error sending action: {e}")

def card_str_to_key(card_str):
    # Converts "10 of clubs" to "10_of_clubs"
    return card_str.lower().replace(" ", "_")

def load_card_images():
    card_images = {}
    img_dir = os.path.join("..", "images", "cards")
    for fname in os.listdir(img_dir):
        if fname.endswith(".png"):
            key = fname.replace(".png", "")
            card_images[key] = pygame.transform.scale(
                pygame.image.load(os.path.join(img_dir, fname)), (CARD_WIDTH, CARD_HEIGHT)
            )
    # Add a fallback for card back
    card_images["card_back"] = pygame.transform.scale(
        pygame.image.load(os.path.join(img_dir, "card_back.png")), (CARD_WIDTH, CARD_HEIGHT)
    )
    return card_images

def main():
    connect_to_server()
    threading.Thread(target=receive_updates, daemon=True).start()
    card_images = load_card_images()
    font = pygame.font.Font(None, 28)
    my_hand_rects = []

    running = True
    while running:
        screen.fill((0, 128, 0))
        clicked = False
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True

        with network_lock:
            if latest_game_state:
                # --- Render player's hand as images ---
                my_hand = latest_game_state.get("my_hand", [])
                if my_hand:
                    my_hand_rects = []
                    for i, card_str in enumerate(my_hand):
                        key = card_str_to_key(card_str)
                        img = card_images.get(key, card_images["card_back"])
                        x = 50 + i * (CARD_WIDTH + 10)
                        y = 400
                        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
                        my_hand_rects.append(rect)
                        screen.blit(img, (x, y))

                # --- Render deck as image ---
                deck_size = latest_game_state.get("deck_size", 0)
                deck_img = card_images["card_back"]
                screen.blit(deck_img, (50, 50))
                deck_text = font.render(f"{deck_size}", True, (255, 255, 255))
                screen.blit(deck_text, (50, 50 + CARD_HEIGHT + 5))

                # --- Render discard pile top as image ---
                discard = latest_game_state.get("discard_pile_top", None)
                if discard:
                    key = card_str_to_key(discard)
                    discard_img = card_images.get(key, card_images["card_back"])
                    screen.blit(discard_img, (150, 50))
                    discard_text = font.render("Discard", True, (255, 255, 255))
                    screen.blit(discard_text, (150, 50 + CARD_HEIGHT + 5))

                # --- Show turn indicator ---
                turn = latest_game_state.get("current_turn_player_id", None)
                turn_text = f"Turn: {turn}"
                turn_render = font.render(turn_text, True, (255, 255, 0))
                screen.blit(turn_render, (350, 20))

                # --- Handle card click for discard ---
                if clicked and my_hand_rects:
                    for i, rect in enumerate(my_hand_rects):
                        if rect.collidepoint(mouse_pos):
                            send_action({"action": "discard_card", "card": my_hand[i]})
                            break

        pygame.display.flip()
        clock.tick(60)

    client_socket.close()
    pygame.quit()

if __name__ == "__main__":
    main()
