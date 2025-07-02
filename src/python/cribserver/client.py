import curses
import requests
import time
import json
from typing import List, Optional
import threading
import sys
from .cards import Card
from .api_model import Player, GameState, GameListItem, PlayerState, JoinRequest, PlayRequest, DiscardRequest, GoRequest, CribbagePhase


# In src/python/cribserver/client.py

GAME_ID = "FIRST_GAME"

def display_pile(card_indices):
    return ' '.join(Card.to_string(card_idx) for card_idx in card_indices)

class CribbageClient:
    def __init__(self, stdscr, server_url: str, player_id: str, player_name: str, game_id: str):
        self.stdscr = stdscr
        self.server_url = server_url.rstrip('/')
        self.player_id = player_id
        self.player_name = player_name
        self.game_id = GAME_ID
        self.player_state = PlayerState(
            game_id=GAME_ID,
            players=[],
            visible_piles={},
            is_dealer=False,
            my_turn=False,
            phase=CribbagePhase.JOIN,
            )
            
            
        self.message = "Joining game..."
        self.input_buffer = ""
        self.running = True
        self.join_game()

        # Set up curses
        curses.curs_set(0)  # Hide cursor
        curses.start_color()
        curses.use_default_colors()  # Use terminal's default colors
        curses.init_color(0, 0, 0, 0)  # overrides Terminal palette for background. (background, R,G,B)        
        self.stdscr.bkgd(' ', curses.color_pair(0))  # Set background to black
        curses.init_pair(1, curses.COLOR_RED, -1)    # Hearts/Diamonds (red on default bg)
        curses.init_pair(2, curses.COLOR_BLACK, -1)  # Clubs/Spades (black on default bg)
        curses.init_pair(3, curses.COLOR_GREEN, -1)  # Messages (green on default bg)
        self.stdscr.timeout(100)  # Non-blocking input

        # Start polling thread
        self.polling_thread = threading.Thread(target=self.poll_state, daemon=True)
        self.polling_thread.start()

    def get_me(self):
        if self.player_state is None or self.player_state.players is None:
            return None
        me = next((p for p in self.player_state.players if p.player_id == self.player_id), None)
        return me
    
    def get_opponent(self):
        if self.player_state is None or self.player_state.players is None:
            return None
        opponent = next((p for p in self.player_state.players if p.player_id != self.player_id), None)
        return opponent

    def get_my_hand(self):
        if self.player_state is None or self.player_state.players is None:
            return []
        return self.player_state.visible_piles.get(self.player_id, [])

    def phase1_pile_total(self):
        if self.player_state.phase != CribbagePhase.COUNT:
            return 0
        card_indices = self.player_state.visible_piles.get("phase1", [])
        return sum(Card.get_value(c) for c in card_indices)

    def join_game(self):
        """Join the game on the server."""
        try:
            request=JoinRequest(
                player_id=self.player_id,
                name=self.player_name,
                )
            response = requests.post(
                f"{self.server_url}/games/{self.game_id}/join",
                json=request.dict(),
            )
            response.raise_for_status()
            self.player_state = PlayerState(**response.json())
            self.message = f"Joined game! Players: {len(self.player_state.players)}"
            if self.player_state.phase == CribbagePhase.DISCARD:
                self.message += " Game started, check your hand."
        except requests.RequestException as e:
            self.message = f"Error joining game: {str(e)}"

    def poll_state(self):
        """Poll server for player state."""
        while self.running:
            try:
                # Get game state
                response = requests.get(f"{self.server_url}/games/{self.game_id}/{self.player_id}/state")
                response.raise_for_status()
                response_dict = response.json()
                self.player_state = PlayerState(**response_dict)
                json.dump(response_dict, open('x.json', 'w'))
            except requests.RequestException as e:
                self.message = f"Server error: {str(e)}"
            time.sleep(5)

    def discard_cards(self, card_idx1: int, card_idx2: int):
        """Send discard request to server."""
        if self.player_state.phase != CribbagePhase.DISCARD:
            self.message = "Game phase is not DISCARD"
            return
        me = self.get_me()
        if not me:
            self.message = "You're not in the game"
            return
        if card_idx1 < 0 or card_idx2 > 51 or card_idx2 < 0 or card_idx2 > 51:
            self.message = "Invalid card selection"
            return
        mypile = self.player_state.visible_piles[self.player_id]
        if card_idx1 not in mypile or card_idx2 not in mypile:
            self.message = "cards not in your hand"
            return
        try:
            request = DiscardRequest(
                player_id=self.player_id,
                card_indices=[card_idx1, card_idx2],
                )
            response = requests.post(
                f"{self.server_url}/games/{self.game_id}/discard",
                json=request.dict(),
            )
            response.raise_for_status()
            self.message = "Cards discarded"
        except requests.RequestException as e:
            self.message = f"Error discarding: {str(e)}"

    def play_card(self, card_idx: int):
        """Send play request to server."""
        if not self.player_state:
            self.message = "Game state not loaded"
            return
        if self.player_state.phase != CribbagePhase.COUNT:
            self.message = "Can't play card, not in COUNT phase"
            return
        if self.get_me() is None:
            self.message = "You are not in the game"
            return
        mypile = self.player_state.visible_piles[self.player_id]
        if card_idx not in mypile:
            self.message = "Invalid card selection"
            return
        try:
            request = PlayRequest(
                player_id=self.player_id,
                card_idx=card_idx,
                )
            response = requests.post(
                f"{self.server_url}/games/{self.game_id}/play",
                json=request.dict(),
            )
            response.raise_for_status()
            self.player_state = PlayerState(**response.json())
            if self.player_state.phase == CribbagePhase.DONE:
                self.message = f"Game over! "
                self.message += f"Your Score: {get_me().score} "
                self.message += f"Opponent: {get_opponent().score} "
            else:
                self.message = f"Played {Card.to_string(card_idx)}"
        except requests.RequestException as e:
            self.message = f"Error playing card: {str(e)}"


