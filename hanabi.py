from collections import namedtuple

class KnownCard(namedtuple('KnownCard', 'suit number')):
    pass
class Card(namedtuple('Card', 'id known')):
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
        def create(cls, data):
            return cls(cls.identifier, *data)
    MyMove.identifier = identifier
    MyMove.__name__ = name
    IDENTIFIER_TO_MOVE[identifier] = MyMove
    return MyMove
Draw = Move('Draw', 'n', 'move card')
Clues = Move('Clues', 'c', 'move player type param')
ResolvedClues = Move('ResolvedClues', 'c', 'move player type param cards')
Play = Move('Play', 'p', 'move card_id')
Discard = Move('Discard', 'd', 'move card_id')
ResolvedPlay = Move('ResolvedPlay', 'p', 'move card new_card is_success')
ResolvedDiscard = Move('ResolvedDiscard', 'd', 'move card new_card')

def tuple_to_move(tup):
    return IDENTIFIER_TO_MOVE[tup[0]]._make(tup)

class Hanabi:
    def __init__(self, players, rules=Rules(max_tokens=Tokens(8, 4), suits=5, ranks=[3,2,2,2,1], cards_per_player=None), deck=None):
        if rules.cards_per_player is None:
            rules = rules._replace(cards_per_player=5 if len(players) <= 3 else 4)
        self.players = players
        self.rules = rules
        self.deck = deck

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
        self.deal_cards()
        for i, player in cycle(enumerate(players)):
            self.current_player = i
            hands = list(self.hands)
            hands[i] = [card.hidden() for card in hands[i]]
            move, self.player_states[i] = player(self.player_states[i], self.log, hands, self.rules, self.tokens, self.slots, self.discard_pile)
            self.resolve(tuple_to_move(move))
            if self.is_game_over():
                return sum(self.slots)

    def new_shuffled_deck(self):
        cards = []
        for suit in range(self.rules.suits):
            for rank, count in enumerate(ranks):
                for item in range(count):
                    cards.append(KnownCard(suit, rank))
        random.shuffle(cards)
        return [Card(id, card) for id, card in enumerate(cards)]

    def deal_cards(self):
        for player in range(len(self.players)):
            for i in range(self.rules.cards_per_player):
                card = self.take_hidden_card_from_deck()
                assert card is not None
                self.log.append(Draw.create(card))

    def take_hidden_card_from_deck(self):
        if not self.deck:
            return None
        card = self.deck.pop()
        if not self.deck:
            self.final_player = current_player
        self.hands[player].append(card)
        return card.hidden()

    def is_game_over(self):
        return (self.lives == 0 or self.final_player == self.current_player or
            all(slot == len(self.rules.ranks) for slot in self.slots))

    def resolve(self, move):
        if isinstance(move, Clues):
            assert self.clues > 0
            self.clues -= 1
            assert move.player != current_player
            type = {'s': 'suit', 'n': 'rank'}[move.type]
            cards = [card.hidden() for card in hands[move.player] if getattr(card, type) == move.param]
            assert cards
            self.log.append(ResolvedClues.create(move.player, move.type, move.param, cards))
        elif isinstance(move, Play):
            card = self.take_card_from_current_hand(move.card_id)
            is_success = self.slots[card.suit] + 1 == card.rank
            if is_success:
                self.slots[card.suit] += 1
                if self.slots[card.suit] == len(self.rules.ranks):
                    if self.clues < self.rules.max_tokens.clues:
                        self.clues += 1
            else:
                self.graveyard[card.suit][card.rank] += 1
                self.lives -= 1
                assert self.lives >= 0
            drawn = self.take_hidden_card_from_deck()
            self.log.append(ResolvedPlay.create(card, drawn, is_success))
        elif isinstance(move, Discard):
            card = self.take_card_from_current_hand(move.card_id)
            self.graveyard[card.suit][card.rank] += 1
            self.lives -= 1
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

'''
my_player(
    state=...,
    log=['c #01', 'c #02', 'c #03', ..., 'p #08:23 c #09', 'd #01:23 c#10', 'i 0s2 #02 #03 #04', 'h 0n2 #02 #03 #04'],
    log=[(p/d, #, c#), (i, player, s/n, sn#, list_of_ids)]
    hands=[['#07:24', '#09:32'], ['#10', '#17'], ['#20:15', ...], ...],
    rules=Rules(...),
    tokens=Tokens(1,1),
    slots=[4,1,3,0,5],
    graveyard=[[1,1,0,2,0], [2,1,0,1,0], [0,0,1,0,0], [0,0,0,0,0], [0,0,0,0,0]],
)

def my_player(state, log, hands, rules, tokens, slots, graveyard):
    
    return action, new_state
'''
