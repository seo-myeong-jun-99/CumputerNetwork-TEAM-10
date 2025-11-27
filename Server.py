# server.py
# HTTP/1.1 기반 오목 서버

import json
import socket
import threading
import uuid

from game import OmokGame, BLACK, WHITE

HOST = "0.0.0.0" #모든 ip에게서 접속을 받겠다는 의미
PORT = 6000 #포트번호
MAX_HEADER_BYTES = 16 * 1024 #http 헤더가 너무 길면 거절하기(서버에 메모리 너무 많이 들어오는거 막기)
ENCODING = "utf-8" #인코딩

# 전역 게임 상태와 동기화를 위한 락 (게임 상태 기억하기)
game = OmokGame()
lock = threading.Lock()  #서버의 중요한 처리 구간을 한 번에 하나만 실행하게 만드는 장치
player_slots = { #흑백 자리에 누가 앉을지
    BLACK: None,
    WHITE: None,
}
token_colors = {} #black, white, none
token_names = {} # 이름
chat_messages = [] #서버가 저장하고 있는 채팅내역
MAX_CHAT = 100 # 서버가 보관하는 채팅 개수
restart_votes = set() # 다시하기 누른 플레이어 들의 토큰 목록

HTTP_STATUS_TEXT = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}

# HTTP 에러 응답을 만들기 위한 사용자 정의 예외 클래스
class HttpError(Exception):
    def __init__(self, status, message, extra=None):
        self.status = status
        payload = {"ok": False, "msg": message}
        if extra:
            payload.update(extra)
        self.payload = payload
        super().__init__(message)


def color_to_name(color): # 색을 글자로 리턴하기 위한 함수
    if color == BLACK:
        return "BLACK"
    if color == WHITE:
        return "WHITE"
    return "SPECTATOR"


def assign_color_locked(): #자리가 비어있으면 자리 지정해주기
    for color in (BLACK, WHITE): #흑을 먼저 지정해준다
        if player_slots[color] is None:
            return color
    return None #만약 둘다 차있으면 관전자로 배정해준다.


def build_state_payload(): # 게임 상태 응답 포장용
    return {"ok": True, "state": build_state_locked()}


def players_ready_locked(): #흑백 둘다 있는상태
    return player_slots[BLACK] is not None and player_slots[WHITE] is not None


def players_info_locked(): #흑백 들어와있는지 확인
    return {
        "black": player_slots[BLACK] is not None,
        "white": player_slots[WHITE] is not None,
        "ready": players_ready_locked(),
    }


def build_state_locked(): #게임 상태 저장, 플레이어, 채팅, 재시작
    state = game.get_state()
    state["players"] = players_info_locked()
    state["chat"] = chat_messages[-MAX_CHAT:]
    state["restart"] = restart_info_locked()
    return state


def add_chat_locked(name, msg):
    if not msg: #빈 채팅 입력시 무시
        return
    chat_messages.append({"name": name, "msg": msg})
    if len(chat_messages) > MAX_CHAT * 2: #너무 로그 너무 쌓이면 앞부분 날리기
        del chat_messages[:-MAX_CHAT]


def restart_info_locked(): #다시 시작 하기 누가 눌렀는 확인하기 위한 함수
    black_token = player_slots.get(BLACK)
    white_token = player_slots.get(WHITE)
    return {
        "black": black_token in restart_votes if black_token else False,
        "white": white_token in restart_votes if white_token else False,
    }

# 클라이언트가 보낸 body를 JSON 형식으로 파싱하여 dict로 변환
# JSON 형식이 잘못되면 INVALID_JSON 에러 발생
def parse_json_body(body):
    if not body:
        return {}
    try:
        return json.loads(body.decode(ENCODING))
    except json.JSONDecodeError:
        raise HttpError(400, "INVALID_JSON")

# 새로 들어온 유저에게 색을 배정하고, 토큰을 만들어 저장한 뒤,
# 현재 게임 상태와 함께 그 정보를 돌려주는 함수
def handle_join(body):
    name = body.get("name") or "player"
    with lock:
        color = assign_color_locked()
        token = uuid.uuid4().hex # 플레이어 식별을 위한 토큰 생성
        token_colors[token] = color
        token_names[token] = name
        if color in (BLACK, WHITE):
            player_slots[color] = token
        state = build_state_locked()
    print(f"[SERVER] join: name={name} color={color_to_name(color)} token={token[:6]}...")
    return {
        "ok": True,
        "color": color_to_name(color),
        "token": token,
        "state": state,
    }

