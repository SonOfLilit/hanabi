import random
from itertools import cycle
from collections import namedtuple
import random

class KnownCard(namedtuple('KnownCard', 'suit rank')):
    def __repr__(self):
        return f':{self.suit}{self.rank}'

class Card(namedtuple('Card', 'id known')):
    def __repr__(self):
        return f'#{self.id}{self.known or ""}'
    def hidden(self):
        if self.known is not None:
            return self._replace(known=None)
        return self


class Tokens(namedtuple('Tokens', 'clues lives')):
    pass


class Rules(namedtuple('Rules', 'max_tokens suits ranks cards_per_player')):
    pass

IDENTIFIER_TO_MOVE = {}


def Move(name, identifier, items):
    class MyMove(namedtuple(name, items)):
        @classmethod
        def create(cls, *args, **kwargs):
            return cls(cls.identifier, *args, **kwargs)
    MyMove.identifier = identifier
    MyMove.__name__ = name
    if 'Resolved' not in name:
        IDENTIFIER_TO_MOVE[identifier] = MyMove
    return MyMove
ResolvedClue = Move('ResolvedClue', 'c', 'move player type param cards')
ResolvedPlay = Move('ResolvedPlay', 'p', 'move card new_card is_success')
ResolvedDiscard = Move('ResolvedDiscard', 'd', 'move card new_card')
Draw = Move('Draw', 'n', 'move card')
Clue = Move('Clue', 'c', 'move player type param')
Play = Move('Play', 'p', 'move card_id')
Discard = Move('Discard', 'd', 'move card_id')


def tuple_to_move(tup):
    return IDENTIFIER_TO_MOVE[tup[0]]._make(tup)


class Hanabi:
    def __init__(self, players, rules=Rules(max_tokens=Tokens(8, 4), suits=5, ranks=[3,2,2,2,1], cards_per_player=None), deck=None):
        if rules.cards_per_player is None:
            rules = rules._replace(cards_per_player=5 if len(players) <= 3 else 4)
        self.players = players
        self.rules = rules
        self.deck = deck

        self.current_player = None

        if deck is None:
            self.deck = self.new_shuffled_deck()
        self.hands = [[] for _ in players]
        self.tokens = self.rules.max_tokens
        self.log = []
        self.player_states = [None] * len(players)

        self.final_player = None
        self.slots = [0] * self.rules.suits
        self.discard_pile = [[0] * len(self.rules.ranks) for _ in range(self.rules.suits)]

    def run(self):
        assert not self.log
        self.deal_cards()
        while True:
            for i in self.iterate_players():
                hands = list(self.hands)
                hands[i] = [card.hidden() for card in hands[i]]
                player = self.players[self.current_player]
                self.player_states[i], move = player(self.player_states[i], self.log, hands, self.rules, self.tokens, self.slots, self.discard_pile)
                self.resolve(tuple_to_move(move))
                if self.is_game_over():
                    return sum(self.slots)

    def new_shuffled_deck(self):
        cards = []
        for suit in range(self.rules.suits):
            for rank, count in enumerate(self.rules.ranks):
                for item in range(count):
                    cards.append(KnownCard(suit, rank))
        random.shuffle(cards)
        return list(reversed([Card(card_id, card) for card_id, card in enumerate(cards)]))

    def deal_cards(self):
        for player in self.iterate_players():
            for _ in range(self.rules.cards_per_player):
                card = self.take_hidden_card_from_deck()
                assert card is not None
                self.log.append(Draw.create(card))

    def iterate_players(self):
        for i in range(len(self.players)):
            self.current_player = i
            yield i

    def take_hidden_card_from_deck(self):
        if not self.deck:
            return None
        card = self.deck.pop()
        if not self.deck:
            self.final_player = self.current_player
        self.hands[self.current_player].append(card)
        return card.hidden()

    def is_game_over(self):
        return (self.lives == 0 or self.final_player == self.current_player or
            all(slot == len(self.rules.ranks) for slot in self.slots))

    def resolve(self, move):
        if isinstance(move, Clue):
            assert self.clues > 0
            self.clues -= 1
            assert move.player != self.current_player
            cards = [card.hidden() for card in self.hands[move.player] if getattr(card.known, move.type) == move.param]
            assert cards
            self.log.append(ResolvedClue.create(move.player, move.type, move.param, cards))
        elif isinstance(move, Play):
            card = self.take_card_from_current_hand(move.card_id)
            is_success = self.slots[card.known.suit] == card.known.rank
            if is_success:
                self.slots[card.known.suit] += 1
                if self.slots[card.known.suit] == len(self.rules.ranks):
                    if self.clues < self.rules.max_tokens.clues:
                        self.clues += 1
            else:
                self.discard_pile[card.known.suit][card.known.rank] += 1
                self.lives -= 1
                assert self.lives >= 0
            drawn = self.take_hidden_card_from_deck()
            self.log.append(ResolvedPlay.create(card, drawn, is_success))
        elif isinstance(move, Discard):
            card = self.take_card_from_current_hand(move.card_id)
            self.discard_pile[card.known.suit][card.known.rank] += 1
            self.clues += 1
            drawn = self.take_hidden_card_from_deck()
            self.log.append(ResolvedDiscard.create(card, drawn))
        else:
            assert False, 'no such move'

    @property
    def clues(self):
        return self.tokens.clues
    @clues.setter
    def clues(self, value):
        self.tokens = self.tokens._replace(clues=value)

    @property
    def lives(self):
        return self.tokens.lives
    @lives.setter
    def lives(self, value):
        self.tokens = self.tokens._replace(lives=value)

    def take_card_from_current_hand(self, card_id):
        for i, card in enumerate(self.hands[self.current_player]):
            if card.id == card_id:
                break
        else:
            assert False, f'no such card in hand: {card_id}'
        del self.hands[self.current_player][i]
        return card

    def print(self):
        for attr in ['log', 'tokens', 'slots', 'discard_pile']:
            print(f'{attr}:')
            pprint(getattr(self, attr))

if __name__ == '__main__':
    from players.base import random_player
    from pprint import pprint
    score = []
    for i in range(100):
        h = Hanabi([random_player, random_player, random_player])
        score.append(h.run())

    import pandas as pd
    d = pd.Series(score)
    print(d.describe())
    print(d.value_counts())
