# client_pygame.py
# HTTP 오목 클라이언트 (pygame UI)

import socket
import sys
import pygame

from game import BOARD_SIZE, EMPTY, BLACK, WHITE
from protocol import (
    set_server,
    join_server,
    request_state,
    submit_move,
    quit_game,
    send_chat,
)

CELL_SIZE = 40
MARGIN = 40
CHAT_WIDTH = 260
WIDTH = BOARD_SIZE * CELL_SIZE + MARGIN * 2 + CHAT_WIDTH
HEIGHT = BOARD_SIZE * CELL_SIZE + MARGIN * 2

BOARD_COLOR = (200, 170, 120)
LINE_COLOR = (0, 0, 0)
BLACK_COLOR = (0, 0, 0)
WHITE_COLOR = (255, 255, 255)
PLAYER_NAME = "pygame-client"
CHAT_BG = (245, 245, 245)
CHAT_BORDER = (180, 180, 180)
CHAT_TEXT = (30, 30, 30)
CHAT_INPUT_BG = (255, 255, 255)
CHAT_INPUT_BORDER = (120, 120, 120)


def coord_from_mouse(pos):
    mx, my = pos
    x = round((mx - MARGIN) / CELL_SIZE)
    y = round((my - MARGIN) / CELL_SIZE)
    return x, y


def draw_board(screen, state: dict, my_color_name: str):
    board = state["board"]
    players = state.get("players", {})
    waiting = not players.get("ready", True)
    chat_messages = state.get("chat", [])

    screen.fill(BOARD_COLOR)

    # board lines
    for i in range(BOARD_SIZE):
        pygame.draw.line(
            screen,
            LINE_COLOR,
            (MARGIN + i * CELL_SIZE, MARGIN),
            (MARGIN + i * CELL_SIZE, MARGIN + (BOARD_SIZE - 1) * CELL_SIZE),
            1,
        )
        pygame.draw.line(
            screen,
            LINE_COLOR,
            (MARGIN, MARGIN + i * CELL_SIZE),
            (MARGIN + (BOARD_SIZE - 1) * CELL_SIZE, MARGIN + i * CELL_SIZE),
            1,
        )

    # stones
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            stone = board[y][x]
            if stone == EMPTY:
                continue
            color = BLACK_COLOR if stone == BLACK else WHITE_COLOR
            pygame.draw.circle(
                screen,
                color,
                (MARGIN + x * CELL_SIZE, MARGIN + y * CELL_SIZE),
                CELL_SIZE // 2 - 4,
            )

    # info text
    font = pygame.font.SysFont(None, 24)

    txt1 = f"You are {my_color_name}"
    surface1 = font.render(txt1, True, (0, 0, 0))
    screen.blit(surface1, (10, 10))

    winner = state["winner"]
    if winner == BLACK:
        txt2 = "Black wins!"
    elif winner == WHITE:
        txt2 = "White wins!"
    elif winner == 0:
        txt2 = "Draw!"
    elif waiting:
        txt2 = "Waiting for opponent..."
    else:
        turn = "Black" if state["turn"] == BLACK else "White"
        txt2 = f"Turn: {turn}"

    surface2 = font.render(txt2, True, (0, 0, 0))
    screen.blit(surface2, (10, 30))

    return chat_messages, waiting


def draw_chat(screen, chat_messages, input_text):
    font = pygame.font.SysFont(None, 20)
    area_x = WIDTH - CHAT_WIDTH + 10
    area_y = MARGIN
    area_w = CHAT_WIDTH - 20
    area_h = HEIGHT - MARGIN * 2 - 50

    chat_rect = pygame.Rect(area_x - 5, area_y - 5, area_w + 10, area_h + 10)
    pygame.draw.rect(screen, CHAT_BG, chat_rect)
    pygame.draw.rect(screen, CHAT_BORDER, chat_rect, 1)

    # draw messages (latest at bottom)
    line_y = area_y + area_h - 20
    for msg in reversed(chat_messages[-20:]):
        text = f"{msg.get('name', '???')}: {msg.get('msg', '')}"
        surface = font.render(text, True, CHAT_TEXT)
        screen.blit(surface, (area_x, line_y))
        line_y -= 20
        if line_y < area_y:
            break

    # input box
    input_rect = pygame.Rect(area_x - 5, HEIGHT - MARGIN - 40, area_w + 10, 30)
    pygame.draw.rect(screen, CHAT_INPUT_BG, input_rect)
    pygame.draw.rect(screen, CHAT_INPUT_BORDER, input_rect, 1)
    input_surface = font.render(input_text, True, (0, 0, 0))
    screen.blit(input_surface, (input_rect.x + 5, input_rect.y + 5))


def detect_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def main():
    # -------------------------
    # 서버 IP 설정 (입력 없으면 자동 감지)
    # -------------------------
    host_input = ""
    if sys.stdin.isatty():
        host_input = input("서버 주소 입력 (엔터 시 자동 감지): ").strip()
    if host_input:
        host = host_input
    else:
        host = detect_local_ip()
        print(f"서버 호스트를 {host}로 설정합니다.")
    set_server(host)

    # 서버 연결 (입력 없으면 기본 이름)
    name_input = ""
    if sys.stdin.isatty():
        name_input = input(f"접속할 이름 입력 ({PLAYER_NAME} 기본): ").strip()
    player_name = name_input if name_input else PLAYER_NAME

    join_resp = join_server(player_name)
    if not join_resp.get("ok"):
        print("Failed to join server:", join_resp)
        return

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Omok Client (pygame)")

    token = join_resp.get("token")
    color_name = join_resp.get("color", "UNKNOWN")
    state = join_resp.get("state")
    chat_input = ""

    if color_name == "BLACK":
        my_color = BLACK
    elif color_name == "WHITE":
        my_color = WHITE
    else:
        my_color = None

    clock = pygame.time.Clock()
    running = True

    while running:
        clock.tick(30)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    chat_input = chat_input[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    text = chat_input.strip()
                    if text:
                        resp = send_chat(token, text)
                        if not resp.get("ok"):
                            print("Chat send failed:", resp)
                        if resp.get("chat") and state is not None:
                            state["chat"] = resp["chat"]
                    chat_input = ""
                else:
                    if len(chat_input) < 200:
                        chat_input += event.unicode

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state is None:
                    continue
                if state["winner"] is not None:
                    continue
                if my_color is None:
                    print("You are not an active player.")
                    continue
                if state["turn"] != my_color:
                    print("Not your turn.")
                    continue

                x, y = coord_from_mouse(event.pos)
                if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
                    resp = submit_move(token, x, y)
                    if not resp.get("ok"):
                        print("Move rejected:", resp)
                    if resp.get("state"):
                        state = resp["state"]

        resp = request_state()
        if resp.get("ok") and resp.get("state"):
            state = resp["state"]

        chat_messages = []
        if state is not None:
            chat_messages, _ = draw_board(screen, state, color_name)
        else:
            screen.fill(BOARD_COLOR)
        draw_chat(screen, chat_messages, chat_input)
        pygame.display.flip()

    quit_game(token)
    pygame.quit()


if __name__ == "__main__": # 직접 실행과 import할때 구분하기 위해 사용
    main()
