import platform
import subprocess
import time
import argparse
from datetime import datetime
import socket
import signal
import sys

# Colori per il terminale
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def get_hostname(ip):
    """Tenta di risolvere l'hostname da un indirizzo IP."""
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname
    except (socket.herror, socket.gaierror):
        return None

def ping(host):
    """
    Esegue un ping verso l'host specificato.
    Restituisce True se l'host è raggiungibile, False altrimenti.
    """
    # Determina il comando ping appropriato in base al sistema operativo
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    command = ['ping', param, '1', host]
    
    try:
        # Esegue il comando ping e cattura l'output
        output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
        # Restituisce True se il comando ping è stato eseguito con successo (codice di uscita 0)
        return output.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        print(f"Errore durante l'esecuzione del ping verso {host}: {e}")
        return False

def monitor_hosts(hosts, interval=5, continuous=False, log_file=None):
    """
    Monitora lo stato degli host specificati.
    
    Args:
        hosts (list): Lista di indirizzi IP da monitorare
        interval (int): Intervallo di tempo tra i controlli (in secondi)
        continuous (bool): Se True, continua il monitoraggio all'infinito
        log_file (str): Nome del file di log (opzionale)
    """
    # Mappa per tenere traccia dello stato precedente degli host
    previous_states = {host: None for host in hosts}
    
    # Contatori per le statistiche
    statistics = {host: {"checks": 0, "up": 0, "down": 0} for host in hosts}
    
    # Funzione per gestire l'interruzione del programma (Ctrl+C)
    def signal_handler(sig, frame):
        print("\n" + Colors.YELLOW + "Interruzione del monitoraggio..." + Colors.ENDC)
        print_statistics(statistics)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        count = 1
        while True:
            print(f"\n{Colors.BOLD}===== Controllo #{count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====={Colors.ENDC}")
            
            for host in hosts:
                # Ottiene il nome host (se possibile)
                hostname = get_hostname(host)
                host_display = f"{host} ({hostname})" if hostname else host
                
                # Controlla lo stato corrente dell'host
                is_up = ping(host)
                statistics[host]["checks"] += 1
                
                if is_up:
                    statistics[host]["up"] += 1
                    status = f"{Colors.GREEN}ONLINE{Colors.ENDC}"
                else:
                    statistics[host]["down"] += 1
                    status = f"{Colors.RED}OFFLINE{Colors.ENDC}"
                
                # Mostra lo stato corrente
                print(f"Host: {host_display:<40} Stato: {status}")
                
                # Evidenzia i cambiamenti di stato
                if previous_states[host] is not None and previous_states[host] != is_up:
                    change = "UP" if is_up else "DOWN"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    message = f"{timestamp} - Host {host} è passato a {change}"
                    print(f"{Colors.YELLOW}* Cambio di stato: {message}{Colors.ENDC}")
                    
                    # Log del cambio di stato su file se specificato
                    if log_file:
                        with open(log_file, 'a') as f:
                            f.write(f"{message}\n")
                
                # Aggiorna lo stato precedente
                previous_states[host] = is_up
            
            # Se non è in modalità continua, esce dopo il primo controllo
            if not continuous:
                break
            
            # Attende l'intervallo specificato prima del prossimo controllo
            print(f"\nProssimo controllo tra {interval} secondi. Premi Ctrl+C per terminare.")
            time.sleep(interval)
            count += 1
            
    except KeyboardInterrupt:
        print("\n" + Colors.YELLOW + "Interruzione del monitoraggio..." + Colors.ENDC)
    finally:
        # Mostra le statistiche al termine del monitoraggio
        print_statistics(statistics)

def print_statistics(statistics):
    """Mostra le statistiche di monitoraggio."""
    print("\n" + Colors.BOLD + "Statistiche di monitoraggio:" + Colors.ENDC)
    for host, stats in statistics.items():
        if stats["checks"] > 0:
            uptime_percent = (stats["up"] / stats["checks"]) * 100
            print(f"Host: {host:<15} | Controlli: {stats['checks']:<4} | " \
                  f"Up: {stats['up']:<4} | Down: {stats['down']:<4} | " \
                  f"Uptime: {uptime_percent:.1f}%")

def main():
    """Funzione principale dello script."""
    parser = argparse.ArgumentParser(description='Script di monitoraggio rete tramite ICMP (ping)')
    
    # Argomenti da linea di comando
    parser.add_argument('hosts', nargs='*', help='Indirizzi IP degli host da monitorare')
    parser.add_argument('-f', '--file', help='File contenente gli indirizzi IP (uno per riga)')
    parser.add_argument('-i', '--interval', type=int, default=5, 
                        help='Intervallo tra i controlli in secondi (default: 5)')
    parser.add_argument('-c', '--continuous', action='store_true', 
                        help='Esegue il monitoraggio in modo continuo')
    parser.add_argument('-l', '--log', help='Nome del file di log per i cambi di stato')
    
    args = parser.parse_args()
    
    # Raccoglie gli host da monitorare
    hosts_to_monitor = []
    
    # Aggiunge gli host specificati come argomenti
    if args.hosts:
        hosts_to_monitor.extend(args.hosts)
    
    # Legge gli host dal file se specificato
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_hosts = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                hosts_to_monitor.extend(file_hosts)
        except FileNotFoundError:
            print(f"Errore: File {args.file} non trovato.")
            return
    
    # Verifica che ci sia almeno un host da monitorare
    if not hosts_to_monitor:
        print("Errore: Specificare almeno un host da monitorare.")
        parser.print_help()
        return
    
    # Rimuove i duplicati
    hosts_to_monitor = list(dict.fromkeys(hosts_to_monitor))
    
    print(f"{Colors.BLUE}Avvio del monitoraggio per {len(hosts_to_monitor)} host...{Colors.ENDC}")
    
    # Avvia il monitoraggio
    monitor_hosts(hosts_to_monitor, args.interval, args.continuous, args.log)

if __name__ == "__main__":
    main()
