from hanabi import Play, Discard, Clue


def oracle_player(state, log, hands, rules, tokens, slots, discard_pile):
    """
    Zvika and Ofer's oracle player
    """
    my_id = len(log) % len(hands)

    my_hand = hands[my_id]
    playable_card = None
    for card in my_hand:
        if slots[card.known.suit] == card.known.rank:
            if playable_card is None or playable_card.known.rank < card.known.rank:
                playable_card = card

    if playable_card is not None:
        return state, Play.create(playable_card.id)

    def get_card_to_discard():
        # discard already played
        for card in my_hand:
            if slots[card.known.suit] > card.known.rank:
                return card.id
        # discard unreachable
        for suit in range(rules.suits):
            max_rank_in_suit = None
            for rank in range(len(rules.ranks)):
                left_in_rank = rules.ranks[rank] - discard_pile[suit][rank]
                if rank >= slots[suit] and left_in_rank == 0:
                    max_rank_in_suit = rank
                    break
            if max_rank_in_suit:
                for card in my_hand:
                    if card.known.suit == suit and card.known.rank > max_rank_in_suit:
                        return card.id

        # discard duplicates in own hand
        knowns = [card.known for card in my_hand]
        if len(set(knowns)) < len(knowns):
            for i, known in enumerate(knowns):
                for known2 in knowns[i:]:
                    if known == known2:
                        return my_hand[i].id

        # discard duplicates with others
        knowns = [card.known for card in my_hand]
        for hand in hands[:my_id]+hands[my_id+1:]:
            knowns2 = [card.known for card in hand]
            if len(set(knowns+knowns2)) < len(knowns)+len(set(knowns2)):
                for i, known in enumerate(knowns):
                    for known2 in knowns2:
                        if known == known2:
                            return my_hand[i].id

    if tokens.clues < rules.max_tokens.clues:
        card = get_card_to_discard()
        if card is not None:
            return state, Discard.create(card)

    if tokens.clues > 0:
        player = (my_id + 1) % len(hands)
        if hands[player]:
            return state, Clue.create(player, 'suit', hands[player][0].known.suit)

    if tokens.lives > 1:
        card = get_card_to_discard()
        if card is not None:
            return state, Play.create(card)

    diff = None
    throw = None
    for card in my_hand:
        card_diff = card.known.rank - slots[card.known.suit]
        if diff is None or card_diff > diff:
            diff = card_diff
            throw = card

    if tokens.clues < rules.max_tokens.clues:
        return state, Discard.create(throw.id)
    else:
        return state, Play.create(throw.id)
