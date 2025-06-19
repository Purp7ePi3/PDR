import platform
import subprocess
import time
import argparse
from datetime import datetime
import socket
import signal
import sys
import os
import re
import threading
import queue

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    
def get_hostname(ip):
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname
    except (socket.herror, socket.gaierror):
        return None

def validate_ip(ip):
    ipv4_pattern = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
    if ipv4_pattern.match(ip):
        return all(0 <= int(num) <= 255 for num in ip.split('.'))
    return False

def ping(host, timeout=2):
    system = platform.system().lower()
    if system == 'windows':
        command = ['ping', '-n', '1', '-w', str(timeout * 1000), host]
    else: 
        command = ['ping', '-c', '1', '-W', str(timeout), host]
    try:
        start_time = time.time()
        output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              timeout=timeout+1, text=True)
        elapsed_time = time.time() - start_time
        if output.returncode == 0:
            response_time = None
            if system == 'windows':
                match = re.search(r'tempo=(\d+)ms', output.stdout)
                if match:
                    response_time = float(match.group(1))
            else:
                match = re.search(r'time=([\d\.]+) ms', output.stdout)
                if match:
                    response_time = float(match.group(1))
            if response_time is None:
                response_time = elapsed_time * 1000
                
            return True, response_time
        else:
            return False, 0.0
            
    except subprocess.TimeoutExpired:
        return False, 0.0
    except Exception as e:
        print(f"{host}: {e}")
        return False, 0.0

def parallel_ping(hosts, timeout=2, max_workers=10):
    results = {}
    result_queue = queue.Queue()
    
    def worker(host):
        is_up, response_time = ping(host, timeout)
        result_queue.put((host, is_up, response_time))
    num_workers = min(max_workers, len(hosts))
    threads = []
    for host in hosts:
        while len(threads) >= num_workers:
            threads = [t for t in threads if t.is_alive()]
            if len(threads) >= num_workers:
                time.sleep(0.1)
        
        t = threading.Thread(target=worker, args=(host,))
        t.daemon = True
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    while not result_queue.empty():
        host, is_up, response_time = result_queue.get()
        results[host] = (is_up, response_time)
    
    return results

def format_time(ms):
    if ms < 1:
        return "< 1 ms"
    elif ms < 1000:
        return f"{ms:.1f} ms"
    else:
        return f"{ms/1000:.2f} s"

