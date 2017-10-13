import random
from pprint import pprint
from hanabi import Clue, Play, Discard


def make_io_player(name):
    """
    Aur's basic IO player generator
    """
    def io_player(state, log, hands, rules, tokens, slots, discard_pile):
        print(f"{name}'s turn")
        pprint(log[-len(hands):])
        pprint(hands)
        pprint(tokens)
        pprint(slots)
        pprint(discard_pile)
        pprint('What will it be?')
        pprint('[c]lue <player><type><n>\t\t[p]lay <card>\t\t[d]iscard <card>')
        move = input().split()
        try:
            if move[0] == 'c':
                _, ptn = move
                p, t, n = ptn
                t = {'s': 'suit', 'n': 'rank'}[t]
                return state, Clue.create(int(p), t, int(n))
            elif move[0] == 'p':
                _, card_id = move
                return state, Play.create(int(card_id))
            elif move[0] == 'd':
                _, card_id = move
                return state, Discard.create(int(card_id))
        except:
            print('illegal move')
            return io_player(state, log, hands, rules, tokens, slots, discard_pile)
    return io_player


def random_player(state, log, hands, rules, tokens, slots, discard_pile):
    """
    Zvika and Ofer's random player
    """
    my_id = len(log) % len(hands)

    possible_actions = [Play]
    if tokens.clues > 0:
        possible_actions.append(Clue)

    if tokens.clues < rules.max_tokens.clues:
        possible_actions.append(Discard)

    action = random.choice(possible_actions)

    if action == Play:
        return state, Play.create(random.choice(hands[my_id]).id)
    if action == Discard:
        return state, Discard.create(random.choice(hands[my_id]).id)
    if action == Clue:
        player = random.choice([i for i in range(len(hands)) if i != my_id])
        type = random.choice(['suit', 'rank'])
        return state, Clue.create(player, type, getattr(random.choice(hands[player]).known, type))

"""
h = Hanabi([random_player, random_player, random_player])
print(h.run())
print(h.log)



Hanabi([make_io_player('Aur'), make_io_player('Ofer')]).run()
"""
