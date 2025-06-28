from cribserver.cards import Card, Deck


def test_card():
    # Test rank and suit
    assert Card.get_rank(0) == 1 and Card.get_suit(0) == 0
    assert Card.get_rank(12) == 13 and Card.get_suit(12) == 0
    assert Card.get_rank(13) == 1 and Card.get_suit(13) == 1
    assert Card.get_rank(51) == 13 and Card.get_suit(51) == 3

    # Test string methods
    assert Card.get_rank_string(0) == "A" and Card.get_suit_string(0) == "Clubs"
    assert Card.get_rank_string(12) == "K" and Card.get_suit_string(12) == "Clubs"
    assert Card.get_rank_string(13) == "A" and Card.get_suit_string(13) == "Diamonds"
    assert Card.get_rank_string(51) == "K" and Card.get_suit_string(51) == "Spades"

    # Test to_string
    assert Card.to_string(0) == " AC"
    assert Card.to_string(12) == " KC"
    assert Card.to_string(13) == " AD"
    assert Card.to_string(51) == " KS"

    # Test from_string
    assert Card.from_string(" AC") == 0
    assert Card.from_string(" KC") == 12
    assert Card.from_string(" AD") == 13
    assert Card.from_string(" KS") == 51

    # Test invalid inputs
    try:
        Card.from_string("XXXX")
        assert False, "Should raise ValueError for invalid length"
    except ValueError as e:
        assert str(e) == "invalid length. must be 2-3 chars"
    
    try:
        Card.from_string(" XZ")
        assert False, "Should raise ValueError for invalid rank"
    except ValueError as e:
        assert str(e) == "invalid rank"
    
    try:
        Card.from_string(" AX")
        assert False, "Should raise ValueError for invalid suit"
    except ValueError as e:
        assert str(e) == "invalid suit"

    # Test round-trip
    for i in range(52):
        assert Card.from_string(Card.to_string(i)) == i

    print("All tests passed!")


def test_deck():
    deck = Deck()

    # Test reset
    assert len(deck.piles[Deck.REMAINING]) == 52
    assert len(deck.piles[Deck.DISCARD]) == 0
    assert set(deck.piles[Deck.REMAINING]) == set(range(52))

    # Test create_pile and deal_to_pile
    deck.create_pile("player1")
    deck.deal_to_pile("player1")
    assert len(deck.piles[Deck.REMAINING]) == 51
    assert len(deck.piles["player1"]) == 1

    # Test deal_to_piles
    deck.reset()
    deck.create_pile("player1")
    deck.create_pile("player2")
    deck.deal_to_piles(["player1", "player2"], 3)
    assert len(deck.piles[Deck.REMAINING]) == 46
    assert len(deck.piles["player1"]) == 3
    assert len(deck.piles["player2"]) == 3

    # Test play_card
    card = deck.piles["player1"][0]
    deck.play_card(card, "player1", Deck.DISCARD)
    assert len(deck.piles["player1"]) == 2
    assert len(deck.piles[Deck.DISCARD]) == 1
    assert deck.piles[Deck.DISCARD][0] == card

    # Test shuffle
    deck.create_pile("temp")
    deck.deal_to_pile("temp")
    deck.deal_to_pile(Deck.DISCARD)
    deck.shuffle()
    assert len(deck.piles[Deck.REMAINING]) == 52
    assert len(deck.piles[Deck.DISCARD]) == 0
    assert len(deck.piles["temp"]) == 0
    assert set(deck.piles[Deck.REMAINING]) == set(range(52))

    # Test get_cards
    deck.reset()
    deck.create_pile("player1")
    deck.deal_to_pile("player1")
    player_cards = deck.get_cards("player1")
    assert len(player_cards) == 1
    assert player_cards[0] in range(52)

    # Test error cases
    try:
        deck.deal_to_pile("nonexistent")
        assert False, "Should raise ValueError for nonexistent pile"
    except ValueError as e:
        assert str(e) == "Pile nonexistent does not exist"

    try:
        deck.play_card(0, "nonexistent", Deck.DISCARD)
        assert False, "Should raise ValueError for nonexistent pile"
    except ValueError as e:
        assert str(e) == "Source or destination pile does not exist"

    print("All deck tests passed!")

if __name__ == "__main__":
    test_deck()

if __name__ == "__main__":
    test_card()
