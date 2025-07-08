from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Callable, Tuple
from .cards import Card, Deck


class CribbagePhase(Enum):
    # wait for both players to join
    JOIN = 1
    # deal 6 cards to each player
    DEAL = 2
    # both players add 2 cards to the Crib
    DISCARD = 3
    # Flip the starter card (transition to COUNT)
    FLIP_STARTER = 4
    # players alternate playing cards and getting points
    COUNT = 5
    # players each count points in their hand, dealer counts second
    SHOW = 6
    # dealer counts points in the crib
    CRIB = 7
    # game has ended.
    DONE = 8


class LogType(Enum):
    # logs that don't go to PlayerState
    PRIVATE = 1
    # logs that do go to PlayerState
    PUBLIC = 2
    JOIN = 3
    DEAL = 4
    DISCARD = 5
    PLAY = 6


# Pydantic models
class Player(BaseModel):
    player_id: str
    name: str
    score: int = 0

class GameState:
    # unique ID for the game
    game_id: str
    # 2 players
    players: List[Player]
    # 52 cards
    deck: Deck
    # played cards to restore for SHOW phase after COUNT
    played_cards: List[Tuple[str, int]]
    # first player to join is the dealer
    dealer: Optional[str] = None  # player_id of dealer
    # turn during the COUNT phase. Alternate.
    current_turn: Optional[str] = None
    # current phase of the game
    phase: CribbagePhase
    # messages for each game phase change and each time points are score
    game_log: List[Tuple[LogType, str]]

    def phase1_total(self):
        return sum([Card.get_value(c) for c in self.deck.get_cards("phase1")])

    def log_action(self, action_type: LogType, player_id: str, subject: str):
        log_message = f"{action_type.name},{player_id},{subject}"
        self.game_log.append((LogType.PRIVATE, log_message))

    def append_log(self, player: Player) -> Callable[[str], None]:
        '''
        returns a method to append messages to game log
        '''
        game = self
        class LogAppender:
            def append(self, msg: str) -> None:
                game.game_log.append((LogType.PUBLIC, f"{player.name} {msg}"))
        return LogAppender()

    def change_phase(self, new_phase: CribbagePhase) -> None:
        self.phase = new_phase
        self.game_log.append((LogType.PUBLIC, f"game.phase -> {new_phase.name}"))

    def __init__(self, **kw):
        self.game_log = []
        self.played_cards = []
        self.__dict__.update(kw)

class GameListItem(BaseModel):
    game_id: str
    player_count: int
    phase: CribbagePhase

    @classmethod
    def from_game_state(cls, game):
        return GameListItem(
            game_id=game.game_id,
            player_count=len(game.players),
            phase=game.phase
            )

class PlayerState(BaseModel):
    game_id: str
    players: List[Player]
    visible_piles: Optional[Dict[str, List[int]]] = None
    is_dealer: bool = None
    my_turn: bool
    phase: CribbagePhase
    game_log: List[str] = Field(default_factory=list)

    @classmethod
    def from_game_state(cls, game, player_id):
        deck = game.deck
        visible_piles = {}
        deck.copy_existing_piles(("starter", "phase1", player_id), visible_piles)
        #print(f"from_game_state: len(players)={len(game.players)}  phase={game.phase.name}")
        result = cls(
            game_id = game.game_id,
            players = game.players.copy(),
            is_dealer = game.dealer == player_id,
            my_turn = (game.current_turn is not None and game.current_turn == player_id),
            phase = game.phase,
            visible_piles = visible_piles,
            game_log = [s for (t, s) in game.game_log if t == LogType.PUBLIC]
            )
        return result

class JoinRequest(BaseModel):
    player_id: str
    name: str

class PlayRequest(BaseModel):
    player_id: str
    card_idx: int

class DiscardRequest(BaseModel):
    player_id: str
    card_indices: List[int]

class GoRequest(BaseModel):
    player_id: str
