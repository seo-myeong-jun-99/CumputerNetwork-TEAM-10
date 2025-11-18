import socket

HOST = "127.0.0.1"   # 서버 IP (같은 컴퓨터면 그대로)
PORT = 5000


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        rfile = sock.makefile("r", encoding="utf-8")

        print(f"서버({HOST}:{PORT})에 연결됨.")

        while True:
            line = rfile.readline()
            if not line:
                print("서버와의 연결이 종료되었습니다.")
                break
            line = line.rstrip("\n")

            # 서버가 "MOVE ..." 라고 보내면 입력해서 돌리기
            if line.startswith("MOVE"):
                # "MOVE " 뒤에 있는 메시지를 프롬프트로 사용
                prompt = line[4:].strip()
                if not prompt:
                    prompt = "좌표 입력 (row col): "
                else:
                    prompt += " "

                user_input = input(prompt)
                # 사용자가 그냥 엔터 치면 다시 한 번 입력
                while not user_input.strip():
                    user_input = input(prompt)

                sock.sendall((user_input.strip() + "\n").encode("utf-8"))
            else:
                # 그 외의 메시지는 그냥 출력
                print(line)


if __name__ == "__main__":
    main()
