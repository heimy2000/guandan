from flask import Flask, render_template, request, jsonify, Response
from collections import Counter
import random
import time
import json

app = Flask(__name__)

# 定义牌型
CARD_TYPES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', 'S', 'X']
CARD_VALUES = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14, 'S': 15, 'X': 16}
SUIT_VALUES = {'♠': 1, '♥': 2, '♣': 3, '♦': 4}

class Card:
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit

    def __str__(self):
        return f"{self.rank}{self.suit}"

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def __hash__(self):
        return hash((self.rank, self.suit))

    def __eq__(self, other):
        if isinstance(other, Card):
            return self.rank == other.rank and self.suit == other.suit
        return False

    def __lt__(self, other):
        if isinstance(other, Card):
            return (CARD_VALUES.get(self.rank, 0), SUIT_VALUES[self.suit]) < (CARD_VALUES.get(other.rank, 0), SUIT_VALUES[other.suit])
        return False

class Player:
    def __init__(self, name, position):
        self.name = name
        self.position = position
        self.hand = []
        self.reported = False

    def play_card(self, card):
        self.hand.remove(card)

    def report_cards(self):
        if len(self.hand) <= 10 and not self.reported:
            self.reported = True
            return len(self.hand)
        return None

class Game:
    def __init__(self):
        self.players = [Player(f"Player{i+1}", i) for i in range(4)]
        self.current_player = 0
        self.last_played_cards = []
        self.game_over = False
        self.game_log = []
        self.rank_card = None
        self.trump_suit = '♥'
        self.level = 2
        self.reset_game()

    def create_deck(self):
        suits = ['♠', '♥', '♣', '♦']
        deck = [Card(rank, suit) for suit in suits for rank in CARD_TYPES[:-2]]  # 去掉大小王
        deck.append(Card('S', ''))  # 添加小王
        deck.append(Card('X', ''))  # 添加大王
        deck *= 2  # 使用两副牌
        # 将两张红桃级牌设为任意牌
        for card in deck:
            if card.suit == '♥' and card.rank == self.rank_card:
                card.rank = 'R'  # 'R'表示任意牌
        random.shuffle(deck)
        return deck

    def deal_cards(self):
        self.deck = self.create_deck()
        for i in range(25):
            for player in self.players:
                player.hand.append(self.deck.pop())

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

    # 无条件地移动到下一个玩家
        self.current_player = (self.current_player + 1) % 4

    # 在所有玩家都pass之后重置last_played_cards的逻辑需要调整
    # 这个检查应该在所有玩家都有机会行动之后进行
        if all(not p.hand for p in self.players):  # 如果所有玩家手中都没有牌，游戏结束
            self.game_over = True
        elif all(p == player or not self.choose_cards(p) for p in self.players):  # 如果除了当前玩家外，其他玩家都无法出牌
            self.last_played_cards = []  # 重置last_played_cards
        # 注意：这里不需要再次设置self.current_player，因为已经设置了下一个玩家

    # 报牌逻辑保持不变
        for player in self.players:
            card_count = player.report_cards()
            if card_count is not None:
                self.game_log.append(f"{player.name} reports {card_count} cards.")

        time.sleep(1)  # 添加1秒延迟


    def choose_cards(self, player):
        if not self.last_played_cards:
            # 当前玩家是第一个出牌,尽可能多地出点数小的牌
            for card_type in ['single', 'pair', 'trio', 'trio_single', 'trio_pair', 'sequence', 'sequence_pair', 'bomb', 'rocket', 'straight_flush', 'four_kings']:
                cards = self.find_cards_by_type(player.hand, card_type)
                if cards:
                    return cards
            return []  # 如果找不到合适的牌,则选择pass
        else:
            # 当前玩家不是第一个出牌,尽可能出点数大的牌来压制对手
            last_card_type = self.get_card_type(self.last_played_cards)
            if last_card_type == 'rocket':
                return []  # 火箭不能被其他牌型压制,只能选择pass
            elif last_card_type in ['bomb', 'straight_flush', 'four_kings']:
                bigger_cards = self.find_bigger_cards(player.hand, self.last_played_cards)
                if bigger_cards:
                    return bigger_cards
                else:
                    return []  # 找不到更大的特殊牌型,只能选择pass
            else:
                same_type_cards = self.find_same_type_cards(player.hand, last_card_type)
                if same_type_cards:
                    if self.compare_cards(same_type_cards, self.last_played_cards) > 0:
                        return same_type_cards
                    else:
                        for card_type in ['bomb', 'rocket', 'straight_flush', 'four_kings']:
                            cards = self.find_cards_by_type(player.hand, card_type)
                            if cards:
                                return cards
                        return []  # 找不到更大的同种牌型或特殊牌型,只能选择pass
                else:
                    for card_type in ['bomb', 'rocket', 'straight_flush', 'four_kings']:
                        cards = self.find_cards_by_type(player.hand, card_type)
                        if cards:
                            return cards
                    return []  # 找不到同种牌型或特殊牌型,只能选择pass

    def compare_cards(self, cards1, cards2):
        type1 = self.get_card_type(cards1)
        type2 = self.get_card_type(cards2)
        if type1 == type2:
            return CARD_VALUES.get(cards1[-1].rank, 0) - CARD_VALUES.get(cards2[-1].rank, 0)
        else:
            return 0

    def find_bigger_cards(self, cards, last_played_cards):
        last_card_type = self.get_card_type(last_played_cards)
        if last_card_type == 'bomb':
            bombs = self.find_bombs(cards)
            if bombs:
                return min(bombs, key=lambda b: CARD_VALUES[b[0].rank])
        elif last_card_type == 'rocket':
            return []
        elif last_card_type == 'straight_flush':
            straight_flushes = self.find_straight_flushes(cards)
            if straight_flushes:
                bigger_straight_flushes = [sf for sf in straight_flushes if self.compare_cards(sf, last_played_cards) > 0]
                if bigger_straight_flushes:
                    return min(bigger_straight_flushes, key=lambda sf: CARD_VALUES[sf[0].rank])
        elif last_card_type == 'four_kings':
            return []
        return []

    def find_cards_by_type(self, cards, card_type):
        valid_cards = [c for c in cards if c.rank in CARD_VALUES and c.suit]
        if card_type == 'single':
            return [min(valid_cards, key=lambda c: CARD_VALUES[c.rank])]
        elif card_type == 'pair':
            pairs = [c for c in valid_cards if valid_cards.count(c) == 2]
            if pairs:
                return [min(pairs, key=lambda c: CARD_VALUES[c.rank])] * 2
        elif card_type == 'trio':
            trios = [c for c in valid_cards if valid_cards.count(c) == 3]
            if trios:
                return [min(trios, key=lambda c: CARD_VALUES[c.rank])] * 3
        elif card_type == 'bomb':
            bombs = self.find_bombs(valid_cards)
            if bombs:
                return min(bombs, key=lambda b: CARD_VALUES[b[0].rank])
        elif card_type == 'rocket':
            rockets = self.find_rockets(valid_cards)
            if rockets:
                return rockets[0]
        elif card_type == 'straight_flush':
            straight_flushes = self.find_straight_flushes(valid_cards)
            if straight_flushes:
                return min(straight_flushes, key=lambda sf: CARD_VALUES[sf[0].rank])
        elif card_type == 'four_kings':
            four_kings = self.find_four_kings(valid_cards)
            if four_kings:
                return four_kings
        elif card_type == 'trio_single':
            return self.find_trio_single(valid_cards)
        elif card_type == 'trio_pair':
            return self.find_trio_pair(valid_cards)
        elif card_type == 'sequence':
            return self.find_sequence(valid_cards)
        elif card_type == 'sequence_pair':
            return self.find_sequence_pair(valid_cards)
        return []

    def find_same_type_cards(self, cards, card_type):
        if card_type == 'single':
            return [max(cards, key=lambda c: CARD_VALUES.get(c.rank, 0))]
        elif card_type == 'pair':
            pairs = [c for c in cards if cards.count(c) >= 2]
            if pairs:
                pair = max(set(pairs), key=lambda c: CARD_VALUES.get(c.rank, 0))
                return [c for c in cards if c == pair][:2]
        elif card_type == 'trio':
            trios = [c for c in cards if cards.count(c) >= 3]
            if trios:
                trio = max(set(trios), key=lambda c: CARD_VALUES.get(c.rank, 0))
                return [c for c in cards if c == trio][:3]
        elif card_type == 'trio_single':
            trios = [c for c in cards if cards.count(c) >= 3]
            singles = [c for c in cards if c != trios[0]]
            if trios and singles:
                trio = max(set(trios), key=lambda c: CARD_VALUES.get(c.rank, 0))
                single = max(singles, key=lambda c: CARD_VALUES.get(c.rank, 0))
                return [c for c in cards if c == trio][:3] + [single]
        elif card_type == 'trio_pair':
            trios = [c for c in cards if cards.count(c) >= 3]
            pairs = [c for c in cards if cards.count(c) == 2 and c != trios[0]]
            if trios and pairs:
                trio = max(set(trios), key=lambda c: CARD_VALUES.get(c.rank, 0))
                pair = max(set(pairs), key=lambda c: CARD_VALUES.get(c.rank, 0))
                return [c for c in cards if c == trio][:3] + [c for c in cards if c == pair][:2]
        elif card_type == 'sequence':
            sequences = self.find_sequences(cards)
            if sequences:
                return max(sequences, key=lambda seq: CARD_VALUES.get(seq[-1].rank, 0))
        elif card_type == 'sequence_pair':
            sequence_pairs = self.find_sequence_pairs(cards)
            if sequence_pairs:
                return max(sequence_pairs, key=lambda seq: CARD_VALUES.get(seq[-1].rank, 0))
        return []

    def find_sequences(self, cards):
        sequences = []
        for start in range(len(CARD_TYPES) - 5):
            end = start + 5
            sequence = [c for c in cards if c.rank in CARD_TYPES[start:end]]
            if len(sequence) >= 5 and self.is_consecutive([CARD_VALUES.get(c.rank, 0) for c in sequence]):
                sequences.append(sequence)
        return sequences

    def find_sequence_pairs(self, cards):
        sequence_pairs = []
        pairs = [c for c in cards if cards.count(c) >= 2]
        for start in range(len(CARD_TYPES) - 3):
            end = start + 3
            sequence_pair = [p for p in pairs if p.rank in CARD_TYPES[start:end]]
            if len(sequence_pair) >= 6 and self.is_consecutive([CARD_VALUES.get(p.rank, 0) for p in sequence_pair]):
                sequence_pairs.append(sequence_pair)
        return sequence_pairs

    def find_bombs(self, cards):
        bombs = []
        for card in set(cards):
            if cards.count(card) == 4:
                bombs.append([c for c in cards if c == card])
            if cards.count(card) == 5:
                bombs.append([c for c in cards if c == card][:5])
            if cards.count(card) == 6:
                bombs.append([c for c in cards if c == card][:6])
        return bombs

    def find_straight_flushes(self, cards):
        straight_flushes = []
        for suit in ['♠', '♥', '♣', '♦']:
            suit_cards = [c for c in cards if c.suit == suit]
            sequences = self.find_sequences(suit_cards)
            straight_flushes.extend(sequences)
        return straight_flushes

    def find_four_kings(self, cards):
        kings = [c for c in cards if c.rank in ['J', 'Q', 'K', 'A']]
        if len(kings) == 4:
            return kings
        return []

    def find_rockets(self, cards):
        rockets = []
        small_joker = Card('S', '')
        big_joker = Card('X', '')
        if small_joker in cards and big_joker in cards:
            rockets.append([small_joker, big_joker])
        return rockets

    def find_trio_single(self, cards):
        trios = [c for c in cards if cards.count(c) >= 3]
        singles = [c for c in cards if c not in trios]
        if trios and singles:
            trio = min(trios, key=lambda c: CARD_VALUES[c.rank])
            single = min(singles, key=lambda c: CARD_VALUES[c.rank])
            return [trio] * 3 + [single]
        return []

    def find_trio_pair(self, cards):
        trios = [c for c in cards if cards.count(c) >= 3]
        pairs = [c for c in cards if cards.count(c) == 2 and c not in trios]
        if trios and pairs:
            trio = min(trios, key=lambda c: CARD_VALUES[c.rank])
            pair = min(pairs, key=lambda c: CARD_VALUES[c.rank])
            return [trio] * 3 + [pair] * 2
        return []

    def is_consecutive(self, values):
        return sorted(values) == list(range(min(values), max(values) + 1))

    def is_consecutive(self, values):
        return sorted(values) == list(range(min(values), max(values) + 1))

    def get_card_type(self, cards):
        if len(cards) == 1:
            return 'single'
        elif len(cards) == 2:
            if cards[0].rank == cards[1].rank:
                return 'pair'
            elif str(cards[0]) in ['S', 'X'] and str(cards[1]) in ['S', 'X']:
                return 'rocket'
        elif len(cards) == 3:
            if cards[0].rank == cards[1].rank == cards[2].rank:
                return 'trio'
        elif len(cards) == 4:
            if cards[0].rank == cards[1].rank == cards[2].rank == cards[3].rank:
                return 'bomb'
        elif len(cards) == 5:
            values = [CARD_VALUES.get(c.rank, 0) for c in cards]
            if self.is_consecutive(values):
                if len(set(c.suit for c in cards)) == 1:
                    return 'straight_flush'
                else:
                    return 'sequence'
            else:
                counts = Counter(cards)
                if 3 in counts.values() and 2 in counts.values():
                    return 'trio_pair'
                elif 4 in counts.values() and 1 in counts.values():
                    return 'bomb'
        elif len(cards) == 6:
            counts = Counter(cards)
            if len(counts) == 3 and all(count == 2 for count in counts.values()):
                values = [CARD_VALUES.get(c.rank, 0) for c in cards]
                if self.is_consecutive(values):
                    return 'sequence_pair'
            elif 4 in counts.values() and 2 in counts.values():
                return 'bomb'
        elif len(cards) >= 5:
            values = [CARD_VALUES.get(c.rank, 0) for c in cards]
            if self.is_consecutive(values):
                if len(set(c.suit for c in cards)) == 1:
                    return 'straight_flush'
                else:
                    return 'sequence'
        return None

    def get_game_state(self):
        game_state = {
            'players': [{'name': player.name, 'hand': [str(card) for card in player.hand]} for player in self.players],
            'current_player': self.current_player,
            'last_played_cards': [str(card) for card in self.last_played_cards],
            'game_over': self.game_over,
            'game_log': self.game_log,
            'rank_card': self.rank_card,
            'trump_suit': self.trump_suit,
            'level': self.level
        }
        return game_state

    def reset_game(self):
        self.set_rank_card()
        self.deal_cards()
        self.current_player = 0
        self.last_played_cards = []
        self.game_over = False
        self.game_log = []
        self.level = 2

    def set_rank_card(self):
        rank = random.choice(CARD_TYPES[:-2])  # 随机选择一个级牌,不包括大小王
        self.rank_card = rank
        self.game_log.append(f"本局级牌为: {rank}")

    def upgrade_level(self, pair1, pair2):
        # 实现升级逻辑
        if pair1.rank == pair2.rank:
            if pair1.rank == self.rank_card:
                self.level = 3
            else:
                self.level = 2
        else:
            self.level = 1

    def pay_tribute(self, player):
        # 实现进贡逻辑
        if self.level == 3:
            for card in player.hand:
                if card.rank == 'R':
                    player.play_card(card)
                    self.game_log.append(f"{player.name} pays tribute with {card}.")
                    break

    def return_tribute(self, player):
        # 实现还贡逻辑
        if self.level == 3:
            for card in self.deck:
                if card.rank == 'R':
                    player.hand.append(card)
                    self.deck.remove(card)
                    self.game_log.append(f"{player.name} gets the tribute card back.")
                    break

    def report_cards(self):
        # 实现报牌逻辑
        for player in self.players:
            card_count = player.report_cards()
            if card_count is not None:
                self.game_log.append(f"{player.name} reports {card_count} cards.")

game = Game()

@app.route('/')
def index():
    game.reset_game()
    return render_template('index.html', game_state=game.get_game_state())

@app.route('/play')
def play():
    def generate():
        game_state = game.get_game_state()
        while not game_state['game_over']:
            game.play_turn()
            game_state = game.get_game_state()
            yield f"data: {json.dumps(game_state)}\n\n"
        yield f"data: {json.dumps(game_state)}\n\n"
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)  # 设置Flask应用的端口为5000
