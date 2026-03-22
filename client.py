import urllib.request
import urllib.parse
import sys
import json
import http.cookiejar
import threading
import time
import socket

class ChatClient:
    def __init__(self, server_url):
        self.server_url = server_url.rstrip('/')
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))

    def send_nick(self, nick):
        data = urllib.parse.urlencode({'nick': nick}).encode('utf-8')
        try:
            req = urllib.request.Request(self.server_url, data=data, method='POST')
            self.opener.open(req)
            return True
        except Exception as e:
            print(f"Ошибка при отправке ника: {e}")
            return False

    def get_messages_json(self):
        try:
            response = self.opener.open(self.server_url + '/api/messages')
            data = response.read().decode('utf-8')
            return json.loads(data)
        except Exception as e:
            print(f"Ошибка получения сообщений: {e}")
            return None

    def send_message(self, message):
        data = urllib.parse.urlencode({'message': message}).encode('utf-8')
        try:
            req = urllib.request.Request(self.server_url, data=data, method='POST')
            self.opener.open(req)
            return True
        except Exception as e:
            print(f"Ошибка при отправке: {e}")
            return False

def show_all_messages(messages):
    if not messages:
        print("Сообщений пока нет.")
        return
    print("\n=== Все сообщения ===")
    for i, msg in enumerate(messages, 1):
        print(f"{i}. {msg}")

def show_new_messages(messages, old_messages):
    if not messages:
        print("Сообщений пока нет.")
        return
    new_msgs = [msg for msg in messages if msg not in old_messages]
    if new_msgs:
        print("\n=== Новые сообщения ===")
        for i, msg in enumerate(new_msgs, 1):
            print(f"{i}. {msg}")
    else:
        print("Новых сообщений нет.")

def discover_servers(timeout=5):
    """Слушает broadcast на порту 44444 и возвращает список URL найденных серверов."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 44444))
    sock.settimeout(timeout)
    servers = set()
    print(f"Поиск серверов в сети (ожидание {timeout} сек)...")
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            msg = data.decode('utf-8')
            if msg.startswith('CHAT_SERVER:'):
                url = msg.split(':', 1)[1]
                servers.add(url)
    except socket.timeout:
        pass
    finally:
        sock.close()
    return sorted(servers)

def auto_refresh_worker(client, stop_event, callback):
    while not stop_event.is_set():
        time.sleep(3)
        if stop_event.is_set():
            break
        messages = client.get_messages_json()
        if messages is not None:
            callback(messages)

def main():
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = None

    if server_url is None:
        # Пытаемся обнаружить сервер автоматически
        found = discover_servers()
        if found:
            print("Найденные серверы:")
            for i, url in enumerate(found, 1):
                print(f"{i}. {url}")
            choice = input("Введите номер сервера или адрес вручную: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(found):
                server_url = found[int(choice)-1]
            else:
                server_url = choice
        else:
            server_url = input("Введите адрес сервера (например, http://192.168.31.43:8080): ").strip()
            if not server_url:
                server_url = "http://localhost:8080"

    nick = input("Введите ваш ник: ").strip()
    if not nick:
        print("Ник не может быть пустым. Завершение.")
        return

    client = ChatClient(server_url)

    print("Подключение к серверу...")
    if not client.send_nick(nick):
        print("Не удалось установить соединение.")
        return

    print(f"Консольный клиент чата (ник: {nick})")
    print("Доступные команды:")
    print("  all      - показать все сообщения")
    print("  new      - показать новые сообщения")
    print("  send     - отправить сообщение")
    print("  auto     - включить/выключить автообновление")
    print("  discover - поиск других серверов в сети")
    print("  connect <url> - подключиться к другому серверу")
    print("  exit     - выход")
    print("-" * 50)

    all_msgs = client.get_messages_json()
    if all_msgs is None:
        return
    show_all_messages(all_msgs)
    last_msgs = all_msgs.copy()

    auto_refresh_enabled = False
    stop_auto_event = threading.Event()
    auto_thread = None

    def on_auto_refresh(messages):
        nonlocal last_msgs
        if messages and messages != last_msgs:
            new_msgs = [msg for msg in messages if msg not in last_msgs]
            if new_msgs:
                print("\n[Автообновление] Новые сообщения:")
                for i, msg in enumerate(new_msgs, 1):
                    print(f"  {i}. {msg}")
                last_msgs = messages.copy()

    def set_auto_refresh(enabled):
        nonlocal auto_refresh_enabled, auto_thread, stop_auto_event
        if enabled and not auto_refresh_enabled:
            auto_refresh_enabled = True
            stop_auto_event.clear()
            auto_thread = threading.Thread(target=auto_refresh_worker, args=(client, stop_auto_event, on_auto_refresh), daemon=True)
            auto_thread.start()
            print("Автообновление включено (каждые 3 сек).")
        elif not enabled and auto_refresh_enabled:
            auto_refresh_enabled = False
            stop_auto_event.set()
            if auto_thread:
                auto_thread.join(timeout=1)
            print("Автообновление выключено.")

    try:
        while True:
            cmd = input("\nВведите команду: ").strip().lower()
            if cmd == "exit":
                set_auto_refresh(False)
                print("Выход.")
                break
            elif cmd == "all":
                all_msgs = client.get_messages_json()
                if all_msgs is None:
                    continue
                show_all_messages(all_msgs)
                last_msgs = all_msgs.copy()
            elif cmd == "new":
                all_msgs = client.get_messages_json()
                if all_msgs is None:
                    continue
                show_new_messages(all_msgs, last_msgs)
                last_msgs = all_msgs.copy()
            elif cmd == "send":
                msg = input("Введите сообщение: ").strip()
                if not msg:
                    print("Сообщение не может быть пустым.")
                    continue
                if client.send_message(msg):
                    print("Сообщение отправлено.")
                    all_msgs = client.get_messages_json()
                    if all_msgs is not None:
                        show_new_messages(all_msgs, last_msgs)
                        last_msgs = all_msgs.copy()
                else:
                    print("Не удалось отправить.")
            elif cmd == "auto":
                set_auto_refresh(not auto_refresh_enabled)
            elif cmd == "discover":
                servers = discover_servers()
                if servers:
                    print("Найденные серверы:")
                    for i, url in enumerate(servers, 1):
                        print(f"{i}. {url}")
                else:
                    print("Серверы не найдены.")
            elif cmd.startswith("connect "):
                new_url = cmd[8:].strip()
                if new_url:
                    # Переподключаемся
                    set_auto_refresh(False)
                    client = ChatClient(new_url)
                    if client.send_nick(nick):
                        print(f"Подключено к {new_url}")
                        all_msgs = client.get_messages_json()
                        if all_msgs is not None:
                            show_all_messages(all_msgs)
                            last_msgs = all_msgs.copy()
                        if auto_refresh_enabled:
                            set_auto_refresh(True)
                    else:
                        print("Не удалось подключиться к новому серверу.")
            else:
                print("Неизвестная команда. Доступны: all, new, send, auto, discover, connect <url>, exit")
    except KeyboardInterrupt:
        print("\nЗавершено пользователем.")
        set_auto_refresh(False)

if __name__ == "__main__":
    main()
