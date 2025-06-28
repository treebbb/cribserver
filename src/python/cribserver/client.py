import curses
import requests
import time
import json
from typing import List, Optional
from .cards import Card
import threading
import sys


# In src/python/cribserver/client.py

class CribbageClient:
    def __init__(self, stdscr, server_url: str, player_id: str, player_name: str, game_id: str):
        self.stdscr = stdscr
        self.server_url = server_url.rstrip('/')
        self.player_id = player_id
        self.player_name = player_name
        self.game_id = game_id
        self.state = None
        self.scores = {}  # Cache scores
        self.message = "Joining game..."
        self.input_buffer = ""
        self.running = True
        self.join_game()

        # Set up curses
        curses.curs_set(0)  # Hide cursor
        curses.start_color()
        curses.use_default_colors()  # Use terminal's default colors
        self.stdscr.bkgd(' ', curses.color_pair(0))  # Set background to black
        curses.init_pair(1, curses.COLOR_RED, -1)    # Hearts/Diamonds (red on default bg)
        curses.init_pair(2, curses.COLOR_BLACK, -1)  # Clubs/Spades (black on default bg)
        curses.init_pair(3, curses.COLOR_GREEN, -1)  # Messages (green on default bg)
        self.stdscr.timeout(100)  # Non-blocking input

        # Start polling thread
        self.polling_thread = threading.Thread(target=self.poll_state, daemon=True)
        self.polling_thread.start()

    def join_game(self):
        """Join the game on the server."""
        try:
            response = requests.post(
                f"{self.server_url}/games/{self.game_id}/join",
                json={"player_id": self.player_id, "name": self.player_name}
            )
            response.raise_for_status()
            data = response.json()
            self.message = f"Joined game! Players: {data['player_count']}/2"
            if data["player_count"] == 2:
                self.message += " Game started, check your hand."
        except requests.RequestException as e:
            self.message = f"Error joining game: {str(e)}"

    def poll_state(self):
        """Poll server for game state and scores every 1.5 seconds."""
        while self.running:
            try:
                # Get game state
                response = requests.get(f"{self.server_url}/games/{self.game_id}/state")
                response.raise_for_status()
                self.state = response.json()

                # Get scores
                response = requests.get(f"{self.server_url}/games/{self.game_id}/score")
                response.raise_for_status()
                self.scores = response.json()
            except requests.RequestException as e:
                self.message = f"Server error: {str(e)}"
            time.sleep(1.5)

    def discard_cards(self, card_indices: List[int]):
        """Send discard request to server."""
        if not self.state or "players" not in self.state:
            self.message = "Game state not loaded"
            return
        player = next((p for p in self.state["players"] if p["player_id"] == self.player_id), None)
        if not player or len(card_indices) != 2:
            self.message = "Invalid discard selection"
            return
        cards = [player["hand"][i] for i in card_indices if i < len(player["hand"])]
        if len(cards) != 2:
            self.message = "Select exactly 2 cards"
            return
        try:
            response = requests.post(
                f"{self.server_url}/games/{self.game_id}/discard",
                json={"player_id": self.player_id, "cards": cards}
            )
            response.raise_for_status()
            self.message = "Cards discarded"
        except requests.RequestException as e:
            self.message = f"Error discarding: {str(e)}"

    def play_card(self, card_index: int):
        """Send play request to server."""
        if not self.state or "players" not in self.state:
            self.message = "Game state not loaded"
            return
        player = next((p for p in self.state["players"] if p["player_id"] == self.player_id), None)
        if not player or card_index >= len(player["hand"]):
            self.message = "Invalid card selection"
            return
        card = player["hand"][card_index]
        try:
            response = requests.post(
                f"{self.server_url}/games/{self.game_id}/play",
                json={"player_id": self.player_id, "card": card}
            )
            response.raise_for_status()
            result = response.json()
            if result["status"] == "game_over":
                self.message = f"Game over! Winner: {result['winner']}"
            else:
                self.message = f"Played {card['rank']} of {card['suit']}"
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
        score_str = "Scores: " + ", ".join(f"{pid}: {score}" for pid, score in self.scores.items())
        self.stdscr.addstr(2, 0, score_str)
    
        # Starter card (only show after both players discard)
        if self.state and self.state.get("starter") and all(len(p["discarded"]) == 2 for p in self.state["players"]):
            starter = Card(**self.state["starter"])
            color = curses.color_pair(1) if starter.suit in [Suit.HEARTS, Suit.DIAMONDS] else curses.color_pair(2)
            self.stdscr.addstr(4, 0, f"Starter: {starter.to_display()}", color)
    
        # Played cards and running total
        if self.state and self.state.get("played_cards"):
            pile = ", ".join(Card(**c).to_display() for c in self.state["played_cards"])
            self.stdscr.addstr(5, 0, f"Played: {pile} (Total: {self.state['current_total']})")
    
        # Player's hand
        if self.state and "players" in self.state:
            player = next((p for p in self.state["players"] if p["player_id"] == self.player_id), None)
            if player and player["hand"]:
                self.stdscr.addstr(7, 0, "Your Hand:")
                for i, card in enumerate(player["hand"]):
                    card_obj = Card(**card)
                    color = curses.color_pair(1) if card_obj.suit in [Suit.HEARTS, Suit.DIAMONDS] else curses.color_pair(2)
                    self.stdscr.addstr(8 + i, 0, f"{i+1}: {card_obj.to_display()}", color)
    
        # Input prompt (discard or play phase)
        if self.state and all(len(p["discarded"]) == 2 for p in self.state["players"]) and not self.state["show_phase"]:
            prompt = f"{'Your turn!' if self.state['current_turn'] == self.player_id else 'Waiting for opponent...'} Enter card number to play (e.g., '1'), 'q' to quit: "
        else:
            prompt = "Enter two card numbers to discard (e.g., '1 2'), 'q' to quit: "
        self.stdscr.addstr(height - 2, 0, prompt)
        self.stdscr.addstr(height - 1, 0, self.input_buffer)
    
        # Messages
        message_lines = self.message.split("\n")
        for i, line in enumerate(message_lines[:5]):
            self.stdscr.addstr(7 + i, 30, line[:width-31\, curses.color_pair(3))
    
        self.stdscr.refresh()

    def run(self):
        """Main loop for handling input and drawing UI."""
        while self.running:
            try:
                self.draw()
                key = self.stdscr.getch()
                if key == -1:  # No input
                    continue
                if key == ord('q'):
                    self.running = False
                elif key in range(ord('0'), ord('9') + 1):
                    self.input_buffer += chr(key)
                elif key == ord(' '):
                    self.input_buffer += " "
                elif key == ord('\n'):
                    if self.input_buffer.strip():
                        # Discard phase: expect two numbers
                        if self.state and not all(len(p["discarded"]) == 2 for p in self.state["players"]):
                            numbers = [int(n) - 1 for n in self.input_buffer.strip().split()]
                            if len(numbers) == 2:
                                self.discard_cards(numbers)
                            else:
                                self.message = "Please select exactly 2 cards to discard"
                        # Play phase: expect one number
                        elif self.state and all(len(p["discarded"]) == 2 for p in self.state["players"]) and not self.state["show_phase"]:
                            if self.state["current_turn"] == self.player_id:
                                try:
                                    card_index = int(self.input_buffer.strip()) - 1
                                    self.play_card(card_index)
                                except ValueError:
                                    self.message = "Invalid card number"
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
    player_name = "Player"  # Replace with desired name
    game_id = "game1"

    client = CribbageClient(stdscr, server_url, player_id, player_name, game_id)
    client.run()

def run_client():
    """Console entry point for running the curses client."""
    curses.wrapper(main)

if __name__ == "__main__":
    run_client()
