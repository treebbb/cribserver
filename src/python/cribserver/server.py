from fastapi import FastAPI, HTTPException
from typing import List, Dict, Optional
import json
import os
import random
import uvicorn
from .cards import Card, Deck
from .cribbage import score_play_phase, score_show_phase, deal_to_players
from .api_model import Player, GameState, GameListItem, PlayerState, JoinRequest, PlayRequest, DiscardRequest, GoRequest, CribbagePhase

# Initialize FastAPI app
app = FastAPI(title="Cribbage Game Server")
    
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
@app.get("/games/", response_model=List[GameListItem])
async def list_games():
    """List all available games."""
    result = []
    for game in games:
        item = GameListItem.from_game_state(game)
        result.append(item)
    return result

@app.post("/games/{game_id}/join", response_model=PlayerState)
async def join_game(game_id: str, request: JoinRequest):
    """Join a Cribbage game (2 players) and deal cards when full."""
    if game_id not in games:
        games[game_id] = GameState(
            game_id=game_id,
            players=[],
            deck=Deck(),
            dealer=None,
            current_turn=None,
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
        game.change_phase(CribbagePhase.DEAL)
        deal_to_players(game.deck, game.players[0].player_id, game.players[1].player_id)
        game.dealer = game.players[0].player_id
        game.current_turn = game.players[1].player_id  # Non-dealer starts discard phase
        game.change_phase(CribbagePhase.DISCARD)
    
    # Update player stats
    if request.player_id not in player_stats:
        player_stats[request.player_id] = {"name": request.name, "wins": 0, "games_played": 1}
    else:
        player_stats[request.player_id]["games_played"] += 1
    save_stats()
    
    return PlayerState.from_game_state(game, request.player_id)

@app.get("/games/{game_id}/{player_id}/state")
async def get_game_state(game_id: str, player_id: str):
    """Get current game state."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    game = games[game_id]
    return PlayerState.from_game_state(game, player_id)


@app.post("/games/{game_id}/discard", response_model=PlayerState)
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
        game.change_phase(CribbagePhase.FLIP_STARTER)
        deck.deal_to_pile("starter")
        # Non-dealer (player 1) starts play phase        
        game.current_turn = next(p.player_id for p in game.players if p.player_id != game.dealer)
        game.change_phase(CribbagePhase.COUNT)
    return PlayerState.from_game_state(game, player.player_id)

@app.post("/games/{game_id}/play")
async def play_card(game_id: str, request: PlayRequest, response_model=PlayerState):
    """Play a card in the count phase."""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    deck = game.deck
    if game.phase != CribbagePhase.COUNT:
        print("1")
        raise HTTPException(status_code=400, detail="In show phase, cannot play cards")
    if request.player_id != game.current_turn:
        print("2")
        raise HTTPException(status_code=400, detail="Not your turn")
    
    player = next((p for p in game.players if p.player_id == request.player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Convert request.card to Card object
    card_idx = request.card_idx
    if card_idx not in deck.get_cards(request.player_id):
        print("3")
        raise HTTPException(status_code=400, detail="Card not in hand")
    if game.phase1_total() + Card.get_value(card_idx) > 31:
        print("4")
        raise HTTPException(status_code=400, detail="Card exceeds 31")
    
    # Play card
    deck.play_card(card_idx, request.player_id, "phase1")
    game.played_cards.append((request.player_id, card_idx))
    player.score += score_play_phase(deck.get_cards("phase1"), score_log=game.append_log(player))
    
    # Check for Go
    next_player = game.players[(game.players.index(player) + 1) % 2]
    next_valid = any(Card.get_value(c) + game.phase1_total() <= 31 for c in deck.get_cards(next_player.player_id))
    cur_valid = any(Card.get_value(c) + game.phase1_total() <= 31 for c in deck.get_cards(player.player_id))
    if next_valid:
        game.current_turn = next_player.player_id
    else:
        # opponent doesn't have any cards < 31. keep playing with the current player
        if cur_valid:
            # current player has more cards < 31. Let him continue playing
            game.current_turn = player.player_id
        else:
            # current player doesn't have cards < 31 either. finish this round. Next player starts
            game.game_log.append(f"{player.name} 1 point for Go")
            if game.phase1_total() != 31:
                # Go point. Don't double count if 31
                player.score += 1
            game.current_turn = next_player.player_id
            deck.drain_pile("phase1")
        
    
    # Advance turn or move to show phase
    if not any(deck.get_cards(p.player_id) for p in game.players):
        game.change_phase(CribbagePhase.SHOW)
        # Score show phase
        for p in reversed(game.players): # second player counts first
        # move cards back into player's hands and score
            hand = []
            for player_id, card_idx in game.played_cards:
                if p.player_id == player_id:
                    hand.append(card_idx)
            p.score += score_show_phase(hand, deck.get_cards("starter")[0], is_crib=False, score_log=game.append_log(p))
        # move to CRIB phase
        game.change_phase(CribbagePhase.CRIB)
        if game.dealer:
            dealer = next(p for p in game.players if p.player_id == game.dealer)
            dealer.score += score_show_phase(deck.get_cards("crib"), deck.get_cards("starter")[0], is_crib=True, score_log=game.append_log(dealer))
        # Determine winner
        winner = max(game.players, key=lambda p: p.score)
        player_stats[winner.player_id]["wins"] += 1
        save_stats()
        # Reset game
        game.change_phase(CribbagePhase.DONE)
        return PlayerState.from_game_state(game, request.player_id)
    
    return PlayerState.from_game_state(game, request.player_id)

@app.get("/players/{player_id}/stats")
async def get_player_stats(player_id: str):
    """Get player stats."""
    if player_id not in player_stats:
        raise HTTPException(status_code=404, detail="Player not found")
    return player_stats[player_id]

def run_server():
    """Run the FastAPI server with uvicorn."""
    uvicorn.run("cribserver.server:app", host="0.0.0.0", port=5000, reload=True)
    
