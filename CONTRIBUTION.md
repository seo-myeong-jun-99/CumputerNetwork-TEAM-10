### REFAT MD SAYED ISLAM
- Implemented the entire `game.py` (core Omok game logic)
  - Created the 15×15 Omok board data structure
  - Implemented move validation (bounds checking, occupied cell checks)
  - Built the win detection algorithm (horizontal, vertical, diagonal checks)
  - Implemented turn switching between BLACK and WHITE
  - Managed overall game states (playing, win, draw)

---

### 김우진 (Woojin Kim)
- Implemented the entire `protocol.py` (HTTP communication layer)
  - Built HTTP/1.1 request/response construction and parsing logic
  - Implemented JSON serialization/deserialization
  - Created client-side API wrappers for join/move/state/quit/restart/chat
  - Designed error handling for network failures and invalid server responses

---

### 서명준
- Implemented major server-side logic in `Server.py`
  - Implemented player/session management
  - Integrated game logic with server-side state handling
  - Implemented HTTP request parsing and routing
  - Managed game state responses for all connected clients
  - Wrote documentation and contributed to project structuring

---

### 권진욱
- Implemented the entire `client.py` (pygame Omok client UI)
  - Built complete game interface (board rendering, stones, status bar, restart UI)
  - Implemented user input handling (mouse clicks, keyboard input, restart logic, quitting)
  - Integrated all client-side API calls (`join_server`, `request_state`, `submit_move`, `send_chat`, `restart_game`, `quit_game`)
  - Implemented periodic state synchronization and screen rendering loop
  - Implemented chat UI, message rendering, and input system
  - Added local IP auto-detection and command-line argument parsing
