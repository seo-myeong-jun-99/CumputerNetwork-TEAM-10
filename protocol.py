# protocol.py
# Simple HTTP/1.1 request helpers for the Omok server
# client 과 Server가 통신할 수 있게 하는 역할
import json
import socket

SERVER_HOST = "172.16.100.87" #기본값, 학교
SERVER_PORT = 6000
TIMEOUT = 5
USER_AGENT = "OmokHTTPClient/1.0"


def _read_until(sock, marker):
    data = b""
    while marker not in data: #marker(예를들어 \r\n\r\n)가 나올 때 까지 데이터 읽기
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data

# 응답을 해석한다
def _read_http_response(sock): #이부분은 server부분과 동일하게 작동
    data = _read_until(sock, b"\r\n\r\n")
    if b"\r\n\r\n" not in data:
        raise RuntimeError("INVALID_HTTP_RESPONSE")
    header_part, body = data.split(b"\r\n\r\n", 1)
    header_lines = header_part.decode("iso-8859-1").split("\r\n")
    status_line = header_lines[0] #프로토콜 버전 + 상태 코드 + 상태 메시지로 이루어져 있다
    parts = status_line.split(" ", 2)
    if len(parts) < 2:
        raise RuntimeError("INVALID_STATUS_LINE")
    try:
        status_code = int(parts[1])
    except ValueError as exc:
        raise RuntimeError("INVALID_STATUS_CODE") from exc

    headers = {}
    for line in header_lines[1:]:
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    content_length = int(headers.get("content-length", "0") or "0")
    while len(body) < content_length:
        chunk = sock.recv(4096)
        if not chunk:
            break
        body += chunk
    return status_code, headers, body[:content_length]
#200,
# {
#   'content-type': 'application/json',
#   'content-length': '27'
# },
# b'{"ok": true, "msg": "hi"}'

def _http_request(method, path, body_bytes):
    lines = [ #http 메시지 만들기
        f"{method} {path} HTTP/1.1",
        f"Host: {SERVER_HOST}:{SERVER_PORT}",
        f"User-Agent: {USER_AGENT}",
        "Accept: application/json",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close",
    ]
    if body_bytes:
        lines.insert(4, "Content-Type: application/json")
    request_data = "\r\n".join(lines + ["", ""]).encode("utf-8") + body_bytes #최종적으로 이거를 보낼거임

    sock = socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=TIMEOUT) #TCP 연결
    try:
        sock.sendall(request_data) #http요청보내기
        return _read_http_response(sock) #응답받기
    finally:
        sock.close()


def http_json(method, path, payload=None):
    body_bytes = b""
    if payload is not None:
        body_bytes = json.dumps(payload).encode("utf-8")
    try:
        status, _headers, resp_body = _http_request(method, path, body_bytes)
    except (OSError, RuntimeError) as exc:
        return {"ok": False, "msg": f"NETWORK_ERROR: {exc}", "status": None}

    if resp_body:
        try:
            data = json.loads(resp_body.decode("utf-8"))
        except json.JSONDecodeError:
            data = {"ok": False, "msg": "INVALID_SERVER_JSON"}
    else:
        data = {}

    if status >= 400 and data.get("ok", True): #400번대이상이면 ok여도 false로 바꿔주, http 상태코드를 따르기 (json보다 http를 신뢰)
        data["ok"] = False
    data["status"] = status
    return data


#여기 밑에 함수들 "명령 버튼 함수들", 게임에서 하는 행동을 서버에 전달하는 인터페이스

def join_server(name="pygame-client"):#게임방에 입장하기
    return http_json("POST", "/join", {"name": name})


def request_state(): #전체 상태 요청
    return http_json("GET", "/state")


def submit_move(token, x, y):#돌 놓기
    return http_json("POST", "/move", {"token": token, "x": x, "y": y})


def quit_game(token):#게임 종료
    return http_json("POST", "/quit", {"token": token})


def send_chat(token, msg):#채팅메시지 보내기
    return http_json("POST", "/chat", {"token": token, "msg": msg})


def restart_game(token):#게임 재시작
    return http_json("POST", "/restart", {"token": token})


def set_server(host=None, port=None):#서버 주소/포트 변경하는 설정 함수
    global SERVER_HOST, SERVER_PORT
    if host:
        SERVER_HOST = host
    if port:
        SERVER_PORT = port
