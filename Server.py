import socket

HOST = "0.0.0.0"
PORT = 5000
BOARD_SIZE = 15

EMPTY = "."
BLACK = "X"   # Player 1
WHITE = "O"   # Player 2


def create_board():
    return [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]


def in_bounds(r, c):
    return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE


def check_five(board, r, c):
    stone = board[r][c]
    if stone == EMPTY:
        return False

    directions = [
        (0, 1),   # 가로
        (1, 0),   # 세로
        (1, 1),   # 대각 ↘
        (-1, 1),  # 대각 ↗
    ]

    for dr, dc in directions:
        count = 1

        # 한쪽 방향
        nr, nc = r + dr, c + dc
        while in_bounds(nr, nc) and board[nr][nc] == stone:
            count += 1
            nr += dr
            nc += dc

        # 반대 방향
        nr, nc = r - dr, c - dc
        while in_bounds(nr, nc) and board[nr][nc] == stone:
            count += 1
            nr -= dr
            nc -= dc

        if count >= 5:
            return True

    return False


def board_to_string(board):
    # 열 번호
    header = "   " + " ".join(f"{i:2d}" for i in range(1, BOARD_SIZE + 1))
    lines = [header]
    for i, row in enumerate(board, start=1):
        lines.append(f"{i:2d} " + " ".join(row))
    return "\n".join(lines)


def send_line(sock, msg):
    sock.sendall((msg + "\n").encode("utf-8"))


def broadcast(players, msg):
    for p in players:
        send_line(p["sock"], msg)


def game_server():
    board = create_board()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv: #socket.AF_INET(IPv4 사용), socket.SOCK_STREAM(TCP소켓 사용) 
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT)) # ip와 포트번호로 바인딩
        srv.listen(2) #플레이어 최대 2명
        print(f"서버 대기 중... ({HOST}:{PORT})")

        
        players = []

        for num in (1, 2):
            conn, addr = srv.accept() #서버가 클라이언트 요청을 수락
            print(f"플레이어 {num} 접속: {addr}")
            f = conn.makefile("r", encoding="utf-8")
            stone = BLACK if num == 1 else WHITE
            player = {"sock": conn, "file": f, "stone": stone}
            players.append(player)
            send_line(conn, f"INFO 서버에 연결되었습니다. 당신의 돌: {stone}")
            send_line(conn, "INFO 다른 플레이어를 기다리는 중입니다...")

        broadcast(players, "INFO 두 플레이어가 모두 접속했습니다. 게임을 시작합니다!")

        turn = 0  # 0 → players[0] / 1 → players[1]

        while True:
            current = players[turn]
            other = players[1 - turn]

            # 현재 보드 상태 브로드캐스트
            board_str = board_to_string(board)
            broadcast(players, "")
            broadcast(players, "BOARD")
            for line in board_str.split("\n"):
                broadcast(players, line)
            broadcast(players, f"INFO 현재 차례: {current['stone']}")

            # 현재 플레이어에게 입력 요구
            send_line(current["sock"], "MOVE 당신의 수를 입력하세요 (row col, 1~15):")

            # 좌표 읽기
            while True:
                line = current["file"].readline()
                if not line:
                    # 연결 끊김
                    broadcast(players, "INFO 상대가 접속을 종료했습니다. 게임을 끝냅니다.")
                    return
                line = line.strip()
                if not line:
                    continue

                try:
                    r_str, c_str = line.split()
                    r = int(r_str) - 1
                    c = int(c_str) - 1
                except ValueError:
                    send_line(current["sock"], "MOVE 형식이 잘못되었습니다. 예: 8 8")
                    continue

                if not in_bounds(r, c):
                    send_line(current["sock"], "MOVE 보드 범위를 벗어났습니다. 1~15 사이로 다시 입력:")
                    continue

                if board[r][c] != EMPTY:
                    send_line(current["sock"], "MOVE 이미 돌이 놓인 자리입니다. 다시 입력:")
                    continue

                # 유효한 수
                board[r][c] = current["stone"]
                break

            # 승리/무승부 체크
            if check_five(board, r, c):
                board_str = board_to_string(board)
                broadcast(players, "")
                broadcast(players, "BOARD")
                for line in board_str.split("\n"):
                    broadcast(players, line)

                broadcast(players, f"RESULT 플레이어 {current['stone']} 승리!")
                break

            # 무승부 (보드 가득 참)
            if all(board[i][j] != EMPTY for i in range(BOARD_SIZE) for j in range(BOARD_SIZE)):
                board_str = board_to_string(board)
                broadcast(players, "")
                broadcast(players, "BOARD")
                for line in board_str.split("\n"):
                    broadcast(players, line)
                broadcast(players, "RESULT 보드가 가득 찼습니다. 무승부!")
                break

            # 턴 넘기기
            turn = 1 - turn

        # 게임 종료
        broadcast(players, "INFO 게임이 종료되었습니다. 서버를 종료합니다.")
        for p in players:
            p["sock"].close()


if __name__ == "__main__":
    game_server()
