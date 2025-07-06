import traceback
from typing import List

def cts(card_idx):
    '''
    card to string
    '''
    return Card.to_string(card_idx).strip()

def score_play_phase(played_cards: List[int], score_log: List[str]) -> int:
    """Score the play phase for the last card played (custom Cribbage rules) and log scoring events."""
    if not played_cards:
        return 0

    score = 0
    last_card = played_cards[-1]
    last_card_rank = Card.get_rank(last_card)
    last_card_value = Card.get_value(last_card)
    total = sum(Card.get_value(card) for card in played_cards)

    # Check for 15 or 31
    if total == 15:
        score += 2
        score_log.append("2 points for 15 total")
    elif total == 31:
        score += 2
        score_log.append("2 points for 31 total")

    # Check for pairs (only with the last card)
    pair_cards = [last_card]
    for i in range(len(played_cards) - 1):  # Check up to second-to-last card
        if Card.get_rank(played_cards[i]) == last_card_rank:
            pair_cards.append(played_cards[i])
    if len(pair_cards) == 2:
        score += 2
        score_log.append(f"2 points for pair of {', '.join(cts(c) for c in pair_cards)}")
    elif len(pair_cards) == 3:
        score += 6
        score_log.append(f"6 points for triplet of {', '.join(cts(c) for c in pair_cards)}")
    elif len(pair_cards) == 4:
        score += 12
        score_log.append(f"12 points for quad of {', '.join(cts(c) for c in pair_cards)}")

    # Check for runs (only involving the last card)
    # Collect ranks of consecutive cards from the end
    recent_ranks = [last_card_rank]
    for i in range(len(played_cards) - 2, -1, -1):
        current_rank = Card.get_rank(played_cards[i])
        if current_rank in recent_ranks:  # Skip duplicates to avoid breaking runs
            continue
        recent_ranks.append(current_rank)
        # Check for a run with the last card
        sorted_ranks = sorted(recent_ranks)
        for length in range(len(sorted_ranks), 2, -1):  # Check longest runs first
            for start in range(len(sorted_ranks) - length + 1):
                run = sorted_ranks[start:start + length]
                if last_card_rank in run and run == list(range(min(run), min(run) + length)):
                    # Found a run including the last card
                    run_cards = []
                    for card in played_cards[-length:]:  # Check recent cards for the run
                        if Card.get_rank(card) in run and cts(card) not in run_cards:
                            run_cards.append(cts(card))
                    run_cards.sort(key=lambda x: Card.get_rank(Card.from_string(x)))
                    score += length
                    score_log.append(f"{length} points for run of {', '.join(run_cards)}")
                    return score  # Return immediately after scoring the longest run

    return score

from typing import List, Tuple
import random
import itertools
from .cards import Card, Deck

def score_show_phase(hand: List[int], starter: int, is_crib: bool = False, score_log: List[str] = None) -> int:
    """Score hand or crib in show phase (standard Cribbage rules) and log scoring events."""
    # traceback.print_stack()
    if score_log is None:
        score_log = []
    score = 0
    cards = hand + [starter]

    # Fifteens
    for r in range(2, len(cards) + 1):
        for combo in itertools.combinations(cards, r):
            if sum(Card.get_value(card) for card in combo) == 15:
                score += 2
                combo_cards = [cts(card) for card in combo]
                score_log.append(f"2 points for 15 from {', '.join(combo_cards)}")

    # Pairs
    rank_counts = {}
    for card in cards:
        card_rank = Card.get_rank(card)
        rank_counts[card_rank] = rank_counts.get(card_rank, 0) + 1
    for rank, count in rank_counts.items():
        if count >= 2:
            pairs = count * (count - 1) // 2
            score += 2 * pairs
            pair_cards = [cts(card) for card in cards if Card.get_rank(card) == rank]
            score_log.append(f"{2 * pairs} points for {pairs} pair{'s' if pairs > 1 else ''} of {', '.join(pair_cards)}")

    # Runs
    values = sorted([Card.get_rank(card) for card in cards])  # Get ranks: [5, 8, 9, 9, 10]
    for length in range(len(values), 2, -1):  # Check longest runs first (5, 4, 3)
        runs = []
        for combo in itertools.combinations(range(len(cards)), length):  # Pick card indices
            combo_ranks = sorted([Card.get_rank(cards[i]) for i in combo])
            if combo_ranks == list(range(min(combo_ranks), min(combo_ranks) + length)):
                run_cards = [cts(cards[i]) for i in combo]
                run_cards.sort(key=lambda x: Card.get_rank(Card.from_string(x)))
                runs.append(run_cards)
        if runs:  # If we found runs, score them and stop
            for run_cards in runs:
                score += length
                score_log.append(f"{length} points for run of {', '.join(run_cards)}")
            break

    # Flush
    if all(Card.get_suit(card) == Card.get_suit(hand[0]) for card in hand):
        score += 4
        flush_cards = [cts(card) for card in hand]
        #print(f"FLUSH, {flush_cards}")
        score_log.append(f"4 points for flush of {', '.join(flush_cards)}")
        if not is_crib and all(Card.get_suit(card) == Card.get_suit(starter) for card in cards):
            score += 1
            all_cards = [cts(card) for card in cards]
            score_log.append(f"1 point for flush including starter {cts(starter)}")
        elif is_crib and all(Card.get_suit(card) == Card.get_suit(starter) for card in cards):
            score += 5
            all_cards = [cts(card) for card in cards]
            score_log.append(f"5 points for crib flush of {', '.join(all_cards)}")

    # Nobs
    for card in hand:
        if Card.get_rank(card) == Card.JACK_RANK and Card.get_suit(card) == Card.get_suit(starter):
            score += 1
            score_log.append(f"1 point for nobs with {cts(card)} matching suit of starter {cts(starter)}")

    return score

def deal_to_players(deck: Deck, player_id1: str, player_id2: str):
    deck.create_pile("starter")
    deck.create_pile("crib")
    deck.create_pile("phase1")
    deck.shuffle()
    deck.create_pile(player_id1)
    deck.create_pile(player_id2)
    deck.deal_to_piles([player_id1, player_id2], 6)
