#! /usr/bin/env python3

import random
import itertools
from collections import defaultdict

# Card representation: (value, suit)
# Value: 1=Ace, 2-10, 11=Jack, 12=Queen, 13=King
# Suit: 'S' (Spades), 'H' (Hearts), 'D' (Diamonds), 'C' (Clubs)
def create_deck():
    suits = ['S', 'H', 'D', 'C']
    values = list(range(1, 14))  # 1=Ace, ..., 11=Jack, 12=Queen, 13=King
    return [(v, s) for v in values for s in suits]

# Get cribbage card value (Ace=1, 2-10 face value, J/Q/K=10)
def card_value(card):
    return min(card[0], 10)

def score_play_sequence(play_seq, is_dealer):
    my_score = 0
    opp_score = 0
    total = 0
    # Assume non-dealer (you) starts; if dealer, opponent starts
    my_turns = range(0, 8, 2) if not is_dealer else range(1, 8, 2)
    
    # Track all cards played so far
    played_cards = []
    value_counts = defaultdict(int)  # Count of each card value
    
    for i, card in enumerate(play_seq):
        total += card_value(card)
        is_my_turn = i in my_turns
        played_cards.append(card)
        current_value = card_value(card)
        value_counts[current_value] += 1
        
        # Score 15 or 31
        if total == 15:
            if is_my_turn:
                my_score += 2
            else:
                opp_score += 2
        elif total == 31:
            if is_my_turn:
                my_score += 2
            else:
                opp_score += 2
        
        # Pairs, triplets, quads (any combination of played cards)
        if value_counts[current_value] == 2:
            if is_my_turn:
                my_score += 2  # Pair
            else:
                opp_score += 2
        elif value_counts[current_value] == 3:
            if is_my_turn:
                my_score += 4  # Triplet (additional 4, total 6)
            else:
                opp_score += 4
        elif value_counts[current_value] == 4:
            if is_my_turn:
                my_score += 6  # Quad (additional 6, total 12)
            else:
                opp_score += 6
        
        # Runs (check all subsets of played cards for runs of 3+)
        current_values = sorted([card_value(c) for c in played_cards])
        for length in range(3, min(len(played_cards) + 1, 6)):  # Check runs of 3 to 5
            for subset in itertools.combinations(current_values, length):
                if max(subset) - min(subset) == length - 1 and len(set(subset)) == length:
                    # Valid run (consecutive values, no duplicates)
                    if is_my_turn:
                        my_score += length
                    else:
                        opp_score += length
    
    return my_score

def score_play_sequence3(play_seq, is_dealer):
    my_score = 0
    opp_score = 0
    total = 0
    # Assume non-dealer (you) starts; if dealer, opponent starts
    my_turns = range(0, 8, 2) if not is_dealer else range(1, 8, 2)
    
    for i, card in enumerate(play_seq):
        total += card_value(card)
        # Determine whose turn it is
        is_my_turn = i in my_turns
        # Score 15 or 31
        if total == 15:
            if is_my_turn:
                my_score += 2
            else:
                opp_score += 2
        elif total == 31:
            if is_my_turn:
                my_score += 2
            else:
                opp_score += 2
        # Pairs, triplets, quads
        if i >= 1 and card_value(card) == card_value(play_seq[i-1]):
            if is_my_turn:
                my_score += 2
                if i >= 2 and card_value(card) == card_value(play_seq[i-2]):
                    my_score += 2  # Triplet
                    if i >= 3 and card_value(card) == card_value(play_seq[i-3]):
                        my_score += 2  # Quad
            else:
                opp_score += 2
                if i >= 2 and card_value(card) == card_value(play_seq[i-2]):
                    opp_score += 2  # Triplet
                    if i >= 3 and card_value(card) == card_value(play_seq[i-3]):
                        opp_score += 2  # Quad
        # Runs
        if i >= 2:
            values = sorted([card_value(play_seq[j]) for j in range(i-2, i+1)])
            if values[2] == values[1] + 1 == values[0] + 2:
                if is_my_turn:
                    my_score += 3
                else:
                    opp_score += 3
        if i >= 3:
            values = sorted([card_value(play_seq[j]) for j in range(i-3, i+1)])
            if values[3] == values[2] + 1 == values[1] + 2 == values[0] + 3:
                if is_my_turn:
                    my_score += 4
                else:
                    opp_score += 4
        if i >= 4:
            values = sorted([card_value(play_seq[j]) for j in range(i-4, i+1)])
            if values[4] == values[3] + 1 == values[2] + 2 == values[1] + 3 == values[0] + 4:
                if is_my_turn:
                    my_score += 5
                else:
                    opp_score += 5
    
    return my_score

