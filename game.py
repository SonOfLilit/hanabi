import random
from pprint import pprint
from collections import namedtuple
from enum import Enum
from typing import List, NamedTuple, Tuple

import colorama
colorama.init()
suits_col = [colorama.Fore.RED, colorama.Fore.GREEN, colorama.Fore.YELLOW,
             colorama.Fore.BLUE, colorama.Fore.MAGENTA, colorama.Fore.CYAN, ]

class EndMode(Enum):
    official = 1
    endless = 2
    fair = 3

class IllegalMove(Exception):
    pass

class KnownCard(namedtuple('KnownCard', 'suit rank')):
    def __repr__(self):
        return f':{suits_col[self.suit]}{chr(ord("A")+self.suit)}{self.rank}'

class Card(namedtuple('Card', 'id data')):
    def __repr__(self):
        return f'#{self.id:02}{self.data or ""}'
    def hidden(self):
        if self.data is not None:
            return self._replace(data=None)
        return self

class Tokens(namedtuple('Tokens', 'clues lives')):
    pass

class Rules(namedtuple('Rules', 'max_tokens suits ranks cards_per_player')):
    pass


IDENTIFIER_TO_MOVE = {}
def move_tuple(name: str, identifier: str, items: (str, List[str])) -> NamedTuple:
    class Move(namedtuple(name, items)):
        @classmethod
        def create(cls, *args, **kwargs):
            ret = cls(cls.identifier, *args, **kwargs)
            return ret
    Move.identifier = identifier
    Move.__name__ = name
    if 'Resolved' not in name:
        IDENTIFIER_TO_MOVE[identifier] = Move
    return Move
ResolvedClue = move_tuple('ResolvedClue___', 'c', 'move cur_player player type param cards')
ResolvedPlay = move_tuple('ResolvedPlay___', 'p', 'move cur_player card new_card is_success')
ResolvedDiscard = move_tuple('ResolvedDiscard', 'd', 'move cur_player card new_card')
ResolvedDraw = move_tuple('ResolvedDraw___', 'n', 'move cur_player card')
Clue = move_tuple('Clue', 'c', 'move player type param')
Play = move_tuple('Play', 'p', 'move card_id')
Discard = move_tuple('Discard', 'd', 'move card_id')

def tuple_to_move(tup: Tuple) -> NamedTuple:
    return IDENTIFIER_TO_MOVE[tup[0]]._make(tup)


DEFAULT_RULES = Rules(max_tokens=Tokens(8, 4), cards_per_player=None, suits=5, ranks=[3, 2, 2, 2, 1])

