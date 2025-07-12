import unittest
from fastapi.testclient import TestClient
from cribserver.server import app, games, player_stats, DECK_CREATOR
from cribserver.cards import Deck, Card
from cribserver.api_model import JoinRequest, DiscardRequest, PlayRequest, CribbagePhase, Player

class TestCribbageServer(unittest.TestCase):
    def setUp(self):
        """Set up the test client and reset game state."""
        self.client = TestClient(app)
        self.deck = Deck()
        self.deck.shuffle = lambda: None
        # reset globals in server.py
        games.clear()
        player_stats.clear()
        DECK_CREATOR.create_deck = lambda: self.deck
        # handy map from card string to card_idx
        self.card_map = {Card.to_string(i).strip(): i for i in range(52)}  # Map card strings (e.g., 'AC') to indices

    def set_deck_order(self, card_indices):
        """Set a fixed deck for the game based on dealt cards."""
        

    def parse_card(self, card_str):
        """Convert card string (e.g., 'AC') to index."""
        if card_str not in self.card_map:
            raise ValueError(f"Invalid card string: {card_str}")
        return self.card_map[card_str]

    def run_game_test(self, actions, expected_game_log=None):
        """Run a test with a list of actions and verify game log."""

        # Phase 1: Parse DEAL actions to collect all dealt cards
        cards = []
        for action_line in actions:
            if action_line.startswith("DEAL,"):
                action, player_id, subject = action_line.split(",")
                player_id = player_id.strip()
                card_string = subject.strip()
                cards.append(Card.from_string(card_string))
        self.deck.reset()
        self.deck.piles[self.deck.REMAINING] = cards

        # Phase 2: find the player_ids and game_id
        player_id1 = None
        player_id2 = None
        game_id = None
        for action_line in actions:
            if action_line.startswith("JOIN"):
                action, player_id, subject = action_line.split(",")
                action = action.strip().upper()
                player_id = player_id.strip()
                subject = subject.strip()
                if player_id1 is None:
                    player_id1 = player_id
                    game_id = subject
                else:
                    player_id2 = player_id

        # Phase 3: Process non-DEAL actions
        for action_line in actions:
            action, player_id, subject = action_line.split(",")
            action = action.strip().upper()
            player_id = player_id.strip()
            subject = subject.strip()

            if action == "DEAL":
                continue  # Skip DEAL actions (already processed)

            elif action == "JOIN":
                # Handle JOIN action
                if player_id == 'player1':
                    name = "P1"
                else:
                    name = "P2"
                join_request = JoinRequest(player_id=player_id, name=name)
                response = self.client.post(f"/games/{game_id}/join", json=join_request.model_dump())
                self.assertEqual(response.status_code, 200, f"JOIN failed for {player_id}: {response.text}")
                state = response.json()
                self.assertEqual(state["game_id"], subject)

            elif action == "DISCARD":
                # Handle DISCARD action
                card_indices = []
                for card_string in subject.split():
                    card_indices.append(Card.from_string(card_string))
                discard_request = DiscardRequest(player_id=player_id, card_indices=card_indices)
                response = self.client.post(f"/games/{game_id}/discard", json=discard_request.model_dump())
                self.assertEqual(response.status_code, 200, f"DISCARD failed for {player_id}: {response.text}")
                state = response.json()
                self.assertIn(state["phase"], [CribbagePhase.DISCARD.value, CribbagePhase.COUNT.value])

            elif action == "PLAY":
                # Handle PLAY action
                card_idx = self.parse_card(subject)
                play_request = PlayRequest(player_id=player_id, card_idx=card_idx)
                response = self.client.post(f"/games/{game_id}/play", json=play_request.model_dump())
                self.assertEqual(response.status_code, 200, f"PLAY failed for {player_id}: {response.text}")
                state = response.json()
                self.assertIn(state["phase"], [CribbagePhase.COUNT.value, CribbagePhase.SHOW.value, CribbagePhase.DONE.value])
            else:
                raise ValueError(f"Unknown action: {action}")

        # Verify final game log
        if expected_game_log:
            response = self.client.get(f"/games/{game_id}/{player_id1}/state")
            self.assertEqual(response.status_code, 200)
            state = response.json()
            self.assertEqual(state["game_log"], expected_game_log,
                             f"Game log mismatch:\nExpected:\n{expected_game_log}\nGot:\n{state['game_log']}")
            #for i, (e, g) in enumerate(zip(expected_game_log, state["game_log"])):
            #    if e != g:
            #        print(f"{i}: expected={e}  got={g}")
            #        break

    def test_cribbage_game_flow1(self):
        """Test the full game flow using the input framework."""
        actions = GAME1_ACTIONS.strip().splitlines()
        expected_game_log = GAME1_EXPECTED.strip().splitlines()
        self.run_game_test(actions, expected_game_log)

    def test_cribbage_game_flow2(self):
        """Test the full game flow using the input framework."""
        actions = GAME2_ACTIONS.strip().splitlines()
        expected_game_log = GAME2_EXPECTED.strip().splitlines()
        self.run_game_test(actions, expected_game_log)

    def test_cribbage_game_flow3(self):
        """Test the full game flow using the input framework."""
        actions = GAME3_ACTIONS.strip().splitlines()
        expected_game_log = GAME3_EXPECTED.strip().splitlines()
        self.run_game_test(actions, expected_game_log)
        
