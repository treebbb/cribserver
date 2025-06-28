from typing import List, Tuple
import random
import itertools
from .cards import Card, create_deck

def score_play_phase(played_cards: List[Card], current_card: Card) -> int:
    """Score the play phase for the current card (custom Cribbage rules)."""
    score = 0
    total = sum(card.value() for card in played_cards + [current_card])

    # 15 or 31
    if total == 15 or total == 31:
        score += 2

    # Pairs/Triplets/Quads (non-consecutive)
    rank_counts = {}
    for card in played_cards + [current_card]:
        rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1
    for count in rank_counts.values():
        if count == 2:
            score += 2  # Pair
        elif count == 3:
            score += 6  # Triplet (2 + 4)
        elif count == 4:
            score += 12  # Quad (2 + 4 + 6)

    # Runs (non-consecutive, 3+ cards)
    values = sorted([card.value() for card in played_cards + [current_card]])
    for length in range(3, len(values) + 1):
        for combo in itertools.combinations(values, length):
            if sorted(combo) == list(range(min(combo), min(combo) + length)):
                score += length
                break  # Score longest run only

    return score

def score_show_phase(hand: List[Card], starter: Card, is_crib: bool = False) -> int:
    """Score hand or crib in show phase (standard Cribbage rules)."""
    score = 0
    cards = hand + [starter]

    # Fifteens
    for r in range(2, len(cards) + 1):
        for combo in itertools.combinations(cards, r):
            if sum(card.value() for card in combo) == 15:
                score += 2

    # Pairs
    rank_counts = {}
    for card in cards:
        rank_counts[card.rank] = rank_counts.get(card.rank, 0) + 1
    for count in rank_counts.values():
        if count >= 2:
            score += 2 * (count * (count - 1) // 2)

    # Runs
    values = sorted([card.value() for card in cards])
    for length in range(3, len(values) + 1):
        for combo in itertools.combinations(values, length):
            if sorted(combo) == list(range(min(combo), min(combo) + length)):
                score += length
                break

    # Flush
    if all(card.suit == hand[0].suit for card in hand):
        score += 4
        if not is_crib and all(card.suit == starter.suit for card in cards):
            score += 1
        elif is_crib and all(card.suit == starter.suit for card in cards):
            score += 5

    # Nobs
    for card in hand:
        if card.rank == "jack" and card.suit == starter.suit:
            score += 1

    return score

def simulate_play_sequences(
    hand: List[Card],
    starter: Card,
    used_cards: List[Card],
    dealer: bool,
    num_simulations: int = 576
) -> List[Tuple[List[Card], float, float, float, float]]:
    """Simulate play sequences and return top 5 discard kitties with scores."""
    deck = [card for card in create_deck() if card not in used_cards and card not in hand]
    results = []

    # All possible discards (2 cards from 6)
    for discard in itertools.combinations(hand, 2):
        remaining_hand = [card for card in hand if card not in discard]
        play_score_sum = 0
        show_score_sum = 0
        crib_score_sum = 0 if dealer else None

        # Simulate play sequences
        for _ in range(num_simulations // len(list(itertools.combinations(hand, 2)))):
            temp_deck = deck.copy()
            random.shuffle(temp_deck)
            opponent_hand = [temp_deck.pop() for _ in range(4)]  # Simplified opponent hand
            played_cards = []
            current_total = 0
            play_score = 0

            # Simulate play phase (alternate, <= 31)
            players = [remaining_hand, opponent_hand]
            current_player = 0
            while any(players[0]) or any(players[1]):
                valid_moves = [c for c in players[current_player] if current_total + c.value() <= 31]
                if not valid_moves:
                    # Go: 1 point to opponent if they can play
                    current_player = (current_player + 1) % 2
                    valid_moves = [c for c in players[current_player] if current_total + c.value() <= 31]
                    if valid_moves:
                        card = random.choice(valid_moves)
                        players[current_player].remove(card)
                        played_cards.append(card)
                        play_score += score_play_phase(played_cards[:-1], card)
                        current_total += card.value()
                    else:
                        play_score += 1  # Go point
                        current_total = 0
                        played_cards = []
                else:
                    card = random.choice(valid_moves)
                    players[current_player].remove(card)
                    played_cards.append(card)
                    play_score += score_play_phase(played_cards[:-1], card)
                    current_total += card.value()
                    if current_total == 31:
                        current_total = 0
                        played_cards = []
                    current_player = (current_player + 1) % 2

            play_score_sum += play_score
            show_score_sum += score_show_phase(remaining_hand, starter)
            if dealer:
                crib = list(discard) + [temp_deck.pop() for _ in range(2)]  # Simplified crib
                crib_score_sum += score_show_phase(crib, starter, is_crib=True)

        # Average scores
        num = num_simulations // len(list(itertools.combinations(hand, 2)))
        avg_play = play_score_sum / num
        avg_show = show_score_sum / num
        avg_crib = crib_score_sum / num if dealer else 0
        total = avg_play + avg_show + (avg_crib if dealer else 0)
        results.append((list(discard), avg_play, avg_show, avg_crib, total))

    # Return top 5 discards by total score
    return sorted(results, key=lambda x: x[4], reverse=True)[:5]
