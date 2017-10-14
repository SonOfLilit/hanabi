import random
from pprint import pprint
from collections import namedtuple
from enum import Enum
from typing import List, NamedTuple, Tuple


class EndMode(Enum):
    official = 1
    endless = 2
    fair = 3

class IllegalMove(Exception):
    pass

class Suit(int):
    def __str__(self):
        return chr(ord("A") + self)

class Rank(int):
    def __str__(self):
        return str(self + 1)

class KnownCard(namedtuple('KnownCard', 'suit rank')):
    def __repr__(self):
        return f':{self.suit}{self.rank}'

class Card(namedtuple('Card', 'id data')):
    def __repr__(self):
        return f'#{self.id:02}{self.data or ""}'
    def hidden(self):
        return self._replace(data=None)


class Tokens(namedtuple('Tokens', 'clues lives')):
    pass

class Rules(namedtuple('Rules', 'max_tokens suits ranks cards_per_player')):
    pass


class Move():
    @property
    def move_prefix(self):
        return f'{self.move} '
    @property
    def resolved_prefix(self):
        return f'{self.cur_player}>{self.move} '
    @classmethod
    def create(cls, *args, **kwargs):
        return cls(cls.identifier, *args, **kwargs)

class Clue(namedtuple('Clue', 'move player type param'), Move):
    identifier = 'c'
    def __repr__(self):
        return self.move_prefix + f'P={self.player} {self.type}={self.param}'

class Play(namedtuple('Play', 'move card_id'), Move):
    identifier = 'p'
    def __repr__(self):
        return self.move_prefix + f'{self.card_id}'

class Discard(namedtuple('Discard', 'move card_id'), Move):
    identifier = 'd'
    def __repr__(self):
        return self.move_prefix + f'{self.card_id}'

IDENTIFIER_TO_MOVE = {cls.identifier: cls for cls in [Clue, Play, Discard]}

def tuple_to_move(tup: Tuple) -> NamedTuple:
    return IDENTIFIER_TO_MOVE[tup[0]]._make(tup)
    
    
class ResolvedClue(namedtuple('ResolvedClue', 'move cur_player player type param cards cards_neg'), Clue):
    def __repr__(self):
        return self.resolved_prefix + f'player={self.player} {self.type}={self.param} {self.cards} {self.cards_neg}'

class ResolvedPlay(namedtuple('ResolvedPlay', 'move cur_player card new_card is_success'), Play):
    @property
    def card_id(self):  # overwrite the parent property
        return self.card.id
    def __repr__(self):
        return self.resolved_prefix + f'{self.card}{"+" if self.is_success else "-"} {self.new_card}'

class ResolvedDiscard(namedtuple('ResolvedDiscard', 'move cur_player card new_card'), Discard):
    @property
    def card_id(self):  # overwrite the parent property
        return self.card.id
    def __repr__(self):
        return self.resolved_prefix + f'{self.card}  {self.new_card}'
    
class ResolvedDraw(namedtuple('ResolvedDraw___', 'move cur_player cards'), Move):
    identifier = 'n'
    def __repr__(self):
        return self.resolved_prefix + f'{self.cards}'



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
        self.hands = tuple([[] for _ in players])
        self.hands_start = None
        self.tokens = self.rules.max_tokens
        self.log = []
        self.player_states = [None] * len(players)

        self.final_player = None
        self.slots = [0] * self.rules.suits
        self.discard_pile = tuple([[0] * len(self.rules.ranks) for _ in range(self.rules.suits)])

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
                cards += [KnownCard(Suit(suit), Rank(rank))] * count
        random.shuffle(cards)
        return list(reversed([Card(card_id, card) for card_id, card in enumerate(cards)]))

    def deal_cards(self) -> None:
        for player in self.iterate_players():
            cards = [self.take_card_from_deck_to_hand() for _i in range(self.rules.cards_per_player)]
            self.log.append(ResolvedDraw.create(self.current_player, cards))
            if any(card is None for card in cards):
                raise RuntimeError("not enough cards to deal")
        self.hands_start = tuple([hand.copy() for hand in self.hands])
        
    def iterate_players(self):
        for i in range(len(self.players)):
            self.current_player = i
            yield i

    def take_card_from_deck_to_hand(self) -> Card:
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

    @classmethod
    def resolve_clue(_cls, cur_player, hands, move: NamedTuple):
            if move.player == cur_player:
                raise IllegalMove("can't clue yourself")
            cards = [card for card in hands[move.player] if getattr(card.data, move.type) == move.param]
            if not cards:
                raise IllegalMove("no empty clues")
            cards_pos = [card.hidden() for card in cards]
            cards_neg = [card.hidden() for card in hands[move.player] if card not in cards]
            return ResolvedClue.create(cur_player, move.player, move.type, move.param, cards_pos, cards_neg)
        
    def resolve(self, move: NamedTuple) -> None:
        if isinstance(move, Clue):
            if self.clues <= 0:
                raise IllegalMove("no clues to give")
            clue = self.resolve_clue(self.current_player, self.hands, move)
            self.clues -= 1
            self.log.append(clue)
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
            drawn = self.take_card_from_deck_to_hand()
            self.log.append(ResolvedPlay.create(self.current_player, card, drawn, is_success))
        elif isinstance(move, Discard):
            card = self.take_card_from_current_hand(move.card_id)
            self.discard_pile[card.data.suit][card.data.rank] += 1
            self.clues += 1
            drawn = self.take_card_from_deck_to_hand()
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
        for attr in 'rules hands_start log tokens slots hands discard_pile score'.split():
            print(f'{attr}:')
            pprint(getattr(self, attr))
