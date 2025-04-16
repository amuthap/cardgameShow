import random

class Card:
    SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
    RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]

    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return f"{self.rank} of {self.suit}"

class Deck:
    def __init__(self):
        self.cards = [Card(suit, rank) for suit in Card.SUITS for rank in Card.RANKS]
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def deal_card(self):
        return self.cards.pop() if self.cards else None

class Player:
    def __init__(self, name, player_id):
        self.name = name
        self.id = player_id
        self.hand = []

    def add_card(self, card):
        self.hand.append(card)

class Game:
    def __init__(self):
        self.players = {}
        self.deck = Deck()
        self.discard_pile = []
        self.current_turn_player_id = None
        self.game_started = False
        self.min_players = 2

    def add_player(self, player_id, name="Player"):
        if not self.game_started and player_id not in self.players:
            player = Player(name, player_id)
            self.players[player_id] = player
            return player
        return None

    def start_game(self):
        if len(self.players) >= self.min_players:
            self.deck.shuffle()
            for _ in range(5):
                for player in self.players.values():
                    player.add_card(self.deck.deal_card())
            self.current_turn_player_id = list(self.players.keys())[0]
            self.game_started = True

    def get_game_state(self, player_id):
        player = self.players.get(player_id)
        if not player:
            return None
        return {
            "my_hand": [str(card) for card in player.hand],
            "current_turn_player_id": self.current_turn_player_id,
            "deck_size": len(self.deck.cards),
            "discard_pile_top": str(self.discard_pile[-1]) if self.discard_pile else None,
        }

    def handle_action(self, player_id, action_data):
        if self.current_turn_player_id != player_id:
            return False
        action = action_data.get("action")
        if action == "draw_card":
            card = self.deck.deal_card()
            if card:
                self.players[player_id].add_card(card)
            return True
        elif action == "discard_card":
            card_str = action_data.get("card")
            player = self.players[player_id]
            for card in player.hand:
                if str(card) == card_str:
                    player.hand.remove(card)
                    self.discard_pile.append(card)
                    self.current_turn_player_id = list(self.players.keys())[
                        (list(self.players.keys()).index(player_id) + 1) % len(self.players)
                    ]
                    return True
        return False
