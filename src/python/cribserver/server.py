from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
import random
import uvicorn
from .cards import Card, Deck
from .cribbage import score_play_phase, score_show_phase, simulate_play_sequences

# Initialize FastAPI app
app = FastAPI(title="Cribbage Game Server")

# Pydantic models
class Player(BaseModel):
    player_id: str
    name: str
    hand: List[Card] = []
    score: int = 0
    discarded: List[Card] = []  # Track discarded cards for crib

class GameState(BaseModel):
    game_id: str
    players: List[Player]
    deck: List[Card]
    starter: Optional[Card] = None
    dealer: Optional[str] = None  # player_id of dealer
    current_turn: Optional[str] = None
    played_cards: List[Card] = []
    current_total: int = 0
    show_phase: bool = False
    crib: List[Card] = []  # Cards discarded to crib

class JoinRequest(BaseModel):
    player_id: str
    name: str

class PlayRequest(BaseModel):
    player_id: str
    card: Card

class DiscardRequest(BaseModel):
    player_id: str
    cards: List[Card]

class GoRequest(BaseModel):
    player_id: str
    
class SimulateRequest(BaseModel):
    player_id: str
    hand: List[Card]
    used_cards: List[Card]
    dealer: bool
    num_simulations: int = 576

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
            starter=None,
            dealer=None,
            current_turn=None,
            played_cards=[],
            current_total=0,
            show_phase=False,
            crib=[]
        )
    
    game = games[game_id]
    if len(game.players) >= 2:
        raise HTTPException(status_code=400, detail="Game full (2 players max)")
    if any(p.player_id == request.player_id for p in game.players):
        raise HTTPException(status_code=400, detail="Player already in game")
    
    game.players.append(Player(player_id=request.player_id, name=request.name))
    
    # Deal 6 cards to each player and set starter when 2 players join
    if len(game.players) == 2:
        random.shuffle(game.deck)  # Ensure deck is shuffled
        for player in game.players:
            player.hand = [game.deck.pop() for _ in range(6)]
        game.starter = game.deck.pop()
        game.dealer = game.players[0].player_id
        game.current_turn = game.players[1].player_id  # Non-dealer starts discard phase
    
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
    if game.show_phase:
        raise HTTPException(status_code=400, detail="Cannot discard in show phase")
    
    player = next((p for p in game.players if p.player_id == request.player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if len(request.cards) != 2:
        raise HTTPException(status_code=400, detail="Must discard exactly 2 cards")
    if any(card not in player.hand for card in request.cards):
        raise HTTPException(status_code=400, detail="Cards not in hand")
    
    # Move cards to crib
    for card in request.cards:
        player.hand.remove(card)
        player.discarded.append(card)
        game.crib.append(card)
    
    # Check if both players have discarded
    if all(len(p.discarded) == 2 for p in game.players):
        game.current_turn = next(p.player_id for p in game.players if p.player_id != game.dealer)  # Non-dealer (player 1) starts play phase
    
    return {"status": "discarded", "player_id": request.player_id}

@app.get("/games/{game_id}/state")
async def get_game_state(game_id: str):
    """Get current game state."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    return games[game_id]

@app.post("/games/{game_id}/play")
async def play_card(game_id: str, request: PlayRequest):
    """Play a card in the play phase."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    if game.show_phase:
        raise HTTPException(status_code=400, detail="In show phase, cannot play cards")
    if request.player_id != game.current_turn:
        raise HTTPException(status_code=400, detail="Not your turn")
    
    player = next((p for p in game.players if p.player_id == request.player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Convert request.card to Card object
    card = Card(**request.card.dict())  # Ensure it's a Card instance
    if card not in player.hand:
        raise HTTPException(status_code=400, detail="Card not in hand")
    if game.current_total + card.value() > 31:
        raise HTTPException(status_code=400, detail="Card exceeds 31")
    
    # Play card
    player.hand.remove(card)
    game.played_cards.append(card)
    game.current_total += card.value()
    player.score += score_play_phase(game.played_cards[:-1], card)
    
    # Check for Go
    next_player = game.players[(game.players.index(player) + 1) % 2]
    next_valid = any(c.value() + game.current_total <= 31 for c in next_player.hand)
    if not next_valid and not any(c.value() + game.current_total <= 31 for c in player.hand):
        player.score += 1  # Go point
        game.current_total = 0
        game.played_cards = []
    
    # Advance turn or move to show phase
    if not any(p.hand for p in game.players):
        game.show_phase = True
        # Score show phase
        for p in game.players:
            p.score += score_show_phase(p.hand, game.starter, is_crib=False)
        if game.dealer:
            dealer = next(p for p in game.players if p.player_id == game.dealer)
            dealer.score += score_show_phase(game.crib, game.starter, is_crib=True)
        # Determine winner
        winner = max(game.players, key=lambda p: p.score)
        player_stats[winner.player_id]["wins"] += 1
        saveV
        save_stats()
        # Reset game
        games[game_id] = GameState(
            game_id=game_id,
            players=[],
            deck=create_deck(),
            starter=None,
            dealer=None,
            current_turn=None,
            played_cards=[],
            current_total=0,
            show_phase=False,
            crib=[]
        )
        return {"status": "game_over", "winner": winner.player_id}
    
    game.current_turn = next_player.player_id if next_valid else player.player_id
    if game.current_total == 31:
        game.current_total = 0
        game.played_cards = []
    
    return {"status": "played", "card": card.dict()}  # Return card as dict to avoid serialization issues

@app.post("/games/{game_id}/go")
async def go(game_id: str, request: GoRequest):
    """Player passes (Go) when no cards can be played <= 31."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    if game.show_phase:
        raise HTTPException(status_code=400, detail="In show phase, cannot call Go")
    if request.player_id != game.current_turn:
        raise HTTPException(status_code=400, detail="Not your turn")
    
    player = next((p for p in game.players if p.player_id == request.player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Check if player has valid moves
    if any(c.value() + game.current_total <= 31 for c in player.hand):
        raise HTTPException(status_code=400, detail="You have playable cards")
    
    # Award Go point to opponent if they can play
    next_player = game.players[(game.players.index(player) + 1) % 2]
    next_valid = any(c.value() + game.current_total <= 31 for c in next_player.hand)
    if next_valid:
        next_player.score += 1  # Go point to opponent
        game.current_turn = next_player.player_id
    else:
        player.score += 1  # Go point if both cannot play
        game.current_total = 0
        game.played_cards = []
    
    # Check if play phase is over
    if not any(p.hand for p in game.players):
        game.show_phase = True
        for p in game.players:
            p.score += score_show_phase(p.hand, game.starter, is_crib=False)
        if game.dealer:
            dealer = next(p for p in game.players if p.player_id == game.dealer)
            dealer.score += score_show_phase(game.crib, game.starter, is_crib=True)
        winner = max(game.players, key=lambda p: p.score)
        player_stats[winner.player_id]["wins"] += 1
        save_stats()
        games[game_id] = GameState(
            game_id=game_id,
            players=[],
            deck=create_deck(),
            starter=None,
            dealer=None,
            current_turn=None,
            played_cards=[],
            current_total=0,
            show_phase=False,
            crib=[]
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

@app.post("/games/{game_id}/simulate")
async def simulate_discards(game_id: str, request: SimulateRequest):
    """Simulate discards and return top 5 kitties with average scores."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    if len(request.hand) != 6:
        raise HTTPException(status_code=400, detail="Hand must have 6 cards")
    
    game = games[game_id]
    results = simulate_play_sequences(
        hand=[Card(**c) for c in request.hand],  # Convert to Card objects
        starter=game.starter,
        used_cards=[Card(**c) for c in request.used_cards],
        dealer=request.dealer,
        num_simulations=request.num_simulations
    )
    return {
        "top_discards": [
            {
                "kitty": [card.dict() for card in kitty],  # Convert back to dict for JSON response
                "avg_play_score": play,
                "avg_show_score": show,
                "avg_crib_score": crib if request.dealer else None,
                "avg_total_score": total
            }
            for kitty, play, show, crib, total in results
        ]
    }

def run_server():
    """Run the FastAPI server with uvicorn."""
    uvicorn.run("cribserver.server:app", host="0.0.0.0", port=5000, reload=True)
    
