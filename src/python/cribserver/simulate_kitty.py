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

# Score a sequence of played cards (play phase, custom rule: pairs/runs from any combination)
def score_play_sequence(play_seq, is_dealer):
    my_score = 0
    opp_score = 0
    total = 0
    my_turns = range(0, 8, 2) if not is_dealer else range(1, 8, 2)
    played_cards = []
    value_counts = defaultdict(int)
    
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
        
        # Pairs, triplets, quads (any combination)
        if value_counts[current_value] == 2:
            if is_my_turn:
                my_score += 2
            else:
                opp_score += 2
        elif value_counts[current_value] == 3:
            if is_my_turn:
                my_score += 4  # Additional 4 for triplet
            else:
                opp_score += 4
        elif value_counts[current_value] == 4:
            if is_my_turn:
                my_score += 6  # Additional 6 for quad
            else:
                opp_score += 6
        
        # Runs (any combination of played cards)
        current_values = sorted([card_value(c) for c in played_cards])
        for length in range(3, min(len(played_cards) + 1, 6)):
            for subset in itertools.combinations(current_values, length):
                if max(subset) - min(subset) == length - 1 and len(set(subset)) == length:
                    if is_my_turn:
                        my_score += length
                    else:
                        opp_score += length
    
    return my_score

# Score a hand or crib in the show phase
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
        score += 5  # 5-card flush for hand or crib
    elif not is_crib and len(set(suits[:-1])) == 1:
        score += 4  # 4-card flush for hand only
    
    # Nobs (Jack of same suit as starter)
    for card in hand:
        if card[0] == 11 and card[1] == starter[1]:
            score += 1
    
    return score

# Simulate all possible play sequences
def simulate_play(my_hand, opp_hand, starter, is_dealer):
    max_score = 0
    my_cards = list(my_hand)
    opp_cards = list(opp_hand)
    
    for my_order in itertools.permutations(my_cards, 4):
        for opp_order in itertools.permutations(opp_cards, 4):
            play_seq = []
            i, j = 0, 0
            total = 0
            if is_dealer:
                while i < 4 or j < 4:
                    if j < 4 and (i == 4 or total + card_value(opp_order[j]) <= 31):
                        play_seq.append(opp_order[j])
                        total += card_value(opp_order[j])
                        j += 1
                    elif i < 4 and (j == 4 or total + card_value(my_order[i]) <= 31):
                        play_seq.append(my_order[i])
                        total += card_value(my_order[i])
                        i += 1
                    else:
                        total = 0
                        if i < 4 and j < 4:
                            continue
                        break
            else:
                while i < 4 or j < 4:
                    if i < 4 and (j == 4 or total + card_value(my_order[i]) <= 31):
                        play_seq.append(my_order[i])
                        total += card_value(my_order[i])
                        i += 1
                    elif j < 4 and (i == 4 or total + card_value(opp_order[j]) <= 31):
                        play_seq.append(opp_order[j])
                        total += card_value(opp_order[j])
                        j += 1
                    else:
                        total = 0
                        if i < 4 and j < 4:
                            continue
                        break
            if i == 4 and j == 4:
                score = score_play_sequence(play_seq, is_dealer)
                max_score = max(max_score, score)
    
    return max_score

# Main function to evaluate kitties
def evaluate_kitties(my_hand_input, num_simulations, is_dealer=False, used_cards_input=""):
    try:
        my_hand = [(int(c[:-1]), c[-1].upper()) for c in my_hand_input.split()]
        if len(my_hand) != 6 or len(set(my_hand)) != 6:
            raise ValueError("Invalid hand: Must have exactly 6 unique cards")
        
        # Parse used cards
        used_cards = []
        if used_cards_input.strip():
            used_cards = [(int(c[:-1]), c[-1].upper()) for c in used_cards_input.split()]
            if len(set(used_cards)) != len(used_cards):
                raise ValueError("Used cards must be unique")
        
        # Check for overlap between hand and used cards
        if any(card in used_cards for card in my_hand):
            raise ValueError("Hand cards cannot be in used cards")
    except:
        print("Error: Invalid card format. Use e.g., '5H 10D JC' (1-13 for A-K, S/H/D/C for suits)")
        return
    
    deck = create_deck()
    for card in my_hand + used_cards:
        if card not in deck:
            print(f"Error: Invalid card {card}")
            return
        deck.remove(card)
    
    if len(deck) < 7:  # Need at least 6 for opponent + 1 for starter
        print("Error: Not enough cards left in deck after removing hand and used cards")
        return
    
    kitty_scores = defaultdict(lambda: {'round1': [], 'round2': [], 'crib': []})
    
    for kitty in itertools.combinations(my_hand, 2):
        my_remaining = [c for c in my_hand if c not in kitty]
        kitty = list(kitty)
        
        for _ in range(num_simulations):
            starter = random.choice(deck)
            opp_possible_cards = [c for c in deck if c != starter]
            opp_six = random.sample(opp_possible_cards, min(6, len(opp_possible_cards)))
            opp_hand = random.sample(opp_six, min(4, len(opp_six)))
            opp_crib_cards = [c for c in opp_six if c not in opp_hand]
            crib = kitty + opp_crib_cards
            
            round1_score = simulate_play(my_remaining, opp_hand, starter, is_dealer)
            round2_score = score_hand(my_remaining, starter, is_crib=False)
            crib_score = score_hand(crib, starter, is_crib=True) if is_dealer else 0
            
            kitty_scores[tuple(kitty)]['round1'].append(round1_score)
            kitty_scores[tuple(kitty)]['round2'].append(round2_score)
            kitty_scores[tuple(kitty)]['crib'].append(crib_score)
    
    results = []
    for kitty, scores in kitty_scores.items():
        avg_round1 = sum(scores['round1']) / num_simulations
        avg_round2 = sum(scores['round2']) / num_simulations
        avg_crib = sum(scores['crib']) / num_simulations
        avg_total = avg_round1 + avg_round2 + (avg_crib if is_dealer else 0)
        results.append({
            'kitty': kitty,
            'avg_round1': avg_round1,
            'avg_round2': avg_round2,
            'avg_crib': avg_crib,
            'avg_total': avg_total
        })
    
    results.sort(key=lambda x: x['avg_total'], reverse=True)
    
    print("\nTop 5 kitties to discard:")
    for i, result in enumerate(results[:5], 1):
        kitty_str = ' '.join(f"{v}{s}" for v, s in result['kitty'])
        print(f"{i}. Kitty: {kitty_str}")
        print(f"   Avg Round 1 (Play): {result['avg_round1']:.2f}")
        print(f"   Avg Round 2 (Show): {result['avg_round2']:.2f}")
        if is_dealer:
            print(f"   Avg Kitty Score: {result['avg_crib']:.2f}")
        print(f"   Avg Total Score: {result['avg_total']:.2f}\n")

# Example usage
if __name__ == "__main__":
    hand_input = input("Enter your 6 cards (e.g., '5H 5D 6C 7S 8H JD'): ")
    num_sim = int(input("Enter number of simulations: "))
    is_dealer = input("Are you the dealer? (y/n): ").lower() == 'y'
    used_cards_input = input("Enter used cards (space-separated, or press Enter for none): ")
    evaluate_kitties(hand_input, num_sim, is_dealer, used_cards_input)
    
