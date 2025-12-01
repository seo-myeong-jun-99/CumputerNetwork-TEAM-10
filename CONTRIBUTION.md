### REFAT MD SAYED ISLAM
game.py - I made all the game rules and logic:
- Created the 15×15 Omok board
- Made the move checking system (can't place outside board or on taken spots)
- Built the win checker - looks for 5 stones in a row in any direction
- Handles turn switching between BLACK and WHITE
- Manages game states (playing, win, draw)

### 김우진
- Implemented the entire `protocol.py`
  - Built HTTP request/response construction and parsing logic
  - Implemented JSON serialization/deserialization
  - Implemented client-side API wrappers for join/move/state and other game actions

### 서명준
- Server Development `server.py`
  - Player management
  - Game logic handling
  - State management
  - HTTP request processing
  - README documentation

### 권진욱
- Implemented the entire `client.py` (pygame-based Omok client UI)
  - Built the full game interface using pygame (board rendering, stones, status bar, restart UI)
  - Implemented mouse/keyboard event handling for moves, chat, restart, and quitting
  - Integrated all client-side API calls (`join_server`, `request_state`, `submit_move`, `send_chat`, `restart_game`, `quit_game`)
  - Implemented periodic state synchronization with the server and rendering logic
  - Implemented chat UI, message display, and input handling
  - Added local IP auto-detection (`detect_local_ip`) and argument parsing

