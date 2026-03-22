import http.server
import socketserver
import urllib.parse
import json
from html import escape
import socket

START_PORT = 8080
messages = []

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

def find_free_port(start_port):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                port += 1

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class ChatHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

    def safe_write(self, data):
        try:
            self.wfile.write(data)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        try:
            if self.path == '/':
                nick = self.get_cookie('nick')
                if nick is None:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.safe_write(self.nick_form().encode('utf-8'))
                else:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.safe_write(self.chat_page(nick).encode('utf-8'))
            elif self.path == '/api/messages':
                # JSON API для получения сообщений
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                data = json.dumps(messages, ensure_ascii=False)
                self.safe_write(data.encode('utf-8'))
            else:
                self.send_error(404)
        except Exception as e:
            self.log_message("Error in GET: %s", str(e))

    def do_POST(self):
        try:
            if self.path == '/':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                parsed = urllib.parse.parse_qs(post_data.decode('utf-8'))

                if 'nick' in parsed:
                    nick = parsed['nick'][0].strip()
                    if nick:
                        encoded_nick = urllib.parse.quote(nick)
                        self.send_response(303)
                        self.send_header('Location', '/')
                        self.send_header('Set-Cookie', f'nick={encoded_nick}; Max-Age=2592000; Path=/')
                        self.end_headers()
                    else:
                        self.send_error(400, "Ник не может быть пустым")
                    return

                message = parsed.get('message', [''])[0].strip()
                if message:
                    nick_cookie = self.get_cookie('nick')
                    if nick_cookie:
                        full_message = f"{nick_cookie}: {message}"
                        messages.append(escape(full_message))
                        print(f"[Добавлено от браузера] {full_message}")
                    else:
                        if ': ' in message:
                            messages.append(escape(message))
                            print(f"[Добавлено от консоли] {message}")
                        else:
                            print(f"[Игнорировано] сообщение без ника: {message}")
                self.send_response(303)
                self.send_header('Location', '/')
                self.end_headers()
            else:
                self.send_error(404)
        except Exception as e:
            self.log_message("Error in POST: %s", str(e))

    def get_cookie(self, name):
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            for cookie in cookie_header.split(';'):
                cookie = cookie.strip()
                if cookie.startswith(f"{name}="):
                    value = cookie[len(name)+1:]
                    try:
                        return urllib.parse.unquote(value)
                    except:
                        return value
        return None

    def nick_form(self):
        return """<!DOCTYPE html>
<html>
<head><title>Вход в чат</title><meta charset="utf-8"></head>
<body>
<h1>Добро пожаловать в чат</h1>
<form method="post">
    <label>Введите ваш ник:</label>
    <input type="text" name="nick" required>
    <button type="submit">Войти</button>
</form>
</body>
</html>"""

    def chat_page(self, nick):
        return f"""<!DOCTYPE html>
<html>
<head><title>Чат</title><meta charset="utf-8"></head>
<body>
<h1>Чат</h1>
<p>Вы вошли как: <strong>{escape(nick)}</strong></p>
<form id="messageForm" method="post">
    <input type="text" id="messageInput" name="message" placeholder="Напишите сообщение..." required>
    <button type="submit">Отправить</button>
</form>
<hr>
<h2>Все сообщения:</h2>
<ul id="messageList"></ul>

<script>
    let lastCount = 0;

    async function loadMessages() {{
        try {{
            const response = await fetch('/api/messages');
            const messages = await response.json();
            const list = document.getElementById('messageList');
            list.innerHTML = '';
            for (let msg of messages) {{
                const li = document.createElement('li');
                li.textContent = msg;
                list.appendChild(li);
            }}
            lastCount = messages.length;
        }} catch(e) {{
            console.error('Ошибка загрузки сообщений:', e);
        }}
    }}

    // Первоначальная загрузка
    loadMessages();

    // Автообновление каждые 3 секунды
    setInterval(loadMessages, 3000);

    // Отправка сообщения через AJAX без перезагрузки страницы
    const form = document.getElementById('messageForm');
    form.addEventListener('submit', async (e) => {{
        e.preventDefault();
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        if (!message) return;

        try {{
            const formData = new URLSearchParams();
            formData.append('message', message);
            const response = await fetch('/', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                body: formData
            }});
            if (response.ok) {{
                input.value = ''; // очищаем поле
                loadMessages();   // сразу обновляем список
            }}
        }} catch(e) {{
            console.error('Ошибка отправки:', e);
        }}
    }});
</script>
</body>
</html>"""

if __name__ == "__main__":
    local_ip = get_local_ip()
    PORT = find_free_port(START_PORT)
    with ThreadedTCPServer(("0.0.0.0", PORT), ChatHandler) as httpd:
        print(f"Сервер запущен на порту {PORT}")
        print(f"Доступен в локальной сети по адресу: http://{local_ip}:{PORT}")
        print("Для остановки нажмите Ctrl+C")
        httpd.serve_forever()
