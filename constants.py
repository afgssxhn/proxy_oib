# constants.py
import json
import os
from typing import Set, List

# Файловые пути
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(PROJECT_ROOT, 'web')
TEMPLATES_DIR = os.path.join(WEB_DIR, 'templates')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# Создаем директории если их нет
os.makedirs(DATA_DIR, exist_ok=True)

# Пути к файлам
LOG_FILE = os.path.join(DATA_DIR, 'Sites.txt')
BLOCKED_DOMAINS_FILE = os.path.join(DATA_DIR, 'blocked_domains.json')

# Настройки сервера
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8080
BUFFER_SIZE = 65536
MAX_CONNECTIONS = 5
CONNECTION_TIMEOUT = 10

class DomainManager:
    def __init__(self, filename: str = BLOCKED_DOMAINS_FILE):
        self.filename = filename
        self.ensure_file_exists()

    def ensure_file_exists(self) -> None:
        """Создает файл JSON, если он не существует."""
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump({"blocked_domains": []}, f)

    def get_blocked_domains(self) -> List[str]:
        """Получает список заблокированных доменов."""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("blocked_domains", [])
        except Exception as e:
            print(f"Error reading blocked domains: {e}")
            return []

    def add_domain(self, domain: str) -> bool:
        """Добавляет домен в список блокировки."""
        try:
            domain = domain.lower().strip()
            domains = self.get_blocked_domains()
            if domain not in domains:
                domains.append(domain)
                print(f"Добавление домена {domain} в {self.filename}")  # Отладочный вывод
                with open(self.filename, 'w', encoding='utf-8') as f:
                    json.dump({"blocked_domains": domains}, f, indent=2)
                print(f"Домен {domain} успешно добавлен")  # Отладочный вывод
                return True
            return False
        except Exception as e:
            print(f"Error adding domain: {e}")
            return False

    def remove_domain(self, domain: str) -> bool:
        """Удаляет домен из списка блокировки."""
        try:
            domain = domain.lower().strip()
            domains = self.get_blocked_domains()
            if domain in domains:
                domains.remove(domain)
                with open(self.filename, 'w', encoding='utf-8') as f:
                    json.dump({"blocked_domains": domains}, f, indent=2)
                return True
            return False
        except Exception as e:
            print(f"Error removing domain: {e}")
            return False