def monitor_hosts(hosts, interval=5, continuous=False, log_file=None, timeout=2, parallel=True):
    valid_hosts = []
    for host in hosts:
        if validate_ip(host) or host.lower() == 'localhost':
            valid_hosts.append(host)
        else:
            print(f"{Colors.YELLOW}Avviso: '{host}' non sembra un indirizzo IP valido. "
                  f"Tentativo di risoluzione...{Colors.ENDC}")
            try:
                ip = socket.gethostbyname(host)
                print(f"{Colors.GREEN}Risolto '{host}' in '{ip}'. Aggiunto al monitoraggio.{Colors.ENDC}")
                valid_hosts.append(ip)
            except socket.gaierror:
                print(f"{Colors.RED}Errore: Ignoro '{host}'.{Colors.ENDC}")
    
    if not valid_hosts:
        print(f"{Colors.RED}Errore: Nessun host valido da monitorare.{Colors.ENDC}")
        return
    
    previous_states = {host: None for host in valid_hosts}
    
    statistics = {host: {"checks": 0, "up": 0, "down": 0, "total_response_time": 0} 
                 for host in valid_hosts}
    
    hostnames = {host: get_hostname(host) for host in valid_hosts}
    
    def signal_handler(sig, frame):
        print("\n" + Colors.YELLOW + "Interruzione del monitoraggio..." + Colors.ENDC)
        print_statistics(statistics, hostnames)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print(f"{Colors.RED}Errore nella creazione della directory per il log: {e}{Colors.ENDC}")
                log_file = None
        try:
            with open(log_file, 'a') as f:
                f.write(f"=== Sessione di monitoraggio iniziata il {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.write(f"Host monitorati: {', '.join(valid_hosts)}\n\n")
        except IOError as e:
            print(f"{Colors.RED}Errore nell'apertura del file di log: {e}{Colors.ENDC}")
            log_file = None
    
    try:
        count = 1
        while True:
            print(f"\n{Colors.BOLD}===== Controllo #{count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====={Colors.ENDC}")
            
            if parallel:
                results = parallel_ping(valid_hosts, timeout)
            else:
                results = {host: ping(host, timeout) for host in valid_hosts}
            
            for host in valid_hosts:
                is_up, response_time = results[host]
                
                hostname = hostnames[host]
                host_display = f"{host} ({hostname})" if hostname else host
                
                statistics[host]["checks"] += 1
                
                if is_up:
                    statistics[host]["up"] += 1
                    statistics[host]["total_response_time"] += response_time
                    status = f"{Colors.GREEN}ONLINE{Colors.ENDC}"
                    details = f"Risposta: {Colors.CYAN}{format_time(response_time)}{Colors.ENDC}"
                else:
                    statistics[host]["down"] += 1
                    status = f"{Colors.RED}OFFLINE{Colors.ENDC}"
                    details = ""
                
                print(f"Host: {host_display:<40} Stato: {status:<20} {details}")
                
                if previous_states[host] is not None and previous_states[host] != is_up:
                    change = "UP" if is_up else "DOWN"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    message = f"{timestamp} - Host {host} è passato a {change}"
                    print(f"{Colors.YELLOW}* Cambio di stato: {message}{Colors.ENDC}")
                    
                    if log_file:
                        try:
                            with open(log_file, 'a') as f:
                                f.write(f"{message}\n")
                        except IOError as e:
                            print(f"{Colors.RED}Errore nella scrittura del log: {e}{Colors.ENDC}")
                
                previous_states[host] = is_up
            
            if not continuous:
                break
            
            print(f"\nProssimo controllo tra {interval} secondi. Premi Ctrl+C per terminare.")
            time.sleep(interval)
            count += 1
            
    except KeyboardInterrupt:
        print("")
    finally:
        print_statistics(statistics, hostnames)
        
        if log_file:
            try:
                with open(log_file, 'a') as f:
                    f.write(f"\n=== Sessione di monitoraggio terminata il {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
            except IOError:
                pass

def print_statistics(statistics, hostnames=None):
    if not hostnames:
        hostnames = {}
        
    print("\n" + Colors.BOLD + "Statistiche di monitoraggio:" + Colors.ENDC)
    print("-" * 80)
    print(f"{'Host':<30} | {'Controlli':^8} | {'Up':^6} | {'Down':^6} | {'Uptime':^7} | {'Tempo medio':^12}")
    print("-" * 80)
    
    for host, stats in statistics.items():
        if stats["checks"] > 0:
            uptime_percent = (stats["up"] / stats["checks"]) * 100
            
            if stats["up"] > 0:
                avg_response = stats["total_response_time"] / stats["up"]
                avg_response_str = format_time(avg_response)
            else:
                avg_response_str = "N/A"

            hostname = hostnames.get(host)
            host_display = f"{host} ({hostname})" if hostname else host
            if len(host_display) > 28:
                host_display = host_display[:25] + "..."

            if uptime_percent >= 99:
                uptime_str = f"{Colors.GREEN}{uptime_percent:.1f}%{Colors.ENDC}"
            elif uptime_percent >= 90:
                uptime_str = f"{Colors.YELLOW}{uptime_percent:.1f}%{Colors.ENDC}"
            else:
                uptime_str = f"{Colors.RED}{uptime_percent:.1f}%{Colors.ENDC}"
                
            print(f"{host_display:<30} | {stats['checks']:^8} | {stats['up']:^6} | {stats['down']:^6} | "
                  f"{uptime_str:^11} | {avg_response_str:^12}")
    
    print("-" * 80)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('hosts', nargs='*', help='Indirizzi IP degli host da monitorare')
    parser.add_argument('-f', '--file', help='File contenente gli indirizzi IP (uno per riga)')
    parser.add_argument('-i', '--interval', type=int, default=5, 
                        help='Intervallo tra i controlli in secondi (default: 5)')
    parser.add_argument('-c', '--continuous', action='store_true', 
                        help='Esegue il monitoraggio in modo continuo')
    parser.add_argument('-l', '--log', help='Nome del file di log per i cambi di stato')
    parser.add_argument('-t', '--timeout', type=float, default=0.5,
                        help='Timeout per i ping in secondi (default: 2)')
    parser.add_argument('-s', '--sequential', action='store_true',
                        help='Esegue i ping in sequenza invece che in parallelo') 
    args = parser.parse_args()
    hosts_to_monitor = []
    if args.hosts:
        hosts_to_monitor.extend(args.hosts)
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_hosts = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                hosts_to_monitor.extend(file_hosts)
        except FileNotFoundError:
            print(f"{Colors.RED}Errore: File {args.file} non trovato.{Colors.ENDC}")
            return
        except IOError as e:
            print(f"{Colors.RED}Errore nella lettura del file: {e}{Colors.ENDC}")
            return
    if not hosts_to_monitor:
        print(f"{Colors.RED}Errore: Specificare almeno un host da monitorare.{Colors.ENDC}")
        parser.print_help()
        return
    seen = set()
    hosts_to_monitor = [x for x in hosts_to_monitor if not (x in seen or seen.add(x))]
    
    print(f"{Colors.BLUE}Avvio del monitoraggio per {len(hosts_to_monitor)} host...{Colors.ENDC}")
    monitor_hosts(hosts_to_monitor, args.interval, args.continuous, args.log, 
                 args.timeout, not args.sequential)

if __name__ == "__main__":
    main()