# client.py
# HTTP 기반 pygame 오목 클라이언트
#여기는 ui 코드
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
    restart_game,
)


# 화면 그리기
CELL_SIZE = 40
MARGIN = 40
CHAT_WIDTH = 260
TOP_OFFSET = 70  # space for header/status above the board
BOARD_AREA = (BOARD_SIZE - 1) * CELL_SIZE + MARGIN * 2
WIDTH = BOARD_AREA + CHAT_WIDTH
HEIGHT = BOARD_AREA + TOP_OFFSET

BOARD_COLOR = (210, 180, 140)
BOARD_SHADOW = (165, 135, 100)
BACKGROUND = (228, 214, 192)
LINE_COLOR = (55, 35, 15)
BLACK_COLOR = (15, 15, 15)
WHITE_COLOR = (245, 245, 245)
PLAYER_NAME = "pygame-client"

INFO_BAR = (245, 232, 210)
TEXT_MAIN = (40, 35, 30)
TEXT_DIM = (100, 90, 80)
RESTART_ACTIVE = (32, 138, 160)
RESTART_DISABLED = (170, 170, 170)

CHAT_BG = (248, 246, 242)
CHAT_BORDER = (200, 190, 180)
CHAT_TITLE_BG = (235, 226, 214)
CHAT_TEXT = (35, 30, 25)
CHAT_INPUT_BG = (255, 255, 255)
CHAT_INPUT_BORDER = (140, 130, 120)

# 마우스로 좌표 클릭 -> 오목 좌표
def coord_from_mouse(pos):
    mx, my = pos
    x = round((mx - MARGIN) / CELL_SIZE)
    y = round((my - (TOP_OFFSET + MARGIN)) / CELL_SIZE)
    return x, y