class Hanabi:
    def __init__(self, players, rules=DEFAULT_RULES, deck=None, allow_cheats=False, end_mode=EndMode.official):
        if rules.cards_per_player is None:
            rules = rules._replace(cards_per_player=5 if len(players) <= 3 else 4)
        self.players = players
        self.rules = rules
        self.deck = deck
        self.allow_cheats = allow_cheats
        if not isinstance(end_mode, EndMode):
            end_mode = EndMode[end_mode]
        self.end_mode = end_mode

        self.current_player = None

        if deck is None:
            self.deck = self.new_shuffled_deck(self.rules.suits, self.rules.ranks)
        self.hands = [[] for _ in players]
        self.tokens = self.rules.max_tokens
        self.log = []
        self.player_states = [None] * len(players)

        self.final_player = None
        self.slots = [0] * self.rules.suits
        self.discard_pile = [[0] * len(self.rules.ranks) for _ in range(self.rules.suits)]

    def run(self) -> int:
        if self.log:
            raise RuntimeError("run already done")
        self.deal_cards()
        while True:
            for i in self.iterate_players():
                if isinstance(self.final_player, tuple):
                    self.final_player = self.final_player[1]
                hands = list(self.hands)
                if not self.allow_cheats:
                    hands[i] = [card.hidden() for card in hands[i]]
                player = self.players[self.current_player]
                self.player_states[i], move = player(self.player_states[i], self.log, hands, self.rules, self.tokens, self.slots, self.discard_pile)
                self.resolve(tuple_to_move(move))
                if self.is_game_over():
                    return self.score

    @classmethod
    def new_shuffled_deck(cls, suits: int, ranks: List[int]) -> List[Card]:
        cards = []
        for suit in range(suits):
            for rank, count in enumerate(ranks):
                cards += [KnownCard(suit, rank)] * count
        random.shuffle(cards)
        return list(reversed([Card(card_id, card) for card_id, card in enumerate(cards)]))

    def deal_cards(self) -> None:
        for player in self.iterate_players():
            for _i in range(self.rules.cards_per_player):
                card = self.take_hidden_card_from_deck()
                if card is None:
                    raise RuntimeError("not enough cards to deal")
                self.log.append(ResolvedDraw.create(self.current_player, card))

    def iterate_players(self):
        for i in range(len(self.players)):
            self.current_player = i
            yield i

    def take_hidden_card_from_deck(self) -> Card:
        if not self.deck:
            if self.end_mode == EndMode.fair and self.final_player is None:
                self.final_player = (self.current_player - 1) % len(self.hands)
            return None
        card = self.deck.pop()
        if self.end_mode == EndMode.official and not self.deck and self.final_player is None:
            self.final_player = (None, self.current_player)
        self.hands[self.current_player].append(card)
        return card.hidden()

    def is_game_over(self) -> bool:
        if self.end_mode == EndMode.endless and not [i for i in self.hands[(self.current_player + 1) % len(self.hands)] if i]:
            return True
        return (self.lives == 0 or self.final_player == self.current_player or
                all(slot == len(self.rules.ranks) for slot in self.slots))

    def resolve(self, move: NamedTuple) -> None:
        if isinstance(move, Clue):
            if not self.clues > 0:
                raise IllegalMove("no clues to give")
            if not move.player != self.current_player:
                raise IllegalMove("can't clue yourself")
            cards = [card.hidden() for card in self.hands[move.player] if getattr(card.data, move.type) == move.param]
            if not cards:
                raise IllegalMove("no empty clues")
            self.clues -= 1
            self.log.append(ResolvedClue.create(self.current_player, move.player, move.type, move.param, cards))
        elif isinstance(move, Play):
            card = self.take_card_from_current_hand(move.card_id)
            is_success = self.slots[card.data.suit] == card.data.rank
            if is_success:
                self.slots[card.data.suit] += 1
                if self.slots[card.data.suit] == len(self.rules.ranks):
                    if self.clues < self.rules.max_tokens.clues:
                        self.clues += 1
            else:
                self.discard_pile[card.data.suit][card.data.rank] += 1
                self.lives -= 1
                assert self.lives >= 0
            drawn = self.take_hidden_card_from_deck()
            self.log.append(ResolvedPlay.create(self.current_player, card, drawn, is_success))
        elif isinstance(move, Discard):
            card = self.take_card_from_current_hand(move.card_id)
            self.discard_pile[card.data.suit][card.data.rank] += 1
            self.clues += 1
            drawn = self.take_hidden_card_from_deck()
            self.log.append(ResolvedDiscard.create(self.current_player, card, drawn))
        else:
            raise IllegalMove('no such move')

    @property
    def clues(self):
        return self.tokens.clues
    @clues.setter
    def clues(self, value: int):
        self.tokens = self.tokens._replace(clues=value)

    @property
    def score(self):
        return sum(self.slots) if self.lives > 0 else 0

    @property
    def lives(self):
        return self.tokens.lives
    @lives.setter
    def lives(self, value: int):
        self.tokens = self.tokens._replace(lives=value)

    def take_card_from_current_hand(self, card_id: int) -> Card:
        for i, card in enumerate(self.hands[self.current_player]):
            if card.id == card_id:
                del self.hands[self.current_player][i]
                return card
        raise IllegalMove(f'no such card in hand: {card_id}')

    def print(self):
        for attr in ['log', 'tokens', 'slots', 'hands', 'discard_pile', 'score']:
            print(f'{attr}:')
            pprint(getattr(self, attr))


def run_game_n_times(player, times, num_players=3, end_mode=EndMode.official, suits=5, allow_cheats=False):
    score = []
    for _t in range(times):
        h = Hanabi([player] * num_players, rules=DEFAULT_RULES._replace(suits=suits), allow_cheats=allow_cheats, end_mode=end_mode)
        score.append(h.run())

    import pandas as pd
    scores = pd.Series(score)
    print(scores.describe())
    hist = scores.value_counts(sort=False).sort_index()
    print(hist)
    hist.plot(style='o', logy=True)
    return scores


def run_game_once(player, num_players=3, end_mode=EndMode.official, suits=5, allow_cheats=False):
    h = Hanabi([player] * num_players, rules=DEFAULT_RULES._replace(suits=suits), allow_cheats=allow_cheats, end_mode=end_mode)
    h.run()
    h.print()
    return h
