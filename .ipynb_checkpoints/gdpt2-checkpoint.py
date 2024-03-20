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
        if not self.last_played_cards:
            if not player.hand:
                return []  # 如果玩家没有手牌,则跳过
            
            # 如果是第一个出牌,则优先出级牌、任意牌、大小王等大牌
            high_cards = [c for c in player.hand if c.rank in [self.rank_card, 'R', 'S', 'X']]
            if high_cards:
                return [random.choice(high_cards)]
            else:
                return [max(player.hand, key=lambda c: CARD_VALUES[c.rank])]  # 如果没有大牌,则出最大的牌

        last_card_type = self.get_card_type(self.last_played_cards)
        playable_cards = [c for c in player.hand if self.is_valid_move(c)]

        if not playable_cards:
            return []  # 如果没有可出的牌,则跳过

        if last_card_type == 'rocket':
            return []  # 如果上一个玩家出了火箭,则跳过

        if last_card_type == 'bomb':
            bomb_cards = [c for c in playable_cards if self.get_card_type([c]) == 'bomb']
            if bomb_cards:
                # 如果有多个炸弹,则出数值最大的炸弹
                return [max(bomb_cards, key=lambda c: CARD_VALUES[c.rank])]
            else:
                return []  # 如果没有炸弹,则跳过

        if last_card_type == 'trio':
            trio_cards = [c for c in playable_cards if self.get_card_type([c]) == 'trio']
            if trio_cards:
                # 如果有多个三张,则出数值最大的三张
                return [max(trio_cards, key=lambda c: CARD_VALUES[c.rank])]
            else:
                return []  # 如果没有三张,则跳过

        if last_card_type == 'pair':
            pair_cards = [c for c in playable_cards if self.get_card_type([c]) == 'pair']
            if pair_cards:
                # 如果有多个对子,则出数值最大的对子
                return [max(pair_cards, key=lambda c: CARD_VALUES[c.rank])]
            else:
                return []  # 如果没有对子,则跳过

        if last_card_type == 'single':
            single_cards = [c for c in playable_cards if self.get_card_type([c]) == 'single']
            if single_cards:
                # 如果有单张,则出数值最大的单张
                return [max(single_cards, key=lambda c: CARD_VALUES[c.rank])]
            else:
                return []  # 如果没有单张,则跳过

        # 如果上一个玩家出的是其他牌型,则尝试出相同牌型的牌
        same_type_cards = [c for c in playable_cards if self.get_card_type([c]) == last_card_type]
        if same_type_cards:
            # 如果有相同牌型的牌,则出数值最大的
            return [max(same_type_cards, key=lambda c: CARD_VALUES[c.rank])]
        else:
            return []  # 如果没有相同牌型的牌,则跳过

    def is_valid_move(self, card):
        if not self.last_played_cards:
            return True

        last_card_type = self.get_card_type(self.last_played_cards)
        card_type = self.get_card_type([card])

        if not card_type:
            return False

        # 判断牌型大小
        type_order = ['rocket', 'bomb', 'single', 'pair', 'trio', 'trio_pair', 'airplane', 'straight', 'straight_flush']
        
        if card_type not in type_order or last_card_type not in type_order:
            return False

        if type_order.index(card_type) < type_order.index(last_card_type):
            return True
        elif type_order.index(card_type) > type_order.index(last_card_type):
            return False
        else:
            # 牌型一致,比较数字大小
            return CARD_VALUES[card.rank] > CARD_VALUES[self.last_played_cards[0].rank]

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
            elif len(counter) == 2 and set(counter.values()) == {3}:
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
