from typing import List, Dict
import random

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


class Deck:
    REMAINING = "remaining"
    DISCARD = "discard"
    PROTECTED_PILE_NAMES = [REMAINING, DISCARD]
    
    def __init__(self):
        self.piles: Dict[str, List[int]] = {}
        self.reset()

    def reset(self) -> None:
        self.piles = {self.REMAINING: list(range(52)), self.DISCARD: []}
        random.shuffle(self.piles[self.REMAINING])

    def shuffle(self) -> None:
        all_cards = []
        for pile in self.piles.values():
            all_cards.extend(pile)
            pile.clear()
        self.piles[self.REMAINING] = all_cards
        random.shuffle(self.piles[self.REMAINING])
        if self.DISCARD not in self.piles:
            self.piles[self.DISCARD] = []

    def create_pile(self, name: str) -> None:
        if name in self.PROTECTED_PILE_NAMES:
            raise ValueError(f"{name} is a protected name")
        if name not in self.piles:
            self.piles[name] = []

    def deal_to_pile(self, name: str) -> None:
        if name not in self.piles:
            raise ValueError(f"Pile {name} does not exist")
        if not self.piles[self.REMAINING]:
            raise ValueError("No cards left in remaining pile")
        self.piles[name].append(self.piles[self.REMAINING].pop(0))

    def deal_to_piles(self, names: List[str], num_cards: int) -> None:
        for name in names:
            if name not in self.piles:
                raise ValueError(f"Pile {name} does not exist")
        if len(self.piles[self.REMAINING]) < len(names) * num_cards:
            raise ValueError("Not enough cards in remaining pile")
        for _ in range(num_cards):
            for name in names:
                self.piles[name].append(self.piles[self.REMAINING].pop(0))

    def play_card(self, card_idx: int, pile1: str, pile2: str) -> None:
        if pile1 not in self.piles or pile2 not in self.piles:
            raise ValueError("Source or destination pile does not exist")
        if card_idx not in self.piles[pile1]:
            raise ValueError(f"Card {card_idx} not in pile {pile1}")
        self.piles[pile1].remove(card_idx)
        self.piles[pile2].append(card_idx)

    def get_cards(self, name: str) -> List[int]:
        if name not in self.piles:
            raise ValueError(f"Pile {name} does not exist")
        return self.piles[name].copy()