# In src/python/cribserver/client.py

    def draw(self):
        """Draw the game UI."""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        if height < 20 or width < 80:
            self.stdscr.addstr(0, 0, "Terminal too small!")
            self.stdscr.refresh()
            return
    
        # Header
        self.stdscr.addstr(0, 0, f"Cribbage Game: {self.game_id}")
        self.stdscr.addstr(1, 0, f"Player: {self.player_name} ({self.player_id})")
    
        # Scores
        score_str = "Scores: " + ", ".join(f"{p.name}: {p.score}" for p in self.player_state.players)
        self.stdscr.addstr(2, 0, score_str)
    
        # Starter card (only show after both players discard)
        starter_pile = self.player_state.visible_piles.get("starter", [])
        if self.player_state and len(starter_pile) == 1:
            starter = starter_pile[0]
            self.stdscr.addstr(4, 0, f"Starter: {display_pile(starter_pile)}")
    
        # Played cards and running total
        if self.player_state.phase == CribbagePhase.COUNT:
            phase1_pile = self.player_state.visible_piles.get("phase1", [])
            phase1_total = self.phase1_pile_total()
            self.stdscr.addstr(5, 0, f"Played: {display_pile(phase1_pile)} (Total: {phase1_total})")
    
        # Player's hand
        me = self.get_me()
        if me is not None:
            my_hand = self.get_my_hand()
            if my_hand:
                self.stdscr.addstr(7, 0, "Your Hand:")
                for i, card_idx in enumerate(my_hand):
                    self.stdscr.addstr(8 + i, 0, f"{i+1}: {Card.to_string(card_idx)}")
    
        # Input prompt (discard or play phase)
        if self.player_state.phase == CribbagePhase.COUNT:
            prompt = f"{'Your turn!' if self.player_state.my_turn else 'Waiting for opponent...'} Enter card to play (e.g., 'JH'), 'q' to quit: "
            self.stdscr.addstr(height - 2, 0, prompt)
            self.stdscr.addstr(height - 1, 0, self.input_buffer)
        elif self.player_state.phase == CribbagePhase.DISCARD:
            prompt = "Enter two cards to play (e.g., '3C 9H'), 'q' to quit: "
            self.stdscr.addstr(height - 2, 0, prompt)
            self.stdscr.addstr(height - 1, 0, self.input_buffer)
    
        # Messages
        message_lines = self.message.split("\n")
        for i, line in enumerate(message_lines[:5]):
            self.stdscr.addstr(7 + i, 30, line[:width-31], curses.color_pair(3))
    
        self.stdscr.refresh()

    def run(self):
        """Main loop for handling input and drawing UI."""
        while self.running:
            try:
                self.draw()
                key = self.stdscr.getch()
                if key >= 32 and key < 128:
                    keychar = chr(key)
                else:
                    keychar = None
                if key == -1:  # No input
                    continue
                if key == ord('q'):
                    self.running = False
                elif key in range(ord('0'), ord('9') + 1) or keychar in ('C', 'D', 'H', 'S', 'A', 'J', 'Q', 'K'):
                    self.input_buffer += keychar
                elif key == ord(' '):
                    self.input_buffer += " "
                elif key == ord('P'):
                    self.poll_state()
                elif key == ord('\n'):
                    if self.input_buffer.strip():
                        # Discard phase: expect two numbers
                        if self.player_state.phase == CribbagePhase.DISCARD:
                            card_names = self.input_buffer.strip().split()
                            if len(card_names) == 2:
                                card_idx1 = Card.from_string(card_names[0])
                                card_idx2 = Card.from_string(card_names[1])
                                self.discard_cards(card_idx1, card_idx2)
                            else:
                                self.message = "Please select exactly 2 cards to discard"
                        # Play phase: expect one number
                        elif self.player_state.phase == CribbagePhase.COUNT:
                            if self.player_state.my_turn:
                                try:
                                    card_names = self.input_buffer.strip().split()
                                    if len(card_names) == 1:
                                        card_idx1 = Card.from_string(card_names[0])
                                        self.play_card(card_idx1)
                                        self.message = f"Played {Card.to_string(card_idx1)}"
                                    else:
                                        self.message = "Play exactly one card"
                                except ValueError as e:
                                    self.message = f"Invalid card number: {e}"
                            else:
                                self.message = "Not your turn!"
                        self.input_buffer = ""
                elif key == curses.KEY_BACKSPACE or key == 127:
                    self.input_buffer = self.input_buffer[:-1]
            except curses.error:
                pass
            except ValueError:
                self.message = "Invalid input"
                self.input_buffer = ""


def main(stdscr):
    """Entry point for the curses client."""
    # Configuration (hardcoded for simplicity; could use argparse)
    #server_url = "http://192.168.1.100:5000"  # Replace with your server IP
    import os
    server_url = os.environ['CRIBSERVER']
    player_id = f"player_{int(time.time())}"  # Unique ID
    player_name = os.environ.get('CRIBNAME')
    game_id = "game1"

    client = CribbageClient(stdscr, server_url, player_id, player_name, game_id)
    client.run()

def run_client():
    """Console entry point for running the curses client."""
    curses.wrapper(main)

if __name__ == "__main__":
    run_client()
