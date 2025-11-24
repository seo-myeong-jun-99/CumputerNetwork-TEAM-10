# protocol.py
# Simple HTTP/1.1 request helpers for the Omok server

import json
import socket

SERVER_HOST = "172.16.100.87"
SERVER_PORT = 6000
TIMEOUT = 5
USER_AGENT = "OmokHTTPClient/1.0"


def _read_until(sock, marker):
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def _read_http_response(sock):
    data = _read_until(sock, b"\r\n\r\n")
    if b"\r\n\r\n" not in data:
        raise RuntimeError("INVALID_HTTP_RESPONSE")
    header_part, body = data.split(b"\r\n\r\n", 1)
    header_lines = header_part.decode("iso-8859-1").split("\r\n")
    status_line = header_lines[0]
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


def _http_request(method, path, body_bytes):
    lines = [
        f"{method} {path} HTTP/1.1",
        f"Host: {SERVER_HOST}:{SERVER_PORT}",
        f"User-Agent: {USER_AGENT}",
        "Accept: application/json",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close",
    ]
    if body_bytes:
        lines.insert(4, "Content-Type: application/json")
    request_data = "\r\n".join(lines + ["", ""]).encode("utf-8") + body_bytes

    sock = socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=TIMEOUT)
    try:
        sock.sendall(request_data)
        return _read_http_response(sock)
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

    if status >= 400 and data.get("ok", True):
        data["ok"] = False
    data["status"] = status
    return data


def join_server(name="pygame-client"):
    return http_json("POST", "/join", {"name": name})


def request_state():
    return http_json("GET", "/state")


def submit_move(token, x, y):
    return http_json("POST", "/move", {"token": token, "x": x, "y": y})


def quit_game(token):
    return http_json("POST", "/quit", {"token": token})


def send_chat(token, msg):
    return http_json("POST", "/chat", {"token": token, "msg": msg})


def restart_game(token):
    return http_json("POST", "/restart", {"token": token})


def set_server(host=None, port=None):
    global SERVER_HOST, SERVER_PORT
    if host:
        SERVER_HOST = host
    if port:
        SERVER_PORT = port
