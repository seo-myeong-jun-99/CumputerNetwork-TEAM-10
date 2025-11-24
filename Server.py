# server.py
# HTTP/1.1 기반 오목 서버

import json
import socket
import threading
import uuid

from game import OmokGame, BLACK, WHITE

HOST = "0.0.0.0"
PORT = 6000
MAX_HEADER_BYTES = 16 * 1024
ENCODING = "utf-8"

# 전역 게임 상태와 동기화를 위한 락
game = OmokGame()
lock = threading.Lock()
player_slots = {
    BLACK: None,
    WHITE: None,
}
token_colors = {}
token_names = {}
chat_messages = []
MAX_CHAT = 100
restart_votes = set()

HTTP_STATUS_TEXT = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}


class HttpError(Exception):
    def __init__(self, status, message, extra=None):
        self.status = status
        payload = {"ok": False, "msg": message}
        if extra:
            payload.update(extra)
        self.payload = payload
        super().__init__(message)


def color_to_name(color):
    if color == BLACK:
        return "BLACK"
    if color == WHITE:
        return "WHITE"
    return "SPECTATOR"


def assign_color_locked():
    for color in (BLACK, WHITE):
        if player_slots[color] is None:
            return color
    return None


def build_state_payload():
    return {"ok": True, "state": build_state_locked()}


def players_ready_locked():
    return player_slots[BLACK] is not None and player_slots[WHITE] is not None


def players_info_locked():
    return {
        "black": player_slots[BLACK] is not None,
        "white": player_slots[WHITE] is not None,
        "ready": players_ready_locked(),
    }


def build_state_locked():
    state = game.get_state()
    state["players"] = players_info_locked()
    state["chat"] = chat_messages[-MAX_CHAT:]
    state["restart"] = restart_info_locked()
    return state


def add_chat_locked(name, msg):
    if not msg:
        return
    chat_messages.append({"name": name, "msg": msg})
    if len(chat_messages) > MAX_CHAT * 2:
        del chat_messages[:-MAX_CHAT]


def restart_info_locked():
    black_token = player_slots.get(BLACK)
    white_token = player_slots.get(WHITE)
    return {
        "black": black_token in restart_votes if black_token else False,
        "white": white_token in restart_votes if white_token else False,
    }


def parse_json_body(body):
    if not body:
        return {}
    try:
        return json.loads(body.decode(ENCODING))
    except json.JSONDecodeError:
        raise HttpError(400, "INVALID_JSON")


def handle_join(body):
    name = body.get("name") or "player"
    with lock:
        color = assign_color_locked()
        token = uuid.uuid4().hex
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


def handle_move(body):
    token = body.get("token")
    if not token:
        raise HttpError(400, "TOKEN_REQUIRED")

    color = token_colors.get(token)
    if color is None:
        raise HttpError(400, "INVALID_TOKEN")
    if color not in (BLACK, WHITE):
        raise HttpError(400, "NOT_A_PLAYER")

    x = body.get("x")
    y = body.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        raise HttpError(400, "INVALID_COORD")

    with lock:
        if not players_ready_locked():
            state = build_state_locked()
            raise HttpError(400, "WAITING_FOR_OPPONENT", {"state": state})

        if game.winner is not None:
            state = build_state_locked()
            raise HttpError(400, "GAME_ALREADY_OVER", {"state": state})

        if game.current_turn != color:
            state = build_state_locked()
            raise HttpError(400, "NOT_YOUR_TURN", {"state": state})

        ok, msg = game.place_stone(x, y)
        state = build_state_locked()

    return {"ok": ok, "msg": msg, "state": state}


def handle_state():
    with lock:
        return build_state_payload()


def handle_quit(body):
    token = body.get("token")
    if not token:
        raise HttpError(400, "TOKEN_REQUIRED")

    with lock:
        color = token_colors.pop(token, None)
        name = token_names.pop(token, None)
        restart_votes.discard(token)
        if color in (BLACK, WHITE) and player_slots[color] == token:
            player_slots[color] = None
    if name:
        print(f"[SERVER] quit: name={name} color={color_to_name(color)} token={token[:6]}...")
    return {"ok": True, "msg": "BYE"}


def handle_chat(body):
    token = body.get("token")
    if not token:
        raise HttpError(400, "TOKEN_REQUIRED")
    msg = body.get("msg")
    if not isinstance(msg, str):
        raise HttpError(400, "INVALID_MESSAGE")
    if token not in token_names:
        raise HttpError(400, "INVALID_TOKEN")

    with lock:
        name = token_names.get(token, "player")
        add_chat_locked(name, msg[:200])
        chat = chat_messages[-MAX_CHAT:]
    return {"ok": True, "chat": chat}


def handle_restart(body):
    token = body.get("token")
    if not token:
        raise HttpError(400, "TOKEN_REQUIRED")

    with lock:
        color = token_colors.get(token)
        if color not in (BLACK, WHITE):
            raise HttpError(400, "NOT_A_PLAYER")
        if game.winner is None:
            raise HttpError(400, "GAME_NOT_FINISHED")

        restart_votes.add(token)
        votes = restart_info_locked()
        both_ready = votes["black"] and votes["white"]

        if both_ready:
            game.reset()
            restart_votes.clear()
            state = build_state_locked()
            status = "RESTARTED"
        else:
            state = build_state_locked()
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


def read_http_request(conn):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
        if len(data) > MAX_HEADER_BYTES:
            raise HttpError(400, "HEADER_TOO_LARGE")
    if b"\r\n\r\n" not in data:
        raise HttpError(400, "INVALID_HTTP_REQUEST")

    header_bytes, body = data.split(b"\r\n\r\n", 1)
    header_text = header_bytes.decode("iso-8859-1")
    lines = header_text.split("\r\n")
    if not lines or len(lines[0].split()) < 3:
        raise HttpError(400, "INVALID_REQUEST_LINE")

    request_line = lines[0]
    method, path, _ = request_line.split(maxsplit=2)

    headers = {}
    for line in lines[1:]:
        if not line:
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    content_length = int(headers.get("content-length", "0") or "0")
    while len(body) < content_length:
        chunk = conn.recv(4096)
        if not chunk:
            break
        body += chunk
    if len(body) < content_length:
        raise HttpError(400, "INCOMPLETE_BODY")

    return method.upper(), path, body[:content_length]


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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[SERVER] HTTP listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            conn.settimeout(10)
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    main()