def draw_board(screen, state: dict, my_color_name: str, can_restart: bool, fonts): #오목판 그리기
    board = state["board"]
    players = state.get("players", {})
    waiting = not players.get("ready", True)
    chat_messages = state.get("chat", [])
    winner = state["winner"]
    restart_info = state.get("restart", {})

    screen.fill(BACKGROUND)

    board_rect = pygame.Rect(0, TOP_OFFSET, BOARD_AREA, BOARD_AREA)
    pygame.draw.rect(screen, BOARD_SHADOW, board_rect.move(6, 6), border_radius=10)
    pygame.draw.rect(screen, BOARD_COLOR, board_rect, border_radius=10)

    board_origin_y = TOP_OFFSET + MARGIN

    # 선
    for i in range(BOARD_SIZE):
        pygame.draw.line(
            screen,
            LINE_COLOR,
            (MARGIN + i * CELL_SIZE, board_origin_y),
            (MARGIN + i * CELL_SIZE, board_origin_y + (BOARD_SIZE - 1) * CELL_SIZE),
            1,
        )
        pygame.draw.line(
            screen,
            LINE_COLOR,
            (MARGIN, board_origin_y + i * CELL_SIZE),
            (MARGIN + (BOARD_SIZE - 1) * CELL_SIZE, board_origin_y + i * CELL_SIZE),
            1,
        )

    # 돌
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            stone = board[y][x]
            if stone == EMPTY:
                continue
            color = BLACK_COLOR if stone == BLACK else WHITE_COLOR
            pygame.draw.circle(
                screen,
                color,
                (MARGIN + x * CELL_SIZE, board_origin_y + y * CELL_SIZE),
                CELL_SIZE // 2 - 4,
            )

    # info + status bar
    header_rect = pygame.Rect(12, 8, BOARD_AREA - 24, 32)
    pygame.draw.rect(screen, INFO_BAR, header_rect, border_radius=8)

    txt1 = f"You are {my_color_name}"
    surface1 = fonts["label"].render(txt1, True, TEXT_MAIN)
    screen.blit(surface1, (header_rect.x + 12, header_rect.y + 6))

    restart_rect = pygame.Rect(header_rect.right - 140, header_rect.y + 4, 126, 24)
    btn_label = "Restart (R)" if can_restart else "Restart"

    def paint_restart():
        btn_color = RESTART_ACTIVE if can_restart else RESTART_DISABLED
        pygame.draw.rect(screen, btn_color, restart_rect, border_radius=6)
        surface_btn = fonts["small"].render(btn_label, True, (245, 245, 245))
        screen.blit(surface_btn, surface_btn.get_rect(center=restart_rect.center))

    paint_restart()

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

    surface2 = fonts["label"].render(txt2, True, TEXT_MAIN)
    screen.blit(surface2, (header_rect.x + 10, header_rect.bottom + 6))

    # 승리 시 가운데에 나타내기
    if winner is not None:
        overlay = pygame.Surface((BOARD_AREA, BOARD_AREA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, TOP_OFFSET))

        title_surface = fonts["banner"].render(txt2, True, (255, 255, 255))
        title_rect = title_surface.get_rect(
            center=(BOARD_AREA // 2, TOP_OFFSET + BOARD_AREA // 2 - 10)
        )
        screen.blit(title_surface, title_rect)

        # 재시작
        my_key = my_color_name.lower()
        other_key = "white" if my_key == "black" else "black"
        my_req = restart_info.get(my_key, False)
        opp_req = restart_info.get(other_key, False)

        if my_req and not opp_req:
            subtitle = "Restart requested. Waiting for opponent..."
        elif opp_req and not my_req:
            subtitle = "Opponent wants a rematch. Press R to accept."
        else:
            subtitle = "Press R or click Restart to play again."

        subtitle_surface = fonts["banner_sub"].render(subtitle, True, (235, 235, 235))
        subtitle_rect = subtitle_surface.get_rect(
            center=(BOARD_AREA // 2, TOP_OFFSET + BOARD_AREA // 2 + 30)
        )
        screen.blit(subtitle_surface, subtitle_rect)

        # bring the restart button above the overlay
        paint_restart()

    return chat_messages, waiting, restart_rect

#채팅 UI 그리기
def draw_chat(screen, chat_messages, input_text, fonts):
    title_rect = pygame.Rect(BOARD_AREA + 10, 8, CHAT_WIDTH - 20, 26)
    pygame.draw.rect(screen, CHAT_TITLE_BG, title_rect, border_radius=6)
    title_surface = fonts["label"].render("Chat", True, TEXT_MAIN)
    screen.blit(title_surface, (title_rect.x + 10, title_rect.y + 4))

    area_x = BOARD_AREA + 10
    area_y = title_rect.bottom + 6
    area_w = CHAT_WIDTH - 20
    area_h = HEIGHT - MARGIN * 2 - 50

    chat_rect = pygame.Rect(area_x - 2, area_y - 2, area_w + 4, area_h + 4)
    pygame.draw.rect(screen, CHAT_BG, chat_rect)
    pygame.draw.rect(screen, CHAT_BORDER, chat_rect, 1)

    font = fonts["small"]
    # draw messages (latest at bottom)
    line_y = area_y + area_h - 22
    for msg in reversed(chat_messages[-20:]): #최근 20개를 역순으로 출력해서 스크롤 느낌을 만듦
        text = f"{msg.get('name', '???')}: {msg.get('msg', '')}"
        surface = font.render(text, True, CHAT_TEXT)
        screen.blit(surface, (area_x + 4, line_y))
        line_y -= 20
        if line_y < area_y:
            break

    if not chat_messages:
        placeholder = font.render("No messages yet. Say hi!", True, TEXT_DIM) # 채팅이 하나도 없을 경우 이 문구를 표시함
        screen.blit(placeholder, (area_x + 4, area_y + 4))

    # 입력창
    input_rect = pygame.Rect(area_x - 2, HEIGHT - MARGIN - 40, area_w + 4, 32)
    pygame.draw.rect(screen, CHAT_INPUT_BG, input_rect)
    pygame.draw.rect(screen, CHAT_INPUT_BORDER, input_rect, 1)
    input_surface = font.render(input_text, True, (0, 0, 0))
    screen.blit(input_surface, (input_rect.x + 6, input_rect.y + 6))

    hint = fonts["tiny"].render("Enter to send • Esc to quit", True, TEXT_DIM)
    screen.blit(hint, (input_rect.x, input_rect.bottom + 4))

#로컬로 돌릴때 편의를 위함. 자동으로 ip 찾기
def detect_local_ip(): #사용자가 서버 주소를 안 치고 그냥 엔터 치면, 이 컴퓨터의 로컬 IP를 자동으로 찾아주는 역할
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #소켓을 만듦
        s.connect(("8.8.8.8", 80)) # 구글 DNS인 (8,8,8,8)로 연결을 시도해보면 OS가 어떤 IP로 나갈 지 결정
        ip = s.getsockname()[0] # 그 IP를 getsockname()에서 알 수 있음
    except Exception:
        ip = "127.0.0.1" # 이 방법이 실패하면 그냥 (127.0.0.1)을 쓰도록 함
    finally:
        s.close()
    return ip #최종 IP문자열 반환


def main():
    host_input = ""
    if sys.stdin.isatty():
        host_input = input("서버 주소 입력 (빈칸 시 자동 감지): ").strip()
    if host_input:
        host = host_input
    else:
        host = detect_local_ip()
        print(f"로컬 호스트를 {host}로 사용합니다.")
    set_server(host)

    name_input = ""
    if sys.stdin.isatty():
        name_input = input(f"플레이어 이름 입력 ({PLAYER_NAME} 기본): ").strip()
    player_name = name_input if name_input else PLAYER_NAME

    join_resp = join_server(player_name)
    if not join_resp.get("ok"):
        print("Failed to join server:", join_resp)
        return

    pygame.init() #pygame 시작
    screen = pygame.display.set_mode((WIDTH, HEIGHT)) #화면 열기
    pygame.display.set_caption("Omok Client (pygame)")

    fonts = { #폰트 설정
        "label": pygame.font.SysFont("bahnschrift", 20),
        "small": pygame.font.SysFont("bahnschrift", 16),
        "tiny": pygame.font.SysFont("bahnschrift", 12),
        "banner": pygame.font.SysFont("bahnschrift", 64),
        "banner_sub": pygame.font.SysFont("bahnschrift", 26),
    }

    token = join_resp.get("token")
    color_name = join_resp.get("color", "UNKNOWN")
    state = join_resp.get("state")
    chat_input = ""
    restart_rect = None

    if color_name == "BLACK":
        my_color = BLACK #흑돌
    elif color_name == "WHITE":
        my_color = WHITE #백돌
    else:
        my_color = None #관전자

    clock = pygame.time.Clock() #FPS 조절용
    running = True #메인루프 가동 여부

    while running:
        clock.tick(30) # FPS를 30으로 제한

        can_restart = ( #게임이 끝나고 내가 플레이어일 경우 True
            state is not None and state.get("winner") is not None and my_color in (BLACK, WHITE)
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT: # 창 닫힐 경우
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_BACKSPACE: 
                    chat_input = chat_input[:-1]
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    text = chat_input.strip()
                    if text: # 채팅 전송
                        resp = send_chat(token, text)
                        if not resp.get("ok"):
                            print("Chat send failed:", resp)
                        if resp.get("chat") and state is not None:
                            state["chat"] = resp["chat"]
                    chat_input = ""
                elif event.key == pygame.K_r:
                    if can_restart:
                        resp = restart_game(token)
                        if resp.get("state"):
                            state = resp["state"]
                    else:
                        print("Restart is available after a finished game.")
                else:
                    if len(chat_input) < 200: # 채팅 최대 200자 제한
                        chat_input += event.unicode

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if restart_rect and restart_rect.collidepoint(event.pos):
                    if can_restart: # 게임 다시시작
                        resp = restart_game(token)
                        if resp.get("state"):
                            state = resp["state"]
                    continue

                if state is None:
                    continue
                if state["winner"] is not None:
                    continue
                if my_color is None: #관전자일 경우
                    print("You are not an active player.")
                    continue
                if state["turn"] != my_color: #내 차례가 아닐경우
                    print("Not your turn.")
                    continue

                x, y = coord_from_mouse(event.pos)
                if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
                    resp = submit_move(token, x, y)
                    if not resp.get("ok"):
                        print("Move rejected:", resp)
                    if resp.get("state"):
                        state = resp["state"]

        resp = request_state() #서버에 현재 상태 요청
        if resp.get("ok") and resp.get("state"):
            state = resp["state"] #state가 있으면 로컬 state를 그 값으로 바꿈 

        chat_messages = []
        if state is not None:
            chat_messages, _waiting, restart_rect = draw_board(
                screen, state, color_name, can_restart, fonts
            )
        else:
            screen.fill(BACKGROUND)
            restart_rect = None

        draw_chat(screen, chat_messages, chat_input, fonts) #채팅 영역 그리기
        pygame.display.flip() #실제 화면에 렌더링 결과 반영

    quit_game(token)
    pygame.quit()


if __name__ == "__main__":  # 모듈로 import될 때 실행 방지
    main()
