# web/app.py
import os
import sys

# Добавляем родительскую директорию в PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from flask import Flask, render_template, request, redirect, url_for
from constants import DomainManager
from flask_socketio import SocketIO
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app)

# Импортируем путь к файлу логов из констант
from constants import LOG_FILE
last_position = 0

class LogHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == os.path.abspath(LOG_FILE):
            global last_position
            with open(LOG_FILE, 'r', encoding='utf-8') as file:
                file.seek(last_position)
                new_lines = file.readlines()
                last_position = file.tell()
                
                for line in new_lines:
                    if line.strip():
                        socketio.emit('log_update', {'data': line.strip()})

# Инициализация менеджера доменов
domain_manager = DomainManager()

@app.route('/')
def index():
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            print(f"Reading logs from: {LOG_FILE}")  # Для отладки
            with open(LOG_FILE, 'r', encoding='utf-8') as file:
                logs = [line.strip() for line in file.readlines() if line.strip()]
            global last_position
            last_position = os.path.getsize(LOG_FILE)
        except Exception as e:
            print(f"Error reading log file: {e}")
    
    return render_template('monitor.html', logs=logs)

@app.route('/block', methods=['GET', 'POST'])
def block():
    message = None
    message_type = None
    
    if request.method == 'POST':
        domain = request.form.get('domain', '').strip()
        if domain:
            if domain_manager.add_domain(domain):
                message = f'Домен {domain} успешно добавлен в блок-лист'
                message_type = 'success'
            else:
                message = f'Домен {domain} уже находится в блок-листе'
                message_type = 'error'
        else:
            message = 'Введите домен'
            message_type = 'error'
    
    blocked_domains = domain_manager.get_blocked_domains()
    return render_template('block.html', 
                         blocked_domains=blocked_domains,
                         message=message,
                         message_type=message_type)

@app.route('/unblock', methods=['POST'])
def unblock():
    domain = request.form.get('domain', '').strip()
    if domain:
        domain_manager.remove_domain(domain)
    return redirect(url_for('block'))

@socketio.on('request_update')
def handle_update_request():
    """Обработчик запроса обновления от клиента"""
    global last_position
    if os.path.exists(LOG_FILE):
        current_size = os.path.getsize(LOG_FILE)
        if current_size < last_position:
            last_position = 0
        
        if current_size > last_position:
            with open(LOG_FILE, 'r', encoding='utf-8') as file:
                file.seek(last_position)
                new_lines = file.readlines()
                last_position = file.tell()
                
                for line in new_lines:
                    if line.strip():
                        socketio.emit('log_update', {'data': line.strip()})

def start_file_monitor():
    event_handler = LogHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

def main():
    start_file_monitor()
    print(f"Starting web monitor on http://127.0.0.1:5000")
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()