# Score a sequence of played cards (play phase)
def score_play_sequence2(play_seq, is_dealer):
    score = 0
    total = 0
    for i, card in enumerate(play_seq):
        total += card_value(card)
        # Check for 15 or 31
        if total == 15:
            score += 2
        elif total == 31:
            score += 2
        # Check for pairs, triplets, etc.
        if i >= 1 and card_value(card) == card_value(play_seq[i-1]):
            score += 2
            if i >= 2 and card_value(card) == card_value(play_seq[i-2]):
                score += 2  # Triplet
                if i >= 3 and card_value(card) == card_value(play_seq[i-3]):
                    score += 2  # Quad
        # Check for runs
        if i >= 2:
            values = sorted([card_value(play_seq[j]) for j in range(i-2, i+1)])
            if values[2] == values[1] + 1 == values[0] + 2:
                score += 3
        if i >= 3:
            values = sorted([card_value(play_seq[j]) for j in range(i-3, i+1)])
            if values[3] == values[2] + 1 == values[1] + 2 == values[0] + 3:
                score += 4
        if i >= 4:
            values = sorted([card_value(play_seq[j]) for j in range(i-4, i+1)])
            if values[4] == values[3] + 1 == values[2] + 2 == values[1] + 3 == values[0] + 4:
                score += 5
    return score

# Score a hand in the show phase (including starter card)
def score_hand(hand, starter, is_crib=False):
    score = 0
    cards = hand + [starter]
    values = [card_value(c) for c in cards]
    suits = [c[1] for c in cards]
    
    # Fifteens
    for r in range(2, 6):
        for combo in itertools.combinations(values, r):
            if sum(combo) == 15:
                score += 2
    
    # Pairs
    for i, card1 in enumerate(cards):
        for card2 in cards[i+1:]:
            if card_value(card1) == card_value(card2):
                score += 2
    
    # Runs
    sorted_values = sorted(values)
    for length in range(5, 2, -1):
        for i in range(len(sorted_values) - length + 1):
            run = sorted_values[i:i+length]
            if run == list(range(run[0], run[0] + length)):
                score += length
                break
    
    # Flush
    if len(set(suits)) == 1:
        if is_crib:
            score += 5  # Crib requires starter to match suit
        else:
            score += 4  # Hand flush doesn't require starter
    elif not is_crib and len(set(suits[:-1])) == 1:
        score += 4  # Four-card flush in hand
    
    # Nobs (Jack of same suit as starter)
    for card in hand:
        if card[0] == 11 and card[1] == starter[1]:
            score += 1
    
    return score

# Simulate all possible play sequences for given hands
def simulate_play(my_hand, opp_hand, starter):
    max_score = 0
    my_cards = list(my_hand)
    opp_cards = list(opp_hand)
    
    # Generate all possible play sequences (alternating)
    for my_order in itertools.permutations(my_cards, 4):
        for opp_order in itertools.permutations(opp_cards, 4):
            play_seq = []
            i, j = 0, 0
            total = 0
            while i < 4 or j < 4:
                # My turn
                if i < 4 and (j == 4 or total + card_value(my_order[i]) <= 31):
                    play_seq.append(my_order[i])
                    total += card_value(my_order[i])
                    i += 1
                # Opponent's turn
                elif j < 4 and (i == 4 or total + card_value(opp_order[j]) <= 31):
                    play_seq.append(opp_order[j])
                    total += card_value(opp_order[j])
                    j += 1
                else:
                    total = 0  # Reset count after a "go"
                    if i < 4 and j < 4:
                        continue
                    break
            if i == 4 and j == 4:  # Valid sequence uses all cards
                score = score_play_sequence(play_seq, is_dealer=True)
                max_score = max(max_score, score)
    
    return max_score

