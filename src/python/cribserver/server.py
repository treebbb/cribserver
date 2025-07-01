from enum import Enum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
import random
import uvicorn
from .cards import Card, Deck
from .cribbage import score_play_phase, score_show_phase

# Initialize FastAPI app
app = FastAPI(title="Cribbage Game Server")

class CribbagePhase(Enum):
    JOIN = 1
    DEAL = 2
    DISCARD = 3
    FLIP_STARTER = 4
    COUNT = 5
    SHOW = 6
    CRIB = 7

# Pydantic models
class Player(BaseModel):
    player_id: str
    name: str
    score: int = 0

class GameState:
    game_id: str
    players: List[Player]
    deck: Deck
    dealer: Optional[str] = None  # player_id of dealer
    current_turn: Optional[str] = None
    current_total: int = 0
    phase: CribbagePhase

class PlayerState(BaseModel):
    game_id: str
    players: List[Player]
    visible_piles: Optional[Dict[str, List[int]]] = None
    dealer: Optional[str] = None
    current_turn: Optional[str] = None
    current_total: int = 0
    phase: CribbagePhase

    @classmethod
    def from_game_state(cls, game, player_id):
        deck = game.deck
        visible_piles = {
            pile_name: game.deck.get_cards(pile_name)
            for pile_name in ("starter", player_id)
            if game.deck.get_cards(pile_name) is not None
        } if game.deck.get_cards("starter") or game.deck.get_cards(player_id) else None        
        result = cls(
            game_id = game.game_id,
            players = game.players.copy(),
            dealer = game.dealer,
            current_turn = game.current_turn,
            current_total = game.current_total,
            phase = game.phase,
            visible_piles = visible_piles
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
    
# In-memory game state
games: Dict[str, GameState] = {}
player_stats: Dict[str, Dict] = {}
STATS_FILE = "player_stats.json"

# Load/save stats
def load_stats():
    global player_stats
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            player_stats = json.load(f)

def save_stats():
    with open(STATS_FILE, "w") as f:
        json.dump(player_stats, f, indent=2)

load_stats()

# API Endpoints
@app.get("/games")
async def list_games():
    """List all available games."""
    return {"games": list(games.keys())}

@app.post("/games/{game_id}/join")
async def join_game(game_id: str, request: JoinRequest):
    """Join a Cribbage game (2 players) and deal cards when full."""
    if game_id not in games:
        games[game_id] = GameState(
            game_id=game_id,
            players=[],
            deck=Deck(),
            dealer=None,
            current_turn=None,
            current_total=0,
            phase=CribbagePhase.JOIN,
        )
    
    game = games[game_id]
    if len(game.players) >= 2:
        raise HTTPException(status_code=400, detail="Game full (2 players max)")
    if any(p.player_id == request.player_id for p in game.players):
        raise HTTPException(status_code=400, detail="Player already in game")
    
    game.players.append(Player(player_id=request.player_id, name=request.name))

    
    # Deal 6 cards to each player and set starter when 2 players join    
    if len(game.players) == 2:
        # initialize game and deck
        game.phase = CribbagePhase.DEAL
        deck = game.deck
        deck.create_pile("starter")
        deck.create_pile("crib")
        deck.create_pile("phase1")
        deck.shuffle()
        for player in game.players:
            deck.create_pile(player.player_id)
        deck.deal_to_piles([p.player_id for p in game.players], 6)
        game.dealer = game.players[0].player_id
        game.current_turn = game.players[1].player_id  # Non-dealer starts discard phase
        game.phase = CribbagePhase.DISCARD
    
    # Update player stats
    if request.player_id not in player_stats:
        player_stats[request.player_id] = {"name": request.name, "wins": 0, "games_played": 1}
    else:
        player_stats[request.player_id]["games_played"] += 1
    save_stats()
    
    return {"status": "joined", "game_id": game_id, "player_count": len(game.players)}

@app.post("/games/{game_id}/discard")
async def discard_cards(game_id: str, request: DiscardRequest):
    """Discard 2 cards to the crib."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    deck = game.deck
    if game.phase != CribbagePhase.DISCARD:
        raise HTTPException(status_code=400, detail="Can only discard in DISCARD phase")
    
    player = next((p for p in game.players if p.player_id == request.player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if len(request.card_indices) != 2:
        raise HTTPException(status_code=400, detail="Must discard exactly 2 cards")
    if any(card not in deck.get_cards(player.player_id) for card in request.card_indices):
        raise HTTPException(status_code=400, detail="Cards not in hand")
    
    # Move cards to crib
    for card_idx in request.card_indices:
        deck.play_card(card_idx, player.player_id, "crib")
    
    # Check if both players have discarded
    if len(deck.get_cards("crib")) == 4:
        # flip starter card
        deck.deal_to_pile("starter")
        # Non-dealer (player 1) starts play phase        
        game.current_turn = next(p.player_id for p in game.players if p.player_id != game.dealer)
    return {"status": "discarded", "player_id": request.player_id}

@app.get("/games/{game_id}/{player_id}/state")
async def get_game_state(game_id: str, player_id: str):
    """Get current game state."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    game = games[game_id]
    return PlayerState.from_game_state(game, player_id)

@app.post("/games/{game_id}/play")
async def play_card(game_id: str, request: PlayRequest):
    """Play a card in the play phase."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    deck = game.deck
    if game.phase != CribbagePhase.COUNT:
        raise HTTPException(status_code=400, detail="In show phase, cannot play cards")
    if request.player_id != game.current_turn:
        raise HTTPException(status_code=400, detail="Not your turn")
    
    player = next((p for p in game.players if p.player_id == request.player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Convert request.card to Card object
    card_idx = request.card_idx
    if card_idx not in deck.get_cards(request.player_id):
        raise HTTPException(status_code=400, detail="Card not in hand")
    if game.current_total + card.value() > 31:
        raise HTTPException(status_code=400, detail="Card exceeds 31")
    
    # Play card
    deck.play_card(card_idx, request.player_id, "phase1")
    game.current_total += Card.value(card_idx)
    player.score += score_play_phase(deck.get_cards("phase1"))
    
    # Check for Go
    next_player = game.players[(game.players.index(player) + 1) % 2]
    next_valid = any(c.value() + game.current_total <= 31 for c in deck.get_cards(next_player.player_id))
    if not next_valid and not any(c.value() + game.current_total <= 31 for c in deck.get_cards(player.player_id)):
        player.score += 1  # Go point
        game.current_total = 0
        deck.drain_pile("phase1")
    
    # Advance turn or move to show phase
    if not any(deck.get_cards(p.player_id) for p in game.players):
        game.phase = CribbagePhase.SHOW
        # Score show phase
        for p in game.players:
            p.score += score_show_phase(deck.get_cards(p.player_id), deck.get_cards("starter")[0], is_crib=False)
        if game.dealer:
            dealer = next(p for p in game.players if p.player_id == game.dealer)
            dealer.score += score_show_phase(deck.get_cards("crib"), deck.get_cards("starter")[0], is_crib=True)
        # Determine winner
        winner = max(game.players, key=lambda p: p.score)
        player_stats[winner.player_id]["wins"] += 1
        save_stats()
        # Reset game
        games[game_id] = GameState(
            game_id=game_id,
            players=[],
            deck=Deck(),
            dealer=None,
            current_turn=None,
            current_total=0,
            phase=CribbagePhase.DISCARD,
        )
        return {"status": "game_over", "winner": winner.player_id}
    
    game.current_turn = next_player.player_id if next_valid else player.player_id
    if game.current_total == 31:
        game.current_total = 0
        deck.drain_pile("phase1")
    
    return {"status": "played", "card": card_idx}

@app.post("/games/{game_id}/go")
async def go(game_id: str, request: GoRequest):
    """Player passes (Go) when no cards can be played <= 31."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    deck = game.deck
    if game.phase != CribbagePhase.COUNT:
        raise HTTPException(status_code=400, detail="Cannot call Go outside COUNT phase")
    if request.player_id != game.current_turn:
        raise HTTPException(status_code=400, detail="Not your turn")
    
    player = next((p for p in game.players if p.player_id == request.player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Check if player has valid moves
    if any(Card.value(c) + game.current_total <= 31 for c in deck.get_cards(player.player_id)):
        raise HTTPException(status_code=400, detail="You have playable cards")
    
    # Award Go point to opponent if they can play
    next_player = game.players[(game.players.index(player) + 1) % 2]
    next_valid = any(Card.value(c) + game.current_total <= 31 for c in deck.get_cards(next_player.player_id))
    if next_valid:
        next_player.score += 1  # Go point to opponent
        game.current_turn = next_player.player_id
    else:
        player.score += 1  # Go point if both cannot play
        game.current_total = 0
        deck.drain_pile("phase1")
    
    # Check if play phase is over
    if not any(get_cards(p.player_id) for p in game.players):
        game.phase = CribbagePhase.SHOW
        for p in game.players:
            p.score += score_show_phase(deck.get_cards(p.player_id), deck.get_cards("starter")[0], is_crib=False)
        if game.dealer:
            dealer = next(p for p in game.players if p.player_id == game.dealer)
            dealer.score += score_show_phase(deck.get_cards("crib"), deck.get_cards("starter")[0], is_crib=True)
        winner = max(game.players, key=lambda p: p.score)
        player_stats[winner.player_id]["wins"] += 1
        save_stats()
        games[game_id] = GameState(
            game_id=game_id,
            players=[],
            deck=Deck(),
            dealer=None,
            current_turn=None,
            current_total=0,
        )
        return {"status": "game_over", "winner": winner.player_id}
    
    return {"status": "go", "player_id": request.player_id}

@app.get("/games/{game_id}/score")
async def get_scores(game_id: str):
    """Get current scores."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    return {p.player_id: p.score for p in games[game_id].players}

@app.get("/players/{player_id}/stats")
async def get_player_stats(player_id: str):
    """Get player stats."""
    if player_id not in player_stats:
        raise HTTPException(status_code=404, detail="Player not found")
    return player_stats[player_id]

def run_server():
    """Run the FastAPI server with uvicorn."""
    uvicorn.run("cribserver.server:app", host="0.0.0.0", port=5000, reload=True)
    
