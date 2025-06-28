from pydantic import BaseModel
from enum import Enum
from typing import List
import random

class Suit(str, Enum):
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

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

class Card(BaseModel):
    suit: Suit
    rank: Rank

def create_deck() -> List[Card]:
    """Create and shuffle a standard 52-card deck."""
    deck = [
        Card(suit=suit, rank=rank)
        for suit in Suit
        for rank in Rank
    ]
    random.shuffle(deck)
    return deck