# Main function to evaluate kitties
def evaluate_kitties(my_hand_input, num_simulations):
    # Convert input cards to (value, suit) tuples
    try:
        my_hand = [(int(c[:-1]), c[-1].upper()) for c in my_hand_input.split()]
        if len(my_hand) != 6 or len(set(my_hand)) != 6:
            raise ValueError("Invalid hand: Must have exactly 6 unique cards")
    except:
        print("Error: Invalid card format. Use e.g., '5H 10D JC' (1-13 for A-K, S/H/D/C for suits)")
        return
    
    deck = create_deck()
    for card in my_hand:
        if card not in deck:
            print(f"Error: Invalid card {card}")
            return
        deck.remove(card)
    
    # Store results for each kitty
    kitty_scores = defaultdict(lambda: {'round1': [], 'round2': []})
    
    # Iterate over all possible kitties (choose 2 cards from 6)
    for kitty in itertools.combinations(my_hand, 2):
        my_remaining = [c for c in my_hand if c not in kitty]
        kitty = list(kitty)
        
        # Run simulations
        for _ in range(num_simulations):
            # Random starter card
            starter = random.choice(deck)
            # Random opponent hand (4 cards after discarding 2 from 6)
            opp_possible_cards = [c for c in deck if c != starter]
            opp_six = random.sample(opp_possible_cards, 6)
            opp_hand = random.sample(opp_six, 4)  # Opponent keeps 4 cards
            opp_crib_cards = [c for c in opp_six if c not in opp_hand]
            
            # Full crib (my 2 + opponent's 2)
            crib = kitty + opp_crib_cards
            
            # Round 1: Play phase (max score over all sequences)
            round1_score = simulate_play(my_remaining, opp_hand, starter)
            
            # Round 2: Show phase
            round2_score = score_hand(my_remaining, starter, is_crib=False)
            
            # Store scores
            kitty_scores[tuple(kitty)]['round1'].append(round1_score)
            kitty_scores[tuple(kitty)]['round2'].append(round2_score)
    
    # Calculate average scores and sort
    results = []
    for kitty, scores in kitty_scores.items():
        avg_round1 = sum(scores['round1']) / num_simulations
        avg_round2 = sum(scores['round2']) / num_simulations
        avg_total = avg_round1 + avg_round2
        results.append({
            'kitty': kitty,
            'avg_round1': avg_round1,
            'avg_round2': avg_round2,
            'avg_total': avg_total
        })
    
    # Sort by average total score (descending) and get top 5
    results.sort(key=lambda x: x['avg_total'], reverse=True)
    
    # Print top 5 kitties
    print("\nTop 5 kitties to discard:")
    for i, result in enumerate(results[:5], 1):
        kitty_str = ' '.join(f"{v}{s}" for v, s in result['kitty'])
        print(f"{i}. Kitty: {kitty_str}")
        print(f"   Avg Round 1 (Play): {result['avg_round1']:.2f}")
        print(f"   Avg Round 2 (Show): {result['avg_round2']:.2f}")
        print(f"   Avg Total Score: {result['avg_total']:.2f}\n")

# Example usage
if __name__ == "__main__":
    # Example input: "5H 5D 6C 7S 8H JD" (cards: 5H, 5D, 6C, 7S, 8H, Jack of Diamonds)
    hand_input = input("Enter your 6 cards (e.g., '5H 5D 6C 7S 8H JD'): ")
    num_sim = int(input("Enter number of simulations: "))
    evaluate_kitties(hand_input, num_sim)
