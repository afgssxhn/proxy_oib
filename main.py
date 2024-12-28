import subprocess
import sys
import os
import time
import signal
import psutil

def kill_process_and_children(proc):
    """Убивает процесс и все его дочерние процессы"""
    try:
        parent = psutil.Process(proc.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except:
        pass

def start_servers():
    """Запускает прокси-сервер и веб-интерфейс"""
    try:
        # Определяем текущую директорию проекта
        project_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Запускаем прокси-сервер
        print("[*] Запуск прокси-сервера...")
        proxy_server = subprocess.Popen([sys.executable, 'simple_proxy.py'],
                                      cwd=project_dir)
        
        # Даем прокси-серверу время на запуск
        time.sleep(2)
        
        # Запускаем веб-интерфейс
        print("[*] Запуск веб-интерфейса...")
        web_interface = subprocess.Popen([sys.executable, 'web/app.py'],
                                       cwd=project_dir)
        
        print("\n[*] Все сервисы запущены:")
        print("    - Прокси-сервер: http://127.0.0.1:8080")
        print("    - Веб-интерфейс: http://127.0.0.1:5000")
        print("\nНажмите Ctrl+C для завершения работы...\n")
        
        # Ждем завершения процессов
        proxy_server.wait()
        web_interface.wait()
        
    except KeyboardInterrupt:
        print("\n[*] Завершение работы...")
        # Корректно завершаем все процессы
        kill_process_and_children(proxy_server)
        kill_process_and_children(web_interface)
    except Exception as e:
        print(f"[!] Ошибка: {e}")
    finally:
        # Убеждаемся, что все процессы завершены
        try:
            proxy_server.kill()
            web_interface.kill()
        except:
            pass
        print("[*] Все сервисы остановлены")

if __name__ == "__main__":
    start_servers() 