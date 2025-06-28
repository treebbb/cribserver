from cribserver.cards import Card


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

if __name__ == "__main__":
    test_card()
