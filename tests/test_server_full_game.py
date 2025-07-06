import unittest
from fastapi.testclient import TestClient
from cribserver.server import app, games, player_stats
from cribserver.cards import Deck, Card
from cribserver.api_model import JoinRequest, DiscardRequest, PlayRequest, CribbagePhase, Player


EXPECTED_GAME_LOG = '''
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

class TestCribbageServer(unittest.TestCase):
    def setUp(self):
        """Set up the test client and reset game state."""
        self.client = TestClient(app)
        games.clear() # Reset in-memory game state
        player_stats.clear() # Reset player stats
        self.game_id = "test_game"
        self.player1_id = "player1"
        self.player2_id = "player2"
        self.player1_name = "P1"
        self.player2_name = "P2"

        # Fixed deck: Ace to King of Clubs (indices 0 to 12)
        self.fixed_deck_cards = list(range(13)) # [0:AC, 1:2C, ..., 12:KC]

    def set_fixed_deck(self, game_id):
        """Set a fixed deck for the game."""
        if game_id in games:
            games[game_id].deck = Deck()
            games[game_id].deck.piles["remaining"] = self.fixed_deck_cards.copy()
            games[game_id].deck.piles["discard"] = []
            games[game_id].deck.shuffle = lambda: None # Disable shuffle

    def test_cribbage_game_flow(self):
        """Test the full game flow: join, discard, play, and show phases."""
        # Step 1: P1 joins the game
        join_request_p1 = JoinRequest(player_id=self.player1_id, name=self.player1_name)
        response = self.client.post(f"/games/{self.game_id}/join", json=join_request_p1.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(state["game_id"], self.game_id)
        self.assertEqual(state["phase"], CribbagePhase.JOIN.value)
        self.assertEqual(len(state["players"]), 1)
        self.assertEqual(state["players"][0]["name"], self.player1_name)
        self.assertEqual(state["visible_piles"].get(self.player1_id, []), []) # No cards dealt yet
        self.assertEqual(state["players"][0]["score"], 0)
        self.assertEqual(state["is_dealer"], False)
        self.assertEqual(state["my_turn"], False)

        # Set fixed deck for predictable dealing
        self.set_fixed_deck(self.game_id)

        # Step 2: P2 joins the game, triggering deal
        join_request_p2 = JoinRequest(player_id=self.player2_id, name=self.player2_name)
        response = self.client.post(f"/games/{self.game_id}/join", json=join_request_p2.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(state["game_id"], self.game_id)
        self.assertEqual(state["phase"], CribbagePhase.DISCARD.value)
        self.assertEqual(len(state["players"]), 2)
        self.assertEqual(state["players"][1]["name"], self.player2_name)
        self.assertEqual(len(state["visible_piles"][self.player2_id]), 6) # P2 has 6 cards
        self.assertEqual(state["players"][1]["score"], 0)
        self.assertEqual(state["is_dealer"], False)
        self.assertEqual(state["my_turn"], True) # P2 (non-dealer) starts discard

        # Get P1's state to verify cards
        response = self.client.get(f"/games/{self.game_id}/{self.player1_id}/state")
        self.assertEqual(response.status_code, 200)
        state_p1 = response.json()
        self.assertEqual(len(state_p1["visible_piles"][self.player1_id]), 6) # P1 has 6 cards
        self.assertEqual(state_p1["is_dealer"], True) # P1 is dealer
        self.assertEqual(state_p1["my_turn"], False)

        # Expected cards for P1 (first 6 cards: 0:AC, 1:2C, 2:3C, 3:4C, 4:5C, 5:6C)
        self.assertEqual(state_p1["visible_piles"][self.player1_id], [0, 2, 4, 6, 8, 10])

        # Expected cards for P2 (next 6 cards: 6:7C, 7:8C, 8:9C, 9:TC, 10:JC, 11:QC)
        self.assertEqual(state["visible_piles"][self.player2_id], [1, 3, 5, 7, 9, 11])

        # Verify crib is not visible in PlayerState
        self.assertNotIn("crib", state["visible_piles"])
        self.assertNotIn("crib", state_p1["visible_piles"])

        # Check crib via GameState
        game_state = games[self.game_id]
        self.assertEqual(len(game_state.deck.get_cards("crib")), 0) # Crib empty before discards

        # Step 3: P1 discards two cards (e.g., 0:AC, 1:2C to crib)
        discard_request_p1 = DiscardRequest(player_id=self.player1_id, card_indices=[0, 2])
        response = self.client.post(f"/games/{self.game_id}/discard", json=discard_request_p1.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(state["phase"], CribbagePhase.DISCARD.value)
        self.assertEqual(len(state["visible_piles"][self.player1_id]), 4) # 4 cards left
        self.assertEqual(state["visible_piles"][self.player1_id], [4, 6, 8, 10])
        self.assertNotIn("crib", state["visible_piles"]) # Crib not visible

        # Check crib via GameState
        self.assertEqual(game_state.deck.get_cards("crib"), [0, 2]) # 2 cards in crib

        # Step 4: P2 discards two cards (e.g., 6:7C, 7:8C to crib), triggering starter flip
        discard_request_p2 = DiscardRequest(player_id=self.player2_id, card_indices=[11, 1])
        response = self.client.post(f"/games/{self.game_id}/discard", json=discard_request_p2.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(state["phase"], CribbagePhase.COUNT.value)
        self.assertEqual(len(state["visible_piles"][self.player2_id]), 4) # 4 cards left
        self.assertEqual(state["visible_piles"][self.player2_id], [3, 5, 7, 9])
        self.assertEqual(len(state["visible_piles"]["starter"]), 1) # Starter card flipped (12:KC)
        self.assertEqual(state["visible_piles"]["starter"], [12])
        self.assertEqual(state["my_turn"], True) # P2 (non-dealer) starts play
        self.assertNotIn("crib", state["visible_piles"]) # Crib not visible

        # Check crib via GameState
        self.assertEqual(game_state.deck.get_cards("crib"), [0, 2, 11, 1]) # 4 cards in crib

        # Step 5: P2 plays a card (e.g., 9:10C, value 10)
        play_request_p2 = PlayRequest(player_id=self.player2_id, card_idx=9)
        response = self.client.post(f"/games/{self.game_id}/play", json=play_request_p2.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(state["phase"], CribbagePhase.COUNT.value)
        self.assertEqual(len(state["visible_piles"][self.player2_id]), 3) # 3 cards left
        self.assertEqual(state["visible_piles"][self.player2_id], [3, 5, 7])
        self.assertEqual(sum(Card.get_value(c) for c in state["visible_piles"]["phase1"]), 10) # Total is 10
        self.assertEqual(state["my_turn"], False) # P1's turn
        self.assertEqual(state["players"][1]["score"], 0) # No points for single card play

        # Step 6: P1 plays a card (e.g., 4:5C, value 3, total=14)
        play_request_p1 = PlayRequest(player_id=self.player1_id, card_idx=4)
        response = self.client.post(f"/games/{self.game_id}/play", json=play_request_p1.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(len(state["visible_piles"][self.player1_id]), 3) # 3 cards left
        self.assertEqual(state["visible_piles"][self.player1_id], [6, 8, 10])
        self.assertEqual(sum(Card.get_value(c) for c in state["visible_piles"]["phase1"]), 15) # Total is 15
        self.assertEqual(state["my_turn"], False) # P2's turn
        self.assertEqual(state["players"][0]["score"], 2) # Two points for reaching 15

        # Check P2's hand via GameState
        self.assertEqual(game_state.deck.get_cards(self.player2_id), [3, 5, 7])

        # Step 7: P2 plays a card (e.g., 7:8C, value 4, total=23)
        play_request_p2 = PlayRequest(player_id=self.player2_id, card_idx=7)
        response = self.client.post(f"/games/{self.game_id}/play", json=play_request_p2.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(sum(Card.get_value(c) for c in state["visible_piles"]["phase1"]), 23)
        self.assertEqual(len(state["visible_piles"][self.player2_id]), 2) # 2 cards left
        self.assertEqual(state["visible_piles"][self.player2_id], [3, 5])
        self.assertEqual(state["my_turn"], False) # P1's turn

        # Step 8: P1 plays a card (e.g., 6:7C, value 7, total=30)
        # this triggers a Go and a Point
        play_request_p1 = PlayRequest(player_id=self.player1_id, card_idx=6)
        response = self.client.post(f"/games/{self.game_id}/play", json=play_request_p1.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(len(state["visible_piles"][self.player1_id]), 2) # 2 cards left
        self.assertEqual(state["visible_piles"][self.player1_id], [8, 10])
        self.assertEqual(state["my_turn"], False) # P2's turn
        # one point for P1 getting the last card
        self.assertEqual(state["players"][0]["score"], 3)
        # phase1 pile is reset to zero
        self.assertEqual(sum(Card.get_value(c) for c in state["visible_piles"]["phase1"]), 0)

        # step 9: get P2's state to verify cards and turn
        response = self.client.get(f"/games/{self.game_id}/{self.player2_id}/state")
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(len(state["visible_piles"][self.player2_id]), 2) # 2 cards left
        self.assertEqual(state["visible_piles"][self.player2_id], [3, 5])
        self.assertEqual(state["is_dealer"], False)
        self.assertEqual(state["my_turn"], True)

        # Step 10: P2 plays a card (e.g., 3:4C, value 4, total=4)
        play_request_p2 = PlayRequest(player_id=self.player2_id, card_idx=3)
        response = self.client.post(f"/games/{self.game_id}/play", json=play_request_p2.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(sum(Card.get_value(c) for c in state["visible_piles"]["phase1"]), 4)
        self.assertEqual(len(state["visible_piles"][self.player2_id]), 1) # 1 card left
        self.assertEqual(state["visible_piles"][self.player2_id], [5])
        self.assertEqual(state["my_turn"], False) # P1's turn

        # Step 11: P1 plays a card (e.g., 10:JC, value 10, total=14)
        play_request_p1 = PlayRequest(player_id=self.player1_id, card_idx=10)
        response = self.client.post(f"/games/{self.game_id}/play", json=play_request_p1.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(sum(Card.get_value(c) for c in state["visible_piles"]["phase1"]), 14)
        self.assertEqual(len(state["visible_piles"][self.player1_id]), 1) # 1 card left
        self.assertEqual(state["visible_piles"][self.player1_id], [8])
        self.assertEqual(state["my_turn"], False) # P1's turn

        # Step 12: P2 plays last card (e.g., 5:6C, value 6, total=20)
        play_request_p2 = PlayRequest(player_id=self.player2_id, card_idx=5)
        response = self.client.post(f"/games/{self.game_id}/play", json=play_request_p2.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        self.assertEqual(sum(Card.get_value(c) for c in state["visible_piles"]["phase1"]), 20)
        self.assertEqual(len(state["visible_piles"][self.player2_id]), 0) # no cards left
        self.assertEqual(state["my_turn"], False) # P1's turn

        # Step 13: P1 plays last card (e.g., 8:9C, value 9, total=29)
        play_request_p1 = PlayRequest(player_id=self.player1_id, card_idx=8)
        response = self.client.post(f"/games/{self.game_id}/play", json=play_request_p1.model_dump())
        self.assertEqual(response.status_code, 200)
        state = response.json()
        # phase1 pile will be drained after last card played
        self.assertEqual(sum(Card.get_value(c) for c in state["visible_piles"]["phase1"]), 0)
        self.assertEqual(len(state["visible_piles"][self.player1_id]), 0) # no cards
        self.assertEqual(state["my_turn"], False)
        
        # the entire show + crib phase will be scored at this point
        self.assertEqual(state["players"][0]["score"], 30)
        # we are now in the show phase, crib phase, done phase
        self.assertEqual(state["phase"], CribbagePhase.DONE.value)
        # check game log
        #for line in state["game_log"]:
        #    print(line)
        expected = EXPECTED_GAME_LOG.strip().splitlines()
        self.assertEqual(state["game_log"], expected)


if __name__ == "__main__":
    unittest.main()

