from typing import List, Dict
import random

class Card:
    SUITS = ["Clubs", "Diamonds", "Hearts", "Spades"]
    SUIT_CHARS = [s[0] for s in SUITS]
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    JACK_RANK = 11

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
    def get_value(card_index: int) -> int:
        rank = (card_index % 13) + 1
        return min(rank, 10)
    
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
    '''
    now implement a Deck of 52 cards. A deck should have state:1 or more named "piles".
    These piles are ordered lists of cards, representing remaining cards, player hands, discarded cards, or cards in play in the  area share by players.
    
    Deck should have the following methods"card" or "cards" below means the card_idx (0 to 51) unless otherwise stated.
    reset(): the original state of the deck is: all 52 cards are in the "remaining" pile. order of cards in remaining pile is randomized. an empty "discard" pile is created.
    shuffle(): all cards are moved to the "remaining" pile. order of cards is randomized. "discard" pile and any other piles are empty. does not remove any created piles, just empties them.
    create_pile(name): creates a named pile.
    deal_to_pile(name): removes the top card from the "remaining" pile and moves it to the named pile.
    deal_to_piles(list_of_names, num_cards): deals from top of pile to each pile in the given list. e.g. if list_of_names=["A", "B"] and num_cards=3, then cards will be dealt to A,B,A,B,A,B
    play_card(card_idx, pile1, pile2): moves card from pile1 to pile2
    get_cards(name): returns a list of all cards in that named pile
    drain_pile(pile_name): Moves all cards from the named pile to the "discard" pile.
    '''
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

    def drain_pile(self, pile_name):
        '''
        move all cards in pile to the discard pile
        '''
        self.piles[self.DISCARD].extend(self.piles[pile_name])
        self.piles[pile_name].clear()

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

    def copy_existing_piles(self, pile_names: List[str], dest_piles: Dict):
        '''
        copy piles if they exist. If not, ignore
        '''
        for pile_name in pile_names:
            if pile_name in self.piles:
                dest_piles[pile_name] = self.piles[pile_name].copy()
