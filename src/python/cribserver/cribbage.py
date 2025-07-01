from typing import List, Tuple
import random
import itertools
from .cards import Card, Deck

def score_play_phase(played_cards: List[int]) -> int:
    """Score the play phase for the current card (custom Cribbage rules)."""
    score = 0
    total = sum(Card.value(card) for card in played_cards)

    # 15 or 31
    if total == 15 or total == 31:
        score += 2

    # Pairs/Triplets/Quads (non-consecutive)
    rank_counts = {}
    for card in played_cards:
        card_rank = Card.rank(card)
        rank_counts[card_rank] = rank_counts.get(card_rank, 0) + 1
    for count in rank_counts.values():
        if count == 2:
            score += 2  # Pair
        elif count == 3:
            score += 6  # Triplet (2 + 4)
        elif count == 4:
            score += 12  # Quad (2 + 4 + 6)

    # Runs (non-consecutive, 3+ cards)
    values = sorted([card.rank(card) for card in played_cards])
    for length in range(3, len(values) + 1):
        for combo in itertools.combinations(values, length):
            if sorted(combo) == list(range(min(combo), min(combo) + length)):
                score += length
                break  # Score longest run only

    return score

def score_show_phase(hand: List[int], starter: int, is_crib: bool = False) -> int:
    """Score hand or crib in show phase (standard Cribbage rules)."""
    score = 0
    cards = hand + [starter]

    # Fifteens
    for r in range(2, len(cards) + 1):
        for combo in itertools.combinations(cards, r):
            if sum(Card.value(card) for card in combo) == 15:
                score += 2

    # Pairs
    rank_counts = {}
    for card in cards:
        card_rank = Card.rank(card)
        rank_counts[card_rank] = rank_counts.get(card_rank, 0) + 1
    for count in rank_counts.values():
        if count >= 2:
            score += 2 * (count * (count - 1) // 2)

    # Runs
    values = sorted([Card.rank(card) for card in cards])
    for length in range(3, len(values) + 1):
        for combo in itertools.combinations(values, length):
            if sorted(combo) == list(range(min(combo), min(combo) + length)):
                score += length
                break

    # Flush
    if all(Card.suit(card) == Card.suit(hand[0]) for card in hand):
        score += 4
        if not is_crib and all(Card.suit(card) == Card.suit(starter) for card in cards):
            score += 1
        elif is_crib and all(Card.suit(card) == Card.suit(starter) for card in cards):
            score += 5

    # Nobs
    for card in hand:
        if Card.rank(card) == Card.JACK_RANK and Card.suit(card) == Card.suit(starter):
            score += 1

    return score
