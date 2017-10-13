from hanabi import Clue, Play, Discard, ResolvedClue

def naive_player(state, log, hands, rules, tokens, slots, discard_pile):
    """
    Zvika and Ofer's naive player
    """
    my_id = len(log) % len(hands)
    if state is None:
        state = set()

    possible_actions = [Play]
    if tokens.clues > 0:
        possible_actions.append(Clue)

    if tokens.clues < rules.max_tokens.clues:
        possible_actions.append(Discard)

    my_card_ids = [card.id for card in hands[my_id]]

    for move in log[-len(hands):]:
        if move.__name__ == 'ResolvedClue':
            if move.player == my_id:
                for card in move.cards:
                    state.add(card.id)

    state = state.intersection(my_card_ids)

    if state: # Its better to play than hint
        play_card = max(state)
        return state, Play.create(play_card)

    if tokens.clues > 0: # Its better to hint than discard
        for i in range(len(hands) - 1):
            player = (my_id + i + 1) % len(hands)
            player_suits = set([card.known.suit for card in hands[player]])
            player_ranks = set([card.known.rank for card in hands[player]])
            for card in hands[player]:
                if slots[card.known.suit] != card.known.rank:
                    player_suits -= set([card.known.suit])
                    player_ranks -= set([card.known.rank])

            if player_ranks:
                return state, Clue.create(player, 'rank', max(player_ranks)) # its better to go up then sideways
            if player_suits:
                return state, Clue.create(player, 'suit', player_suits.pop())

    if tokens.clues < rules.max_tokens.clues: # Its better to discard then playing like an idiot
        return state, Discard.create(min(my_card_ids))

    return state, Play.create(max(my_card_ids)) # If all else fails, play like an idiot
