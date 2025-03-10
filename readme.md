# Proxy Server с Web-интерфейсом

Прокси-сервер с веб-интерфейсом для мониторинга и управления блокировкой доменов.

## Структура проекта

```
proxy_server/
├── data/                    # Директория с данными
│   ├── Sites.txt           # Файл логов
│   └── blocked_domains.json # Список заблокированных доменов
├── web/                     # Веб-интерфейс
│   ├── templates/          # HTML шаблоны
│   │   ├── monitor.html    # Страница мониторинга
│   │   └── block.html      # Страница управления блокировкой
│   └── app.py             # Flask приложение
├── constants.py            # Константы и менеджер доменов
└── simple_proxy.py         # Основной прокси-сервер
```

## Компоненты

1. Прокси-сервер (simple_proxy.py):
   - Обработка HTTP/HTTPS соединений
   - Фильтрация доменов
   - Логирование доступа

2. Веб-интерфейс (web/):
   - Мониторинг логов в реальном времени
   - Управление списком заблокированных доменов
   - Real-time обновления через WebSocket

3. Управление данными (constants.py):
   - Управление конфигурацией
   - Работа со списком заблокированных доменов
   - Определение путей и констант

## Запуск

1. Запуск прокси-сервера:
```bash
python simple_proxy.py
```

2. Запуск веб-интерфейса:
```bash
python web/app.py
```

Веб-интерфейс будет доступен по адресу: http://127.0.0.1:5000