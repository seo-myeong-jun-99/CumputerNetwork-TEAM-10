# game.py
# Omok (Gomoku) game logic and state container

BOARD_SIZE = 15

EMPTY = 0
BLACK = 1
WHITE = 2


class OmokGame:
    def __init__(self):
        self.reset()

    def in_bounds(self, x, y):
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE

    def place_stone(self, x, y):
        
        if not self.in_bounds(x, y):
            return False, "OUT_OF_BOUNDS"

        if self.board[y][x] != EMPTY:
            return False, "ALREADY_OCCUPIED"

        if self.winner is not None:
            return False, "GAME_ALREADY_OVER"

        self.board[y][x] = self.current_turn
        self.move_count += 1

        if self.check_win(x, y):
            self.winner = self.current_turn
            return True, "WIN"

        if self.move_count == BOARD_SIZE * BOARD_SIZE:
            self.winner = 0  # draw
            return True, "DRAW"

        self.current_turn = WHITE if self.current_turn == BLACK else BLACK
        return True, "OK"

    def check_win(self, x, y):
        """Check if placing at (x, y) results in a 5-in-a-row."""
        color = self.board[y][x]
        if color == EMPTY:
            return False

        directions = [
            (1, 0),   # horizontal
            (0, 1),   # vertical
            (1, 1),   # diag down-right
            (1, -1),  # diag up-right
        ]

        for dx, dy in directions:
            count = 1

            nx, ny = x + dx, y + dy
            while self.in_bounds(nx, ny) and self.board[ny][nx] == color:
                count += 1
                nx += dx
                ny += dy

            nx, ny = x - dx, y - dy
            while self.in_bounds(nx, ny) and self.board[ny][nx] == color:
                count += 1
                nx -= dx
                ny -= dy

            if count >= 5:
                return True

        return False

    def get_state(self):
        return {
            "board": self.board,
            "turn": self.current_turn,
            "winner": self.winner,
            "move_count": self.move_count,
        }

    def reset(self):
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_turn = BLACK
        self.winner = None
        self.move_count = 0