#오목판에서 돌을 두는 것을 제어하는 역할을 하는 함수
def handle_move(body):
    token = body.get("token") #토큰이 있어야 하며
    if not token:
        raise HttpError(400, "TOKEN_REQUIRED")

    color = token_colors.get(token) #유효한 토큰이어야 한다
    if color is None:
        raise HttpError(400, "INVALID_TOKEN")
    if color not in (BLACK, WHITE): #관전자는 돌을 둘 수 없다
        raise HttpError(400, "NOT_A_PLAYER")

    x = body.get("x") #x,y가 숫자가 아니면 거절한다
    y = body.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        raise HttpError(400, "INVALID_COORD")

    with lock: #이 안에서만 게임을 변경한다
        if not players_ready_locked(): #흑백 둘다 있어야하며
            state = build_state_locked()
            raise HttpError(400, "WAITING_FOR_OPPONENT", {"state": state})

        if game.winner is not None: #누가 이겼으면 수를 더 둘 수 없음
            state = build_state_locked()
            raise HttpError(400, "GAME_ALREADY_OVER", {"state": state})

        if game.current_turn != color:
            state = build_state_locked() #내 턴인지 확인하기
            raise HttpError(400, "NOT_YOUR_TURN", {"state": state})

        ok, msg = game.place_stone(x, y) #실제로 돌 두기
        state = build_state_locked() #변경된 사항을 전달하기, 이를 클라이언트에게도 전달

    return {"ok": ok, "msg": msg, "state": state}

# 현재 게임 상태를 알려주는 함수
def handle_state():
    with lock:
        return build_state_payload()

# 플레이어 나가기 처리용
def handle_quit(body):
    token = body.get("token")
    if not token:
        raise HttpError(400, "TOKEN_REQUIRED")

    with lock:
        color = token_colors.pop(token, None)
        name = token_names.pop(token, None)
        restart_votes.discard(token)
        if color in (BLACK, WHITE) and player_slots[color] == token:
            player_slots[color] = None #나가는 플레이어의 색깔 자리를 비워줌, ex) 흑이 나가면 다음에 들어오는 사람이 흑이됨,
            # 참고로 관전자가 자동으로 플레이어가 되지는 않음
    if name:
        print(f"[SERVER] quit: name={name} color={color_to_name(color)} token={token[:6]}...")
    return {"ok": True, "msg": "BYE"}

# 채팅을 서버로 보내는 요청을 처리하는 함수
def handle_chat(body):
    token = body.get("token")
    if not token: # 누가 보낸지 알기(token확인)
        raise HttpError(400, "TOKEN_REQUIRED")
    msg = body.get("msg") # 문자열인지 확인하기, 이상한 타(숫자, dict)등은 안됨.
    # 참고로 사용자가 입력하는 숫자는 어차피 문자열로 처리돼서 상관없음
    if not isinstance(msg, str): #타입 확인
        raise HttpError(400, "INVALID_MESSAGE")
    if token not in token_names: # 토큰이 등록된 토큰인지
        raise HttpError(400, "INVALID_TOKEN")

    with lock:#실제 실행되는 부분
        name = token_names.get(token, "player")#이름찾기, player가 기본값
        add_chat_locked(name, msg[:200]) # 실제로 채팅을 저장하는 부분, 최대 200글자로 제한하기
        chat = chat_messages[-MAX_CHAT:] # 채팅 로그 너무 길어지면 자르기
    return {"ok": True, "chat": chat}

#재경기를 위한 로직
def handle_restart(body):
    token = body.get("token")
    if not token: #누가 시작했는지 알기 위해 토큰 검사
        raise HttpError(400, "TOKEN_REQUIRED")

    with lock:# 서버혼자 작업시작
        color = token_colors.get(token)
        if color not in (BLACK, WHITE):# 현재 플레이어만 재시작 가능하게
            raise HttpError(400, "NOT_A_PLAYER")
        if game.winner is None: # 게임이 끝난 상태여야 함
            raise HttpError(400, "GAME_NOT_FINISHED")

        restart_votes.add(token)
        votes = restart_info_locked()
        both_ready = votes["black"] and votes["white"]

        if both_ready: # 둘다 재시작 동의하면
            game.reset() #게임 재시작
            restart_votes.clear()
            state = build_state_locked()
            status = "RESTARTED"
        else:
            state = build_state_locked() # 계속 기다리는 상태로 유지
            status = "PENDING"

    name = token_names.get(token, "player")
    print(
        f"[SERVER] restart requested by {name} ({color_to_name(color)}) status={status}"
    )
    return {"ok": True, "state": state, "status": status}