GAME1_ACTIONS = '''
JOIN,player1,test_game
JOIN,player2,test_game
DEAL,player1, AC
DEAL,player2, 2C
DEAL,player1, 3C
DEAL,player2, 4C
DEAL,player1, 5C
DEAL,player2, 6C
DEAL,player1, 7C
DEAL,player2, 8C
DEAL,player1, 9C
DEAL,player2,10C
DEAL,player1, JC
DEAL,player2, QC
DISCARD,player1, AC  3C
DISCARD,player2, QC  2C
DEAL,starter, KC
PLAY,player2,10C
PLAY,player1, 5C
PLAY,player2, 8C
PLAY,player1, 7C
PLAY,player2, 4C
PLAY,player1, JC
PLAY,player2, 6C
PLAY,player1, 9C'''
GAME1_EXPECTED = '''
Player P1 joined game
Player P2 joined game
game.phase -> DEAL
game.phase -> DISCARD
Player P1 discarded 2 cards
Player P2 discarded 2 cards
game.phase -> FLIP_STARTER
game.phase -> COUNT
Player P2 played 10C
Player P1 played  5C
P1 2 points for 15 total
Player P2 played  8C
Player P1 played  7C
P1 1 point for Go
Player P2 played  4C
Player P1 played  JC
Player P2 played  6C
Player P1 played  9C
P1 1 point for Go
game.phase -> SHOW
P2 4 points for flush of 10C, 8C, 4C, 6C
P2 1 point for flush including starter KC
P1 2 points for 15 from 5C, JC
P1 2 points for 15 from 5C, KC
P1 4 points for flush of 5C, 7C, JC, 9C
P1 1 point for flush including starter KC
P1 1 point for nobs with JC matching suit of starter KC
game.phase -> CRIB
P1 2 points for 15 from 3C, QC, 2C
P1 2 points for 15 from 3C, 2C, KC
P1 3 points for run of AC, 2C, 3C
P1 4 points for flush of AC, 3C, QC, 2C
P1 5 points for crib flush of AC, 3C, QC, 2C, KC
Player P1 score: 30
Player P2 score: 5
Player P1 wins
game.phase -> DONE
'''
GAME2_ACTIONS = '''
JOIN,player1,test_game
JOIN,player2,test_game
DEAL,player1, 8D
DEAL,player2, JS
DEAL,player1, 9D
DEAL,player2, 2H
DEAL,player1, 10S
DEAL,player2, AC
DEAL,player1, 6H
DEAL,player2, JH
DEAL,player1, 9H
DEAL,player2, 8H
DEAL,player1, QC
DEAL,player2, 7D
DISCARD,player1, 6H  QC
DISCARD,player2, AC  2H
DEAL,starter, 5S
PLAY,player2, JS
PLAY,player1, 10S
PLAY,player2, JH
PLAY,player1, 9D
PLAY,player2, 8H
PLAY,player1, 9H
PLAY,player2, 7D
PLAY,player1, 8D
'''

