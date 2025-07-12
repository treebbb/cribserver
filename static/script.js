// Configuration
const GAME_ID = 'FIRST_GAME';
let playerId = `player_${Date.now()}`; // Unique player ID
let playerName = prompt('Enter your player name:', 'Player') || 'Player';
let joined = false; // Track join status
let selectedCards = []; // Selected cards for discard/play

// Phase mapping for clarity
const CribbagePhase = {
    JOIN: 1,
    DEAL: 2,
    DISCARD: 3,
    FLIP_STARTER: 4,
    COUNT: 5,
    SHOW: 6,
    CRIB: 7,
    DONE: 8
};

// Initialize player info
document.getElementById('player-id').textContent = playerId;
document.getElementById('player-name').textContent = playerName;

// Card string to index conversion
function cardToIndex(cardStr) {
    const ranks = { 'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13 };
    const suits = { 'C': 0, 'D': 1, 'H': 2, 'S': 3 };
    try {
        const [rank, suit] = cardStr.match(/(\d+|A|J|Q|K)([CDHS])/i).slice(1);
        const rankVal = ranks[rank.toUpperCase()];
        const suitVal = suits[suit.toUpperCase()];
        return (suitVal * 13 + (rankVal - 1));
    } catch (e) {
        console.error(`Invalid card string: ${cardStr}`, e);
        document.getElementById('messages').textContent = `Invalid card: ${cardStr}`;
        return null;
    }
}

// Card index to string
function cardIndexToString(index) {
    const ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
    const suits = ['C', 'D', 'H', 'S'];
    const suit = suits[Math.floor(index / 13)];
    const rank = ranks[index % 13];
    return `${rank}${suit}`;
}

// Get card value
function getCardValue(index) {
    const rank = index % 13 + 1;
    return rank > 10 ? 10 : rank;
}

// Get suit class for styling
function getSuitClass(index) {
    const suits = ['clubs', 'diamonds', 'hearts', 'spades'];
    return suits[Math.floor(index / 13)];
}

// Join game
async function joinGame() {
    console.log(`Attempting to join game with playerId: ${playerId}, playerName: ${playerName}`);
    try {
        const response = await fetch(`/games/${GAME_ID}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_id: playerId, name: playerName })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to join game');
        }
        const data = await response.json();
        console.log('Join successful:', data);
        joined = true;
        document.getElementById('messages').textContent = `Joined game! Players: ${data.players.length}`;
        updateUI(data);
        // Start polling
        const scoresDiv = document.getElementById('scores');
        scoresDiv.setAttribute('hx-get', `/games/${GAME_ID}/${playerId}/state`);
        scoresDiv.setAttribute('hx-trigger', 'every 2s');
        htmx.process(scoresDiv); // Ensure htmx processes the new attributes
    } catch (e) {
        console.error('Join error:', e);
        document.getElementById('messages').textContent = `Error joining game: ${e.message}`;
        setTimeout(joinGame, 5000); // Retry after 5 seconds
    }
}

// Update UI based on game state
function updateUI(state) {
    console.log('Updating UI with state:', state);
    document.getElementById('scores').dataset.state = JSON.stringify(state);

    // Update scores
    const scores = state.players.map(p => `${p.name}: ${p.score}`).join(', ');
    document.getElementById('scores').innerHTML = `<p>Scores: ${scores}</p>`;

    // Update starter card
    const starter = state.visible_piles.starter || [];
    document.getElementById('starter-card').innerHTML = starter.length ? `<p>Starter: ${cardIndexToString(starter[0])}</p>` : '<p>Starter: None</p>';

    // Update played cards
    if (state.phase === CribbagePhase.COUNT) {
        const phase1 = state.visible_piles.phase1 || [];
        const total = phase1.reduce((sum, idx) => sum + getCardValue(idx), 0);
        document.getElementById('played-cards').innerHTML = `<p>Played: ${phase1.map(cardIndexToString).join(' ')} (Total: ${total})</p>`;
    } else {
        document.getElementById('played-cards').innerHTML = `<p>Played: None (Total: 0)</p>`;
    }

    // Update player's hand
    if (selectedCards.length == 0) {
      const hand = state.visible_piles[playerId] || [];
      const handHtml = hand.map((idx, i) => `
        <div class="card ${getSuitClass(idx)}" 
             onclick="selectCard('${cardIndexToString(idx)}', this)"
             data-index="${idx}">
            ${cardIndexToString(idx)}
        </div>
      `).join('');
      document.getElementById('hand-cards').innerHTML = handHtml;
    }

    // Update prompt and button
    const prompt = document.getElementById('prompt');
    const button = document.getElementById('action-button');
    console.log(`Phase: ${state.phase}, my_turn: ${state.my_turn}, selectedCards: ${selectedCards}`);
    if (state.phase === CribbagePhase.DISCARD) {
        prompt.textContent = 'Select two cards to discard:';
        button.textContent = 'Discard Cards';
        button.disabled = selectedCards.length !== 2;
        button.classList.toggle('disabled', selectedCards.length !== 2);
    } else if (state.phase === CribbagePhase.COUNT) {
        prompt.textContent = state.my_turn ? 'Select a card to play:' : 'Waiting for opponent...';
        button.textContent = 'Play Card';
        button.disabled = !state.my_turn || selectedCards.length !== 1;
        button.classList.toggle('disabled', !state.my_turn || selectedCards.length !== 1);
    } else if (state.phase === CribbagePhase.DONE) {
        prompt.textContent = 'Game over!';
        button.disabled = true;
        button.classList.add('disabled');
    } else {
        prompt.textContent = `Game phase: ${Object.keys(CribbagePhase).find(key => CribbagePhase[key] === state.phase) || state.phase}`;
        button.disabled = true;
        button.classList.add('disabled');
    }

    // Update messages
    document.getElementById('messages').textContent = state.message || document.getElementById('messages').textContent;

    // Update game log
    //const log = state.game_log.slice(-10).map(line => `<p>${line}</p>`).join('');
    const log = state.game_log.map(line => `<p>${line}</p>`).join('');
    document.getElementById('game-log').innerHTML = log || '<p>No game log yet.</p>';

    // Reset selected cards if phase changes
    if (state.phase !== CribbagePhase.DISCARD && state.phase !== CribbagePhase.COUNT) {
        selectedCards = [];
      document.querySelectorAll('.card').forEach(card => card.classList.remove('selected'));
      console.log(`state update cleared selected cards: state=${state.phase}`)
    }
}

// Card selection logic
function selectCard(cardStr, element) {
    const state = JSON.parse(document.getElementById('scores').dataset.state || '{}');
    console.log(`Card clicked: ${cardStr}, phase: ${state.phase}, my_turn: ${state.my_turn}`);
    if (state.phase === CribbagePhase.DISCARD) {
        if (selectedCards.includes(cardStr)) {
            selectedCards = selectedCards.filter(c => c !== cardStr);
            element.classList.remove('selected');
            console.log(`Deselected card: ${cardStr}, selectedCards: ${selectedCards}`);
        } else if (selectedCards.length < 2) {
            selectedCards.push(cardStr);
            element.classList.add('selected');
            console.log(`Selected card: ${cardStr}, selectedCards: ${selectedCards}`);
        } else {
            document.getElementById('messages').textContent = 'Select exactly two cards';
            console.log('Cannot select more than 2 cards');
            return;
        }
        const button = document.getElementById('action-button');
        button.disabled = selectedCards.length !== 2;
        button.classList.toggle('disabled', selectedCards.length !== 2);
        console.log(`Button disabled: ${button.disabled}`);
    } else if (state.phase === CribbagePhase.COUNT && state.my_turn) {
        if (selectedCards.includes(cardStr)) {
            selectedCards = [];
            element.classList.remove('selected');
            console.log(`Deselected card: ${cardStr}, selectedCards: ${selectedCards}`);
        } else {
            selectedCards = [cardStr];
            document.querySelectorAll('.card').forEach(card => card.classList.remove('selected'));
            element.classList.add('selected');
            console.log(`Selected card: ${cardStr}, selectedCards: ${selectedCards}`);
        }
        const button = document.getElementById('action-button');
        button.disabled = selectedCards.length !== 1;
        button.classList.toggle('disabled', selectedCards.length !== 1);
        console.log(`Button disabled: ${button.disabled}`);
    } else {
        console.log(`Cannot select card: phase=${state.phase}, my_turn=${state.my_turn}`);
    }
}

// Submit action (discard or play)
async function submitAction() {
    const state = JSON.parse(document.getElementById('scores').dataset.state || '{}');
    console.log(`Submitting action, phase: ${state.phase}, selectedCards: ${selectedCards}`);
    try {
        if (state.phase === CribbagePhase.DISCARD) {
            if (selectedCards.length !== 2) {
                document.getElementById('messages').textContent = 'Please select exactly 2 cards to discard';
                console.log('Invalid discard: not 2 cards');
                return;
            }
            console.log('Discarding cards:', selectedCards);
            const response = await fetch(`/games/${GAME_ID}/discard`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    player_id: playerId,
                    card_indices: selectedCards.map(cardToIndex).filter(idx => idx !== null)
                })
            });
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to discard cards');
            }
            const data = await response.json();
            document.getElementById('messages').textContent = 'Cards discarded';
            console.log('Discard successful:', data);
            updateUI(data);
            selectedCards = [];
            document.querySelectorAll('.card').forEach(card => card.classList.remove('selected'));
        } else if (state.phase === CribbagePhase.COUNT) {
            if (selectedCards.length !== 1) {
                document.getElementById('messages').textContent = 'Please select exactly 1 card to play';
                console.log('Invalid play: not 1 card');
                return;
            }
            console.log('Playing card:', selectedCards[0]);
            const response = await fetch(`/games/${GAME_ID}/play`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    player_id: playerId,
                    card_idx: cardToIndex(selectedCards[0])
                })
            });
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to play card');
            }
            const data = await response.json();
            document.getElementById('messages').textContent = `Played ${selectedCards[0]}`;
            console.log('Play successful:', data);
            updateUI(data);
            selectedCards = [];
            document.querySelectorAll('.card').forEach(card => card.classList.remove('selected'));
        } else {
            console.log(`Cannot submit: phase=${state.phase}`);
        }
    } catch (e) {
        console.error('Action error:', e);
        document.getElementById('messages').textContent = `Error: ${e.message}`;
    }
}

// HTMX event listener to update UI after state fetch
document.body.addEventListener('htmx:afterRequest', (event) => {
    if (event.target.id === 'scores' && joined) {
        console.log('State fetch response:', event.detail.xhr.response);
        try {
            const state = JSON.parse(event.detail.xhr.response || '{}');
            updateUI(state);
        } catch (e) {
            console.error('Error parsing state:', e);
            document.getElementById('messages').textContent = `Error parsing state: ${e.message}`;
        }
    }
});

// Add submit button event listener
document.getElementById('action-button').addEventListener('click', submitAction);

// Start join process
console.log('Starting client...');
joinGame();