def route_request(method, path, body):
    if method == "POST" and path == "/join":
        return handle_join(parse_json_body(body))
    if method == "POST" and path == "/move":
        return handle_move(parse_json_body(body))
    if method == "POST" and path == "/quit":
        return handle_quit(parse_json_body(body))
    if method == "POST" and path == "/chat":
        return handle_chat(parse_json_body(body))
    if method == "POST" and path == "/restart":
        return handle_restart(parse_json_body(body))
    if method == "GET" and path == "/state":
        return handle_state()
    if path not in {"/join", "/move", "/quit", "/state", "/chat", "/restart"}:
        raise HttpError(404, "NOT_FOUND")
    raise HttpError(405, "METHOD_NOT_ALLOWED")

# HTTP 요청을 파싱하는 역할
# POST /move HTTP/1.1\r\n
# Host: 127.0.0.1:6000\r\n
# Content-Length: 26\r\n
# \r\n
# {"x":5,"y":7,"token":"abc"}
# 이런식으로 들어옴
def read_http_request(conn):
    data = b""
    while b"\r\n\r\n" not in data: # 헤더와 본문 나누기
        chunk = conn.recv(4096) #클라이언트가 보낸 글자를 읽는다
        if not chunk:
            break
        data += chunk
        if len(data) > MAX_HEADER_BYTES: #헤더가 너무 크면 차단하기
            raise HttpError(400, "HEADER_TOO_LARGE")
    if b"\r\n\r\n" not in data: # 헤더가 제대로 안왔으면 에러
        raise HttpError(400, "INVALID_HTTP_REQUEST")

    header_bytes, body = data.split(b"\r\n\r\n", 1) #헤더와 바디를 나눈다
    header_text = header_bytes.decode("iso-8859-1") #헤더 텍스트 파싱
    lines = header_text.split("\r\n")
    if not lines or len(lines[0].split()) < 3: #http 요청의 첫줄이 최소한 method path version을 지키고 있는지 확인하는 안전장치
        #헤더가 아예없거나, 첫 줄이 최소한 3부분(메서드,경로,버전)으로 안나뉘면 400에러 날리기
        raise HttpError(400, "INVALID_REQUEST_LINE")

    request_line = lines[0]
    method, path, _ = request_line.split(maxsplit=2) #method, path 추출

    headers = {} #헤더를 딕셔너리로 변환
    for line in lines[1:]:
        if not line:
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    #바디 길이 만큼 추가로 받기
    content_length = int(headers.get("content-length", "0") or "0")
    while len(body) < content_length:
        chunk = conn.recv(4096)
        if not chunk:
            break
        body += chunk
    if len(body) < content_length:
        raise HttpError(400, "INCOMPLETE_BODY")

    return method.upper(), path, body[:content_length]

#서버가 만든 데이터 → HTTP 규칙에 맞는 문자열로 만들어서 보낸다
def send_http_response(conn, status, payload):
    body = json.dumps(payload).encode(ENCODING)
    status_text = HTTP_STATUS_TEXT.get(status, "")
    headers = [
        f"HTTP/1.1 {status} {status_text}",
        "Content-Type: application/json",
        f"Content-Length: {len(body)}",
        "Connection: close",
        "",
        "",
    ]
    conn.sendall("\r\n".join(headers).encode(ENCODING) + body)

# 요청 읽고 답장을 보내는
def handle_client(conn, addr):
    try:
        method, path, body = read_http_request(conn)
        response = route_request(method, path, body)
        send_http_response(conn, 200, response)
    except HttpError as err:
        send_http_response(conn, err.status, err.payload)
    except Exception as exc:
        print(f"[SERVER] internal error for {addr}: {exc}")
        send_http_response(conn, 500, {"ok": False, "msg": "SERVER_ERROR"})
    finally:
        conn.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: #소캣: 통신 창, with 써서 프로그램 끝나면 소캣 닫힘
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #오류 방지용
        s.bind((HOST, PORT)) #소캣을 host:port에 연결
        s.listen() #연결 요청 받는 모드로 전환
        print(f"[SERVER] HTTP listening on {HOST}:{PORT}")

        while True: #서버 무한루프 돌리기
            conn, addr = s.accept()#누군가 접속하면
            conn.settimeout(10)# 근데 응답 없으면 끊어버리기
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True) #비유적으로 손님 받을 직원을 만드는 과정
            t.start() #실제로 작업 시작


if __name__ == "__main__":
    main()
