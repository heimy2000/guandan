from flask import Flask, render_template, request, jsonify, Response
from collections import Counter
import random
import time
import json

app = Flask(__name__)

# 定义牌型
CARD_TYPES = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2', 'S', 'X']
CARD_VALUES = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14, '2': 15, 'S': 16, 'X': 17}

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def __str__(self):
        return f"{self.suit}{self.rank}"

class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []

    def play_card(self, card):
        self.hand.remove(card)

class Game:
    def __init__(self):
        self.deck = self.create_deck()
        self.players = [Player(f"Robot{i+1}") for i in range(4)]
        self.current_player = 0
        self.last_played_cards = []
        self.game_over = False
        self.game_log = []

    def create_deck(self):
        suits = ['♠', '♥', '♣', '♦']
        deck = [Card(suit, rank) for suit in suits for rank in CARD_TYPES[:-2]]  # 去掉大小王
        deck.append(Card('', 'S'))  # 添加小王
        deck.append(Card('', 'X'))  # 添加大王
        random.shuffle(deck)
        return deck

    def deal_cards(self):
        for player in self.players:
            player.hand = self.deck[:13]
            self.deck = self.deck[13:]

    def play_turn(self):
        player = self.players[self.current_player]
        played_cards = self.choose_cards(player)

        if not played_cards:
            self.game_log.append(f"{player.name} passes.")
        else:
            for card in played_cards:
                player.play_card(card)

            self.game_log.append(f"{player.name} plays {' '.join(str(card) for card in played_cards)}.")

            if not player.hand:
                self.game_over = True
                self.game_log.append(f"{player.name} wins!")

            self.last_played_cards = played_cards

        self.current_player = (self.current_player + 1) % 4

        if not played_cards:
            if all(not p.hand or not self.choose_cards(p) for p in self.players):
                self.last_played_cards = []  # 如果所有玩家都没有可出的牌,重置last_played_cards
        else:
            while not self.players[self.current_player].hand or not self.choose_cards(self.players[self.current_player]):
                self.current_player = (self.current_player + 1) % 4

        time.sleep(1)  # 添加1秒延迟

    def choose_cards(self, player):
        if not self.last_played_cards:
            if not player.hand:
                return []  # 如果玩家没有手牌,则跳过
            return [min(player.hand, key=lambda c: CARD_VALUES[c.rank])]  # 如果是第一个出牌,出最小的牌

        last_card_type = self.get_card_type(self.last_played_cards)
        playable_cards = [c for c in player.hand if self.is_valid_move([c])]

        if not playable_cards:
            if last_card_type == 'rocket' or last_card_type == 'bomb':
                return []  # 如果上一个玩家出了火箭或炸弹,且没有可出的牌,则跳过
            else:
                return []  # 如果没有可出的牌,则跳过

        if last_card_type == 'bomb':
            bomb_cards = [c for c in playable_cards if self.get_card_type([c]) == 'bomb']
            if bomb_cards:
                return bomb_cards[:len(self.last_played_cards)]  # 如果有炸弹,则出炸弹

        return playable_cards[:len(self.last_played_cards)]  # 否则出相同数量的牌

    def is_valid_move(self, played_cards):
        if not played_cards:
            return True

        card_type = self.get_card_type(played_cards)
        if not card_type:
            return False

        if not self.last_played_cards:
            return True

        last_card_type = self.get_card_type(self.last_played_cards)
        if last_card_type == 'bomb' and card_type != 'bomb':
            return False

        if last_card_type == 'rocket' and card_type != 'rocket':
            return False

        if card_type != last_card_type:
            return False

        if card_type == 'bomb':
            if len(played_cards) < len(self.last_played_cards):
                return False
            elif len(played_cards) == len(self.last_played_cards):
                return CARD_VALUES[played_cards[0].rank] > CARD_VALUES[self.last_played_cards[0].rank]
        else:
            return CARD_VALUES[played_cards[0].rank] > CARD_VALUES[self.last_played_cards[0].rank]

    def get_card_type(self, cards):
        if len(cards) == 1:
            return 'single'
        elif len(cards) == 2:
            if cards[0].rank == cards[1].rank:
                return 'pair'
            elif set(str(c) for c in cards) == {'♠S', '♥S'} or set(str(c) for c in cards) == {'♣X', '♦X'}:
                return 'rocket'
            else:
                return None
        elif len(cards) == 3:
            if cards[0].rank == cards[1].rank == cards[2].rank:
                return 'trio'
            else:
                return None
        elif len(cards) == 4:
            if cards[0].rank == cards[1].rank == cards[2].rank == cards[3].rank:
                return 'bomb'
            else:
                return None
        elif len(cards) == 5:
            values = sorted([CARD_VALUES[c.rank] for c in cards])
            if values == list(range(values[0], values[0] + 5)) and len(set(c.suit for c in cards)) == 1:
                return 'straight_flush'
            elif values == list(range(values[0], values[0] + 5)):
                return 'straight'
            else:
                return None
        elif len(cards) == 6:
            values = [CARD_VALUES[c.rank] for c in cards]
            counter = Counter(values)
            if len(counter) == 3 and set(counter.values()) == {2}:
                return 'trio_pair'
            elif len(counter) == 3 and set(counter.values()) == {3}:
                return 'airplane'
            else:
                return None
        else:
            return None

    def get_game_state(self):
        game_state = {
            'players': [{'name': player.name, 'hand': [str(card) for card in player.hand]} for player in self.players],
            'current_player': self.current_player,
            'last_played_cards': [str(card) for card in self.last_played_cards],
            'game_over': self.game_over,
            'game_log': self.game_log
        }
        return game_state

    def reset_game(self):
        self.deck = self.create_deck()
        for player in self.players:
            player.hand = []
        self.current_player = 0
        self.last_played_cards = []
        self.game_over = False
        self.game_log = []
        self.deal_cards()

game = Game()

@app.route('/')
def index():
    game.reset_game()
    return render_template('index.html', game_state=game.get_game_state())

@app.route('/play')
def play():
    def generate():
        game_state = game.get_game_state()
        while not game.game_over:
            game.play_turn()
            game_state = game.get_game_state()
            yield f"data: {json.dumps(game_state)}\n\n"
        yield "data: GAME_OVER\n\n"
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(port=8451)
