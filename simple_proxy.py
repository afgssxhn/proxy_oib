import socket
import threading
import select
from typing import Tuple, Optional, Set
import os
import sys

# Добавляем корневую директорию проекта в PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

from constants import (
    DomainManager, DEFAULT_HOST, DEFAULT_PORT, BUFFER_SIZE, 
    MAX_CONNECTIONS, CONNECTION_TIMEOUT, LOG_FILE, DATA_DIR
)
from urllib.parse import urlparse
from datetime import datetime
import os
from threading import Lock

# Список доменов для фильтрации
FILTERED_DOMAINS = {
    # Google services
    'google-analytics.com',
    'googletagmanager.com',
    'google.com',
    'googleapis.com',
    'gstatic.com',
    
    # Social and video
    'youtube.com',
    'facebook.com',
    'doubleclick.net',
    
    # Yandex services
    'yadro.ru',
    'yandex.ru',
    'yandex.net',
    'yandex.com',
    'yastatic.net',
    'mc.yandex.ru',
    'mc.yandex.com',
    
    # Analytics and counters
    'counter.yadro.ru',
    
    # CDN and hosting
    'cdn.jsdelivr.net',
    'cloudflare.com',
    'cloudfront.net',
    
    # Mozilla services
    'mozilla.org',
    'mozilla.com',
    'firefox.com',
    'telemetry.mozilla.org',
    'settings.services.mozilla.com',
    
    # Modrinth related
    'cdn.modrinth.com',
    'cdn-raw.modrinth.com',
    'api.modrinth.com',
    
    # Additional services
    'cadmus.script.ac',
    'bservr.com',
    'inmobi.com',
    
    # Others
    'googlevideo.com',
    'googleusercontent.com',
    'clients1.google.com',
    'cse.google.com',
    'region1.google-analytics.com'
}

# Инициализация менеджера доменов
domain_manager = DomainManager()

