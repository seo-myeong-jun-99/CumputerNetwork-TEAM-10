# game.py
# Omok (Gomoku) game logic and state container

BOARD_SIZE = 15 #오목판 사이즈

# 비어있는거는 0, 검은돌 1, 흰돌 2
EMPTY = 0
BLACK = 1
WHITE = 2


class OmokGame:
    def __init__(self):
        self.reset() # 시작시 초기화

    def in_bounds(self, x, y): #x,y가 보드 내부인지 검사하기
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE #BOARD_SIZE 15를 기준으로

    def place_stone(self, x, y): #
        """
        Place a stone at (x, y).
        Returns: (ok: bool, msg: str)
        """
        if not self.in_bounds(x, y): #범위 내부인지 검사
            return False, "OUT_OF_BOUNDS"

        if self.board[y][x] != EMPTY: #이미 그 자리에 다른 돌이 있는 경우(EMPTY가 아닌 경우)
            return False, "ALREADY_OCCUPIED"

        if self.winner is not None: # 만약 승자가 이미 있으면
            return False, "GAME_ALREADY_OVER"

        self.board[y][x] = self.current_turn  #배열이므로 [y][x]로 해야함 주의 (0,0)~(14,14)까지 있음
        self.move_count += 1

        if self.check_win(x, y): #승리 체크
            self.winner = self.current_turn
            return True, "WIN"

        if self.move_count == BOARD_SIZE * BOARD_SIZE: #칸이 꽉차면
            self.winner = 0  # 무승부
            return True, "DRAW"

        self.current_turn = WHITE if self.current_turn == BLACK else BLACK #위의 if상황들이 모두 아닌경우에 실행, 턴 넘기기
        return True, "OK"

    def check_win(self, x, y): #승리 체크하기
        color = self.board[y][x]
        if color == EMPTY: # 안전 장치
            return False

        directions = [
            (1, 0),   # 오른쪽
            (0, 1),   # 아래쪽
            (1, 1),   # 대각선 오른쪽 아래 방향
            (1, -1),  # 대각선 오른쪽 위 방향
        ]

        for dx, dy in directions:
            count = 1 # 방금 둔걸 하나로 치고 시작 (1로 초기화)
            # dx=1 dy=0
            # dx=0 dy=1
            # dx=1 dy=1
            # dx=1 dy=-1
            #순서로 꺼내기

            nx, ny = x + dx, y + dy
            while self.in_bounds(nx, ny) and self.board[ny][nx] == color:
                count += 1
                nx += dx
                ny += dy

            nx, ny = x - dx, y - dy #반대 방향으로도 검사하기
            while self.in_bounds(nx, ny) and self.board[ny][nx] == color:
                count += 1
                nx -= dx
                ny -= dy

            if count >= 5: #총 5개이상이면
                return True

        return False

    def get_state(self):
        """
        Return a dictionary-friendly representation for clients.
        """
        return {
            "board": self.board,
            "turn": self.current_turn,
            "winner": self.winner,
            "move_count": self.move_count,
        }

    def reset(self):
        """Restart the match with a clean board and counters."""
        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)] #처음 시작하면 모든 칸 EMPTY
        self.current_turn = BLACK # 시작은 흑이 먼저
        self.winner = None # 승자는 없는 상태로 시작
        self.move_count = 0 #둔 돌 0 개로 시작
