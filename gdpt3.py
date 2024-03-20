from flask import Flask, render_template, request, jsonify, Response
from collections import Counter
import random
import time
import json

app = Flask(__name__)

# 定义牌型
CARD_TYPES = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2', 'S', 'X']
CARD_VALUES = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14, '2': 15, 'R': 16, 'S': 17, 'X': 18}

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
        self.players = [Player(f"Robot{i+1}") for i in range(4)]
        self.current_player = 0
        self.last_played_cards = []
        self.game_over = False
        self.game_log = []
        self.rank_card = None
        self.reset_game()

    def create_deck(self):
        suits = ['♠', '♥', '♣', '♦']
        deck = [Card(suit, rank) for suit in suits for rank in CARD_TYPES[:-2]]  # 去掉大小王
        deck.append(Card('', 'S'))  # 添加小王
        deck.append(Card('', 'X'))  # 添加大王
        
        # 将两张红桃级牌设为任意牌
        for card in deck:
            if card.suit == '♥' and card.rank == self.rank_card:
                card.rank = 'R'  # 'R'表示任意牌
        
        random.shuffle(deck)
        return deck

    def deal_cards(self):
        self.deck = self.create_deck()
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

        # 判断是否所有其他玩家都pass
        if all(not self.choose_cards(p) for p in self.players if p != player):
            self.last_played_cards = []  # 重置last_played_cards
            self.current_player = self.players.index(player)  # 从最后一个出牌的玩家开始新的回合
        else:
            self.current_player = (self.current_player + 1) % 4

        time.sleep(1)  # 添加1秒延迟

    def choose_cards(self, player):
        # 检查是否可以直接赢得游戏
        if not self.last_played_cards:
            # 如果玩家手中的牌数量等于剩余牌的数量,则直接出所有牌
            if len(player.hand) == len(set(player.hand)):
                return player.hand
            
            # 如果是第一个出牌,则优先出火箭、炸弹、级牌、任意牌等大牌
            rocket_cards = [c for c in player.hand if str(c) in ['S', 'X']]
            if len(rocket_cards) == 2:
                return rocket_cards

            bomb_cards = self.find_bomb(player.hand)
            if bomb_cards:
                return bomb_cards

            high_cards = [c for c in player.hand if c.rank in [self.rank_card, 'R']]
            if high_cards:
                return [max(high_cards, key=lambda c: CARD_VALUES[c.rank])]
            else:
                return [max(player.hand, key=lambda c: CARD_VALUES[c.rank])]  # 如果没有大牌,则出最大的牌

        last_card_type = self.get_card_type(self.last_played_cards)
        playable_cards = [c for c in player.hand if self.is_valid_move(self.last_played_cards + [c])]

        if not playable_cards:
            return []  # 如果没有可出的牌,则跳过

        if last_card_type == 'rocket':
            return []  # 如果上一个玩家出了火箭,则跳过

        if last_card_type == 'bomb':
            bomb_cards = self.find_bomb(playable_cards)
            if bomb_cards:
                return bomb_cards
            else:
                return []  # 如果没有炸弹,则跳过

        # 尝试出同类型的牌
        same_type_cards = self.find_same_type_cards(playable_cards, last_card_type)
        if same_type_cards:
            return same_type_cards

        # 如果没有同类型的牌,则尝试出炸弹
        bomb_cards = self.find_bomb(playable_cards)
        if bomb_cards:
            return bomb_cards

        # 如果没有炸弹,则尝试出任意牌
        if 'R' in [c.rank for c in playable_cards]:
            return [c for c in playable_cards if c.rank == 'R']

        # 如果没有任意牌,则出单张最大的牌
        return [max(playable_cards, key=lambda c: CARD_VALUES[c.rank])]

    def find_bomb(self, cards):
        bomb_cards = []
        for card in set(cards):
            if cards.count(card) == 4:
                bomb_cards = [c for c in cards if c == card]
                break
        return bomb_cards

    def find_same_type_cards(self, cards, card_type):
        same_type_cards = []
        if card_type == 'single':
            same_type_cards = cards
        elif card_type == 'pair':
            for card in set(cards):
                if cards.count(card) >= 2:
                    same_type_cards = [c for c in cards if c == card][:2]
                    break
        elif card_type == 'trio':
            for card in set(cards):
                if cards.count(card) >= 3:
                    same_type_cards = [c for c in cards if c == card][:3]
                    break
        elif card_type == 'trio_single':
            trio_cards = []
            single_cards = []
            for card in set(cards):
                if cards.count(card) >= 3:
                    trio_cards = [c for c in cards if c == card][:3]
                    break
            if trio_cards:
                single_cards = [c for c in cards if c not in trio_cards]
                if single_cards:
                    same_type_cards = trio_cards + [single_cards[0]]
        elif card_type == 'trio_pair':
            trio_cards = []
            pair_cards = []
            for card in set(cards):
                if cards.count(card) >= 3:
                    trio_cards = [c for c in cards if c == card][:3]
                    break
            if trio_cards:
                for card in set(cards):
                    if cards.count(card) >= 2 and card != trio_cards[0]:
                        pair_cards = [c for c in cards if c == card][:2]
                        break
                if pair_cards:
                    same_type_cards = trio_cards + pair_cards
        elif card_type == 'sequence':
            sequences = self.find_sequences(cards)
            if sequences:
                same_type_cards = max(sequences, key=lambda s: CARD_VALUES[s[-1].rank])
        elif card_type == 'sequence_pair':
            sequence_pairs = self.find_sequence_pairs(cards)
            if sequence_pairs:
                same_type_cards = max(sequence_pairs, key=lambda s: CARD_VALUES[s[-1].rank])
        elif card_type == 'airplane':
            airplane_cards = self.find_airplane(cards)
            if airplane_cards:
                same_type_cards = airplane_cards
        return same_type_cards

    def find_sequences(self, cards):
        sequences = []
        for start in range(len(CARD_TYPES) - 5):
            end = start + 5
            sequence = [c for c in cards if c.rank in CARD_TYPES[start:end]]
            if len(sequence) >= 5 and self.is_consecutive([CARD_VALUES[c.rank] for c in sequence]):
                sequences.append(sequence)
        return sequences

    def find_sequence_pairs(self, cards):
        sequence_pairs = []
        pairs = []
        for card in set(cards):
            if cards.count(card) >= 2:
                pairs.append([c for c in cards if c == card][:2])
        for start in range(len(CARD_TYPES) - 3):
            end = start + 3
            sequence_pair = [p for p in pairs if p[0].rank in CARD_TYPES[start:end]]
            if len(sequence_pair) >= 3 and self.is_consecutive([CARD_VALUES[p[0].rank] for p in sequence_pair]):
                sequence_pairs.append([c for p in sequence_pair for c in p])
        return sequence_pairs

    def find_airplane(self, cards):
        airplane_cards = []
        trios = []
        for card in set(cards):
            if cards.count(card) >= 3:
                trios.append([c for c in cards if c == card][:3])
        for start in range(len(CARD_TYPES) - 2):
            end = start + 2
            airplane = [t for t in trios if t[0].rank in CARD_TYPES[start:end]]
            if len(airplane) >= 2 and self.is_consecutive([CARD_VALUES[t[0].rank] for t in airplane]):
                airplane_cards = [c for t in airplane for c in t]
                break
        return airplane_cards

    def is_consecutive(self, values):
        return sorted(values) == list(range(min(values), max(values) + 1))

    def is_valid_move(self, cards):
        if not self.last_played_cards:
            return True

        last_card_type = self.get_card_type(self.last_played_cards)
        card_type = self.get_card_type(cards)

        if not card_type:
            return False

        if last_card_type == 'rocket':
            return False

        if card_type == 'rocket':
            return True

        if last_card_type == 'bomb':
            if card_type != 'bomb':
                return False
            else:
                return CARD_VALUES[cards[-1].rank] > CARD_VALUES[self.last_played_cards[-1].rank]

        if card_type == 'bomb':
            return True

        if card_type != last_card_type:
            return False

        if len(cards) != len(self.last_played_cards):
            return False

        return CARD_VALUES[cards[-1].rank] > CARD_VALUES[self.last_played_cards[-1].rank]

    def get_card_type(self, cards):
        if len(cards) == 1:
            return 'single'
        elif len(cards) == 2:
            if cards[0].rank == cards[1].rank:
                return 'pair'
            elif set(str(c) for c in cards) == {'S', 'X'}:
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
            if self.is_consecutive([CARD_VALUES[c.rank] for c in cards]):
                return 'sequence'
            else:
                counter = Counter([c.rank for c in cards])
                if len(counter) == 2 and set(counter.values()) == {3, 2}:
                    return 'trio_pair'
                else:
                    return None
        elif len(cards) == 6:
            if self.is_consecutive([CARD_VALUES[c.rank] for c in cards]) and len(set(c.rank for c in cards)) == 3:
                return 'sequence_pair'
            else:
                counter = Counter([c.rank for c in cards])
                if len(counter) == 2 and set(counter.values()) == {4, 2}:
                    return 'four_pair'
                elif len(counter) == 3 and set(counter.values()) == {3, 2, 1}:
                    return 'trio_single'
                else:
                    return None
        elif len(cards) in [8, 10, 12]:
            if self.is_consecutive([CARD_VALUES[c.rank] for c in cards]) and len(set(c.rank for c in cards)) == len(cards) // 2:
                return 'sequence_pair'
            elif self.is_airplane(cards):
                return 'airplane'
            else:
                return None
        else:
            if self.is_consecutive([CARD_VALUES[c.rank] for c in cards]):
                return 'sequence'
            else:
                return None

    def get_game_state(self):
        game_state = {
            'players': [{'name': player.name, 'hand': [str(card) for card in player.hand]} for player in self.players],
            'current_player': self.current_player,
            'last_played_cards': [str(card) for card in self.last_played_cards],
            'game_over': self.game_over,
            'game_log': self.game_log,
            'rank_card': self.rank_card
        }
        return game_state

    def reset_game(self):
        self.set_rank_card()
        self.deal_cards()
        self.current_player = 0
        self.last_played_cards = []
        self.game_over = False
        self.game_log = []

    def set_rank_card(self):
        rank = random.choice(CARD_TYPES[:-2])  # 随机选择一个级牌,不包括大小王
        self.rank_card = rank
        self.game_log.append(f"本局级牌为: {rank}")

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

