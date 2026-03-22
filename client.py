import urllib.request
import urllib.parse
import sys
from html.parser import HTMLParser

class MessageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_li = False
        self.messages = []

    def handle_starttag(self, tag, attrs):
        if tag == 'li':
            self.in_li = True

    def handle_endtag(self, tag):
        if tag == 'li':
            self.in_li = False

    def handle_data(self, data):
        if self.in_li:
            text = data.strip()
            if text:
                self.messages.append(text)

def get_all_messages(server_url):
    """Получить список всех сообщений с сервера"""
    try:
        with urllib.request.urlopen(server_url) as response:
            html = response.read().decode('utf-8')
            parser = MessageParser()
            parser.feed(html)
            return parser.messages
    except Exception as e:
        print(f"Ошибка при получении сообщений: {e}")
        return None

def send_message(server_url, message):
    """Отправить новое сообщение на сервер"""
    data = urllib.parse.urlencode({'message': message}).encode('utf-8')
    try:
        req = urllib.request.Request(server_url, data=data, method='POST')
        with urllib.request.urlopen(req):
            return True
    except Exception as e:
        print(f"Ошибка при отправке сообщения: {e}")
        return False

def show_messages(messages, new_only=False, old_messages=None):
    """Вывести сообщения. Если new_only=True, показываем только те, которых не было в old_messages."""
    if not messages:
        print("Сообщений пока нет.")
        return

    if new_only and old_messages is not None:
        new_msgs = [msg for msg in messages if msg not in old_messages]
        if new_msgs:
            print("\n=== Новые сообщения ===")
            for i, msg in enumerate(new_msgs, 1):
                print(f"{i}. {msg}")
        else:
            print("Новых сообщений нет.")
    else:
        print("\n=== Все сообщения ===")
        for i, msg in enumerate(messages, 1):
            print(f"{i}. {msg}")

def main():
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = input("Введите адрес сервера (например, http://192.168.31.43:8080): ").strip()
        if not server_url:
            server_url = "http://localhost:8080"
    if server_url.endswith('/'):
        server_url = server_url[:-1]

    print("Консольный клиент чата. Доступные команды:")
    print("  show - показать новые сообщения")
    print("  send - отправить сообщение")
    print("  exit - выход")
    print("-" * 50)

    # Получаем начальный список сообщений
    all_msgs = get_all_messages(server_url)
    if all_msgs is None:
        return
    show_messages(all_msgs)

    last_count = len(all_msgs)  # храним для определения новых
    last_msgs = all_msgs.copy() # храним все сообщения для сравнения

    try:
        while True:
            cmd = input("\nВведите команду: ").strip().lower()
            if cmd == "exit":
                print("Выход.")
                break
            elif cmd == "show":
                all_msgs = get_all_messages(server_url)
                if all_msgs is None:
                    continue
                show_messages(all_msgs, new_only=True, old_messages=last_msgs)
                # Обновляем last_msgs на текущее состояние
                last_msgs = all_msgs.copy()
            elif cmd == "send":
                msg = input("Введите сообщение: ").strip()
                if not msg:
                    print("Сообщение не может быть пустым.")
                    continue
                if send_message(server_url, msg):
                    print("Сообщение отправлено. Обновляем список...")
                    all_msgs = get_all_messages(server_url)
                    if all_msgs is not None:
                        show_messages(all_msgs, new_only=True, old_messages=last_msgs)
                        last_msgs = all_msgs.copy()
                else:
                    print("Не удалось отправить.")
            else:
                print("Неизвестная команда. Доступны: show, send, exit")
    except KeyboardInterrupt:
        print("\nЗавершено пользователем.")

if __name__ == "__main__":
    main()