class ProxyServer:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        """Initialize proxy server with host and port."""
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.log_lock = Lock()
        self.last_main_domain = None  # Для отслеживания последнего основного домена
        self.last_domain_time = None  # Для отслеживания времени последнего домена

    def _is_domain_blocked(self, domain: str) -> bool:
        """Проверяет, заблокирован ли домен."""
        domain = domain.lower()
        blocked_domains = domain_manager.get_blocked_domains()
        
        # Проверяем домен и его поддомены
        domain_parts = domain.split('.')
        for i in range(len(domain_parts) - 1):
            check_domain = '.'.join(domain_parts[i:])
            if check_domain in blocked_domains:
                return True
        return False
        
    def _should_log_domain(self, domain: str) -> bool:
        """Проверяет, нужно ли логировать данный домен."""
        domain = domain.lower()  # Приводим к нижнему регистру для сравнения
        
        # Проверяем основной домен и все его поддомены
        domain_parts = domain.split('.')
        for i in range(len(domain_parts) - 1):
            check_domain = '.'.join(domain_parts[i:])
            if check_domain in FILTERED_DOMAINS:
                return False
            
            # Также проверяем, не является ли домен поддоменом фильтруемых доменов
            for filtered in FILTERED_DOMAINS:
                if check_domain.endswith(filtered):
                    return False
        
        return True

    def _log_access(self, client_addr: str, domain: str, protocol: str) -> None:
        """Log access to both console and file."""
        # Проверяем, нужно ли логировать этот домен
        if not self._should_log_domain(domain):
            return

        current_time = datetime.now()
        
        # Если это тот же домен и прошло менее 5 секунд, не логируем
        if (self.last_main_domain == domain and 
            self.last_domain_time and 
            (current_time - self.last_domain_time).total_seconds() < 5):
            return

        self.last_main_domain = domain
        self.last_domain_time = current_time
        
        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] Accessing: {domain}"
        
        # Консольное логирование
        print(log_message)
        
        # Запись в файл с использованием блокировки
        with self.log_lock:
            try:
                with open(LOG_FILE, 'a', encoding='utf-8') as file:
                    file.write(f"{log_message}\n")
            except Exception as e:
                print(f"[!] Error writing to log file: {e}")

    def start(self) -> None:
        """Start the proxy server."""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(MAX_CONNECTIONS)
            
            # Создаем файл логов или добавляем разделитель сессии
            separator = f"\n{'='*50}\n=== Proxy Server Session Started at {datetime.now()} ===\n{'='*50}\n\n"
            with open(LOG_FILE, 'a', encoding='utf-8') as file:
                file.write(separator)
                    
            print(f"[*] Proxy server started on {self.host}:{self.port}")
            print(f"[*] Logging to {os.path.abspath(LOG_FILE)}")
            print(f"[*] Filtering auxiliary domains for cleaner logs")
            
            while True:
                client_socket, addr = self.server_socket.accept()
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr)
                )
                thread.daemon = True
                thread.start()
        except Exception as e:
            print(f"[!] Error starting server: {e}")
        finally:
            self.server_socket.close()

    def _forward_data(self, source: socket.socket, destination: socket.socket, 
                     client_addr: str, description: str) -> None:
        """Forward data between sockets with enhanced error handling."""
        source.settimeout(CONNECTION_TIMEOUT)
        destination.settimeout(CONNECTION_TIMEOUT)
        try:
            while True:
                try:
                    data = source.recv(BUFFER_SIZE)
                    if not data:
                        break
                    destination.sendall(data)
                except socket.timeout:
                    break
                except ConnectionResetError:
                    print(f"[!] Connection reset while forwarding {description} for {client_addr}")
                    break
                except Exception as e:
                    print(f"[!] Error forwarding {description} for {client_addr}: {e}")
                    break
        except Exception as e:
            print(f"[!] General error in forwarding {description} for {client_addr}: {e}")
        finally:
            source.close()
            destination.close()

    def _handle_https_tunnel(self, client_socket: socket.socket, 
                           remote_host: str, remote_port: int, 
                           client_addr: str) -> None:
        """Handle HTTPS tunneling with improved error handling."""
        try:
            # Проверяем блокировку домена
            if self._is_domain_blocked(remote_host):
                print(f"[!] Blocked access to {remote_host}")
                client_socket.send(b'HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\n\r\n')
                client_socket.send(b'<h1>403 Forbidden</h1><p>This domain is blocked by proxy settings.</p>')
                return

            # Create connection to remote server
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(CONNECTION_TIMEOUT)
            server_socket.connect((remote_host, remote_port))
            
            # Log the access
            self._log_access(client_addr, remote_host, "HTTPS")
            
            # Send success response to client
            client_socket.send(b'HTTP/1.1 200 Connection established\r\n\r\n')
            
            # Create threads for bi-directional tunneling
            client_to_server = threading.Thread(
                target=self._forward_data,
                args=(client_socket, server_socket, client_addr, "client -> server")
            )
            server_to_client = threading.Thread(
                target=self._forward_data,
                args=(server_socket, client_socket, client_addr, "server -> client")
            )
            
            client_to_server.daemon = True
            server_to_client.daemon = True
            
            client_to_server.start()
            server_to_client.start()
            
            # Wait for either thread to finish
            client_to_server.join()
            server_to_client.join()
            
        except ConnectionRefusedError:
            print(f"[!] Connection refused by remote server {remote_host}:{remote_port}")
            client_socket.send(b'HTTP/1.1 504 Gateway Timeout\r\n\r\n')
        except socket.timeout:
            print(f"[!] Connection timeout to {remote_host}:{remote_port}")
            client_socket.send(b'HTTP/1.1 504 Gateway Timeout\r\n\r\n')
        except Exception as e:
            print(f"[!] Error in HTTPS tunneling to {remote_host}:{remote_port}: {e}")
            client_socket.send(b'HTTP/1.1 502 Bad Gateway\r\n\r\n')
        finally:
            client_socket.close()

    def _handle_client(self, client_socket: socket.socket, addr: Tuple[str, int]) -> None:
        """Handle client connection with improved error handling."""
        client_addr = f"{addr[0]}:{addr[1]}"
        try:
            client_socket.settimeout(CONNECTION_TIMEOUT)
            request = client_socket.recv(BUFFER_SIZE)
            
            if not request:
                return

            try:
                request_str = request.decode('utf-8')
                first_line = request_str.split('\n')[0]
                
                # Handle CONNECT method (HTTPS)
                if 'CONNECT' in first_line:
                    try:
                        host_port = first_line.split(' ')[1]
                        remote_host, remote_port = host_port.split(':')
                        remote_port = int(remote_port)
                        
                        self._handle_https_tunnel(client_socket, remote_host, remote_port, client_addr)
                        return
                        
                    except Exception as e:
                        print(f"[!] Error parsing CONNECT request: {e}")
                        client_socket.send(b'HTTP/1.1 400 Bad Request\r\n\r\n')
                        return
                
                # Handle HTTP request
                else:
                    try:
                        url = first_line.split(' ')[1]
                        domain = urlparse(url).netloc
                        if domain:
                            # Проверяем блокировку домена
                            if self._is_domain_blocked(domain):
                                print(f"[!] Blocked access to {domain}")
                                response = (
                                    b'HTTP/1.1 403 Forbidden\r\n'
                                    b'Content-Type: text/html\r\n'
                                    b'\r\n'
                                    b'<h1>403 Forbidden</h1>'
                                    b'<p>This domain is blocked by proxy settings.</p>'
                                )
                                client_socket.send(response)
                                return
                            self._log_access(client_addr, domain, "HTTP")
                    except Exception as e:
                        print(f"[!] Error parsing HTTP request: {e}")
                
            except UnicodeDecodeError:
                print(f"[!] Unable to decode request from {client_addr}")
                
        except socket.timeout:
            print(f"[!] Connection timeout from {client_addr}")
        except Exception as e:
            print(f"[!] Error handling client {client_addr}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass

def main():
    """Main function to run the proxy server."""
    proxy = ProxyServer()
    try:
        proxy.start()
    except KeyboardInterrupt:
        print("\n[*] Shutting down proxy server...")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")

if __name__ == "__main__":
    main()