GAME2_EXPECTED = '''
Player P1 joined game
Player P2 joined game
game.phase -> DEAL
game.phase -> DISCARD
Player P1 discarded 2 cards
Player P2 discarded 2 cards
game.phase -> FLIP_STARTER
game.phase -> COUNT
Player P2 played  JS
Player P1 played 10S
Player P2 played  JH
P2 2 points for pair of JH, JS
P2 1 point for Go
Player P1 played  9D
Player P2 played  8H
Player P1 played  9H
P1 2 points for pair of 9H, 9D
P1 1 point for Go
Player P2 played  7D
Player P1 played  8D
P1 2 points for 15 total
P1 1 point for Go
game.phase -> SHOW
P2 2 points for 15 from JS, 5S
P2 2 points for 15 from JH, 5S
P2 2 points for 15 from 8H, 7D
P2 2 points for 1 pair of JS, JH
P2 1 point for nobs with JS matching suit of starter 5S
P1 2 points for 15 from 10S, 5S
P1 2 points for 1 pair of 9D, 9H
P1 3 points for run of 8D, 9D, 10S
P1 3 points for run of 8D, 9H, 10S
game.phase -> CRIB
P1 2 points for 15 from QC, 5S
Player P1 score: 18
Player P2 score: 12
Player P1 wins
game.phase -> DONE
'''

GAME3_ACTIONS = '''
JOIN,player1,test_game
JOIN,player2,test_game
DEAL,player1, 5S
DEAL,player2, 5C
DEAL,player1, 6D
DEAL,player2, 5H
DEAL,player1, 7C
DEAL,player2, 10H
DEAL,player1, JS
DEAL,player2, 10S
DEAL,player1, 2H
DEAL,player2, KC
DEAL,player1, 9D
DEAL,player2, 3H
DISCARD,player1, 2H  9D
DISCARD,player2, KC  3H
DEAL,starter, 10D
PLAY,player2, 10S
PLAY,player1, 5S
PLAY,player2, 10H
PLAY,player1, 6D
PLAY,player2, 5H
PLAY,player1, JS
PLAY,player2, 5C
PLAY,player1, 7C
'''
GAME3_EXPECTED = '''
Player P1 joined game
Player P2 joined game
game.phase -> DEAL
game.phase -> DISCARD
Player P1 discarded 2 cards
Player P2 discarded 2 cards
game.phase -> FLIP_STARTER
game.phase -> COUNT
Player P2 played 10S
Player P1 played  5S
P1 2 points for 15 total
Player P2 played 10H
P2 2 points for pair of 10H, 10S
Player P1 played  6D
P1 2 points for 31 total
Player P2 played  5H
Player P1 played  JS
P1 2 points for 15 total
Player P2 played  5C
P2 2 points for pair of 5C, 5H
Player P1 played  7C
P1 1 point for Go
game.phase -> SHOW
P2 2 points for 15 from 10S, 5H
P2 2 points for 15 from 10S, 5C
P2 2 points for 15 from 10H, 5H
P2 2 points for 15 from 10H, 5C
P2 2 points for 15 from 5H, 10D
P2 2 points for 15 from 5C, 10D
P2 6 points for 3 pairs of 10S, 10H, 10D
P2 2 points for 1 pair of 5H, 5C
P1 2 points for 15 from 5S, JS
P1 2 points for 15 from 5S, 10D
P1 3 points for run of 5S, 6D, 7C
game.phase -> CRIB
P1 2 points for 15 from 2H, KC, 3H
P1 2 points for 15 from 2H, 3H, 10D
Player P1 score: 18
Player P2 score: 24
Player P2 wins
game.phase -> DONE
'''

if __name__ == "__main__":
    unittest.main()
