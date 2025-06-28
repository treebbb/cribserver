from pydantic import BaseModel
from enum import Enum
from typing import List
import random

class Suit(str, Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

    @classmethod
    def to_display(cls, suit: str) -> str:
        """Convert suit to display symbol."""
        return {
            cls.HEARTS: "♥",
            cls.DIAMONDS: "♦",
            cls.CLUBS: "♣",
            cls.SPADES: "♠"
        }[suit]

class Rank(str, Enum):
    ACE = "ace"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "jack"
    QUEEN = "queen"
    KING = "king"

    @classmethod
    def to_display(cls, rank: str) -> str:
        """Convert rank to display character."""
        return {
            cls.ACE: "A",
            cls.TEN: "T",
            cls.JACK: "J",
            cls.QUEEN: "Q",
            cls.KING: "K"
        }.get(rank, rank)

class Card(BaseModel):
    suit: Suit
    rank: Rank

    def value(self) -> int:
        """Return numeric value of card for scoring (Ace=1, 2-10=face value, J/Q/K=10)."""
        if self.rank == Rank.ACE:
            return 1
        elif self.rank in [Rank.JACK, Rank.QUEEN, Rank.KING]:
            return 10
        return int(self.rank)

    def to_display(self) -> str:
        """Return card as two-character display string (e.g., 'A♥')."""
        return f"{Rank.to_display(self.rank)}{Suit.to_display(self.suit)}"

def create_deck() -> List[Card]:
    """Create and shuffle a standard 52-card deck."""
    deck = [
        Card(suit=suit, rank=rank)
        for suit in Suit
        for rank in Rank
    ]
    random.shuffle(deck)
    return deck
