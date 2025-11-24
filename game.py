# game.py
# 오목의 규칙과 상태 담당함
BOARD_SIZE = 15

EMPTY = 0
BLACK = 1
WHITE = 2


class OmokGame:
    def __init__(self):
        # board[y][x] 형태로 사용 (행, 열)
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_turn = BLACK  # 흑부터 시작
        self.winner = None         # BLACK / WHITE / None
        self.move_count = 0

    def in_bounds(self, x, y): #범위 안에 두는지 체크
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE

    def place_stone(self, x, y):
        """
        x, y 위치에 현재 턴의 돌을 둔다.
        반환: (성공여부: bool, 메시지: str)
        """
        if not self.in_bounds(x, y):
            return False, "OUT_OF_BOUNDS"

        if self.board[y][x] != EMPTY:
            return False, "ALREADY_OCCUPIED"

        if self.winner is not None:
            return False, "GAME_ALREADY_OVER"

        # 돌 두기
        self.board[y][x] = self.current_turn
        self.move_count += 1

        # 승리 여부 체크
        if self.check_win(x, y):
            self.winner = self.current_turn
            return True, "WIN"

        # 무승부 (원하면 규칙 바꿀 수 있음)
        if self.move_count == BOARD_SIZE * BOARD_SIZE:
            self.winner = 0  # 0 = draw 같은 의미로 써도 됨
            return True, "DRAW"

        # 턴 교체
        self.current_turn = WHITE if self.current_turn == BLACK else BLACK
        return True, "OK"

    def check_win(self, x, y):
        """
        방금 (x,y)에 놓인 돌을 기준으로 5목인지 검사.
        """
        color = self.board[y][x]
        if color == EMPTY:
            return False

        # 4가지 방향 (dx, dy)
        directions = [
            (1, 0),   # 가로
            (0, 1),   # 세로
            (1, 1),   # ↘ 대각
            (1, -1),  # ↗ 대각
        ]

        for dx, dy in directions:
            count = 1  # (x, y) 포함

            # 한쪽 방향
            nx, ny = x + dx, y + dy
            while self.in_bounds(nx, ny) and self.board[ny][nx] == color:
                count += 1
                nx += dx
                ny += dy

            # 반대 방향
            nx, ny = x - dx, y - dy
            while self.in_bounds(nx, ny) and self.board[ny][nx] == color:
                count += 1
                nx -= dx
                ny -= dy

            if count >= 5:
                return True

        return False

    def get_state(self):
        """
        네트워크/클라이언트로 보낼 때 쓸 수 있는 상태 표현.
        """
        return {
            "board": self.board,
            "turn": self.current_turn,
            "winner": self.winner,
            "move_count": self.move_count,
        }
