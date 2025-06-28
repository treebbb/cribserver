class Card:
    SUITS = ["Clubs", "Diamonds", "Hearts", "Spades"]
    SUIT_CHARS = [s[0] for s in SUITS]
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

    @staticmethod
    def get_rank(card_index: int) -> int:
        return (card_index % 13) + 1

    @staticmethod
    def get_rank_string(card_index: int) -> str:
        return Card.RANKS[card_index % 13]

    @staticmethod
    def get_suit(card_index: int) -> int:
        return card_index // 13

    @staticmethod
    def get_suit_string(card_index: int) -> str:
        '''
        => Clubs, Diamonds, etc.
        '''
        return Card.SUITS[card_index // 13]
    @staticmethod

    def get_suit_char(card_index: int) -> str:
        '''
        => 'C', 'D', etc
        '''
        return Card.SUIT_CHARS[card_index // 13]

    @staticmethod
    def to_string(card_index: int) -> str:
        rank = Card.get_rank_string(card_index)
        suit_char = Card.get_suit_char(card_index)
        retval = rank + suit_char
        if len(retval) == 2:
            retval = ' ' + retval
        return retval

    @staticmethod
    def from_string(card_str: str) -> int:
        card_str = card_str.strip()
        if len(card_str) not in (2, 3):
            raise ValueError("invalid length. must be 2-3 chars")
        rank_str = card_str[:-1]
        try:
            rank_idx = next(i for i, s in enumerate(Card.RANKS) if s == rank_str)
        except:
            raise ValueError(f"invalid rank")
        suit_char = card_str[-1]
        try:
            suit_idx = next(i for i, s in enumerate(Card.SUIT_CHARS) if s == suit_char)
        except:
            raise ValueError("invalid suit")
        return suit_idx * 13 + rank_idx
