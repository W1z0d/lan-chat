import http.server
import socketserver
import urllib.parse
from html import escape
import socket

PORT = 8080
messages = []

def get_local_ip():
    """Получает IP-адрес, используемый для выхода в интернет (обычно это локальный IP в сети)."""
    try:
        # Создаём UDP-сокет и подключаемся к внешнему DNS-серверу (не отправляя данные)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

class ChatHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_html()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            parsed = urllib.parse.parse_qs(post_data.decode('utf-8'))
            message = parsed.get('message', [''])[0].strip()
            if message:
                messages.append(escape(message))
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_error(404)

    def generate_html(self):
        html = """<!DOCTYPE html>
<html>
<head><title>Простой чат</title><meta charset="utf-8"></head>
<body>
<h1>Сообщения</h1>
<form method="post">
    <input type="text" name="message" placeholder="Напишите сообщение..." required>
    <button type="submit">Отправить</button>
</form>
<hr>
<h2>Все сообщения:</h2>
<ul>
"""
        for msg in messages:
            html += f"<li>{msg}</li>"
        html += """
</ul>
</body>
</html>
"""
        return html

# Определяем локальный IP
local_ip = get_local_ip()

# Запуск сервера
with socketserver.TCPServer(("0.0.0.0", PORT), ChatHandler) as httpd:
    print(f"Сервер запущен на порту {PORT}")
    print(f"Доступен в локальной сети по адресу: http://{local_ip}:{PORT}")
    print("Для остановки сервера нажмите Ctrl+C")
    httpd.serve_forever()
