import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from pprint import pprint
import requests
from tokens import APP_ID
from User import User
from vk_auth import gen_state
from tokens import AUTH_REDIRECT_URI, AUTH_SERVER_PORT


class CustomHandler(http.server.BaseHTTPRequestHandler):

    # Отключаем системные логи
    def log_message(self, format, *args):
        return

    def log_request_details(self):
        # print("\n\n========================")
        # print("===== Новый запрос =====\n")

        # Метод и путь
        # print(f"Метод: {self.command}")
        # print(f"Путь: {self.path}")

        # Парсинг URL
        parsed = urlparse(self.path)
        # print(f" • Путь без параметров: {parsed.path}")
        # print(f" • Параметры строки: {parsed.query}")
        # print(" • Query параметры: ")
        # pprint(parse_qs(parsed.query))

        # IP клиента
        # print(f"Клиент: {self.client_address[0]}:{self.client_address[1]}")

        # Заголовки
        # print("\n-- Заголовки --")
        # for key, value in self.headers.items():
        #     print(f"{key}: {value}")

        # Куки
        # print("\n-- Cookies --")
        # cookies = self.headers.get("Cookie")
        # if cookies:
        #     print(cookies)
        # else:
        #     print("(нет)")

        # Тело запроса (если есть)
        content_length = self.headers.get("Content-Length")
        if content_length:
            length = int(content_length)
            body = self.rfile.read(length)
            # print("\n-- Тело запроса --")
            # print(body)
        # else:
        #     print("\n-- Тело запроса отсутствует --")

        # print("========================\n")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/auth":
            self.log_request_details()
            qs = parse_qs(parsed.query)
            state = qs["state"][0]
            uid = state[: state.index("_")]
            # print(uid)
            user = User(uid)
            state_0 = gen_state(user.code_verifier, uid)
            # pprint(user)
            # print(state == state_0)

            url = "https://id.vk.ru/oauth2/auth"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "grant_type": "authorization_code",
                "device_id": qs["device_id"][0],
                "client_id": APP_ID,
                "redirect_uri": AUTH_REDIRECT_URI,  # "https://xqmtsvml-8899.euw.devtunnels.ms/auth",
                "code": qs["code"][0],
                "code_verifier": user.code_verifier,
                "state": state,
            }
            # pprint(data)

            response = requests.post(
                url, headers=headers, params=data, data=data
            )  # данные как form-data
            # print(response.status_code)
            json = response.json()
            # pprint(json)
            if json.get("error"):
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(
                    str(json["error"] + ": " + json["error_description"]).encode(
                        "utf-8"
                    )
                )
                return

            # print(type(json))
            # print(str(json["user_id"]) == str(uid))
            # print(json["state"] == state)
            # print(len(json["access_token"]))
            # print(len(json["refresh_token"]))
            # print(len(qs["device_id"][0]))
            if json["access_token"] and json["refresh_token"]:
                user.access_token = json["access_token"]
                user.refresh_token = json["refresh_token"]
                user.device_id = qs["device_id"][0]
                user.save()

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        self.wfile.write(
            "Успешно! Это окно теперь можно закрыть и вернуться к боту.".encode("utf-8")
        )

    # def do_POST(self):
    #     self.log_request_details()

    #     self.send_response(200)
    #     self.send_header("Content-type", "text/plain")
    #     self.end_headers()
    #     self.wfile.write(b"POST received")

    # # При желании можно включить PUT, DELETE и др.
    # def do_PUT(self):
    #     self.log_request_details()
    #     self.send_response(200)
    #     self.end_headers()
    #     self.wfile.write(b"PUT received")

    # def do_DELETE(self):
    #     self.log_request_details()
    #     self.send_response(200)
    #     self.end_headers()
    #     self.wfile.write(b"DELETE received")


# PORT = 8899
with socketserver.TCPServer(("", AUTH_SERVER_PORT), CustomHandler) as httpd:
    # print(f"Сервер запущен на порту {PORT}")
    httpd.serve_forever()
