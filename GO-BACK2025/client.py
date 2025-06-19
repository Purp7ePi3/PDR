"""
Go-Back-N ARQ Protocol - Client Implementation
Risolve il problema dei pacchetti persi durante l'invio iniziale
"""

import socket
import struct
import time
import threading
import random
from datetime import datetime

class GBNClient:
    def __init__(self, server_host='localhost', server_port=8080, window_size=4, timeout=2.0, packet_loss_rate=0.1):
        # Configurazione connessione
        self.server_addr = (server_host, server_port)
        self.window_size = window_size  # Dimensione della finestra di trasmissione
        self.timeout = timeout          # Timeout per ritrasmissione
        self.packet_loss_rate = packet_loss_rate  # Percentuale di perdita pacchetti simulata
        
        # Variabili di controllo Go-Back-N
        self.base = 0        # Primo pacchetto non ancora confermato
        self.next_seq = 0    # Prossimo numero di sequenza da inviare
        self.socket = None
        self.running = False
        self.timer_active = False
        self.timer_thread = None
        self.ack_thread = None
        
        # Statistiche per monitoraggio prestazioni
        self.stats = {
            'packets_sent': 0,
            'packets_lost': 0,
            'retransmissions': 0,
            'acks_received': 0,
            'timeouts': 0,
            'total_packets': 0
        }
        
        # Buffer per memorizzare i dati dei pacchetti
        self.packet_data = {}    # Dati originali per ritrasmissione
        self.sent_packets = {}   # Pacchetti già inviati
        
        # Lock per sincronizzazione thread
        self.lock = threading.Lock()
        
    def log(self, message):
        """Stampa messaggi con timestamp per debugging"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[CLIENT {timestamp}] {message}")
        
    def start(self, num_packets=20):
        """Avvia il client e inizia la trasmissione"""
        try:
            # Inizializza socket UDP
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(0.1)  # Timeout non-bloccante per receive
            self.running = True
            self.stats['total_packets'] = num_packets
            
            # Log configurazione
            self.log(f"Client avviato - Server: {self.server_addr}")
            self.log(f"Finestra: {self.window_size}, Timeout: {self.timeout}s")
            self.log(f"Perdita pacchetti: {self.packet_loss_rate*100}%")
            self.log(f"Pacchetti da inviare: {num_packets}")
            
            # Avvia thread per ricezione ACK
            self.ack_thread = threading.Thread(target=self.receive_acks)
            self.ack_thread.daemon = True
            self.ack_thread.start()
            
            # Inizia invio pacchetti
            self.send_packets(num_packets)
            
            # Attende completamento trasmissione
            self.wait_for_completion()
            
        except Exception as e:
            self.log(e)
        finally:
            self.stop()
            
    def send_packets(self, num_packets):
        """Invia pacchetti seguendo il protocollo Go-Back-N"""
        while self.base < num_packets and self.running:
            with self.lock:
                # Invia pacchetti finché la finestra non è piena
                while (self.next_seq < self.base + self.window_size and 
                       self.next_seq < num_packets and self.running):
                    self.send_packet(self.next_seq)
                    self.next_seq += 1
                    
                # Avvia timer se non è già attivo e ci sono pacchetti in attesa
                if not self.timer_active and self.base < self.next_seq:
                    self.start_timer()
                    
            time.sleep(0.1)  # Piccola pausa per evitare busy waiting
            
    def send_packet(self, seq_num):
        """Invia un singolo pacchetto con numero di sequenza specificato"""
        try:
            # Crea payload del pacchetto
            payload = f"Messaggio {seq_num:03d}"
            packet = struct.pack('!I', seq_num) + payload.encode('utf-8')
            
            # Memorizza dati per eventuale ritrasmissione
            self.packet_data[seq_num] = packet
            
            # Simula perdita casuale del pacchetto
            if random.random() <= self.packet_loss_rate:
                self.stats['packets_lost'] += 1
                self.log(f"Pacchetto #{seq_num} perso (simulato)")
                return
                
            # Invia pacchetto al server
            self.socket.sendto(packet, self.server_addr)
            
            # Memorizza pacchetto inviato
            self.sent_packets[seq_num] = packet
            
            # Aggiorna statistiche
            self.stats['packets_sent'] += 1
            self.log(f"Inviato pacchetto #{seq_num}: '{payload}'")
            
        except Exception as e:
            self.log(f"Errore nell'invio pacchetto #{seq_num}: {e}")
            
    def receive_acks(self):
        """Thread separato per ricevere ACK dal server"""
        while self.running:
            try:
                data, _ = self.socket.recvfrom(1024)
                
                # Verifica che sia un ACK valido (4 bytes)
                if len(data) == 4:
                    ack_num = struct.unpack('!I', data)[0]
                    self.handle_ack(ack_num)
                    
            except socket.timeout:
                continue  # Timeout normale, continua
            except Exception as e:
                if self.running:
                    self.log(f"Errore nella ricezione ACK: {e}")
                    
    def handle_ack(self, ack_num):
        """Gestisce la ricezione di un ACK"""
        with self.lock:
            self.log(f"Ricevuto ACK #{ack_num}")
            self.stats['acks_received'] += 1
            
            # ACK cumulativo: conferma tutti i pacchetti fino ad ack_num
            if ack_num >= self.base:
                old_base = self.base
                self.base = ack_num + 1  # Sposta la finestra
                
                self.log(f"Finestra spostata: base {old_base} -> {self.base}")
                
                # Rimuove pacchetti confermati dai buffer
                for seq in list(self.sent_packets.keys()):
                    if seq <= ack_num:
                        del self.sent_packets[seq]
                        
                for seq in list(self.packet_data.keys()):
                    if seq <= ack_num:
                        del self.packet_data[seq]
                        
                # Gestisce timer
                if self.base < self.next_seq:
                    self.restart_timer()  # Ci sono ancora pacchetti in attesa
                else:
                    self.stop_timer()     # Tutti i pacchetti confermati
                    
    def start_timer(self):
        """Avvia il timer per timeout"""
        if self.timer_active:
            return
            
        self.timer_active = True
        self.timer_thread = threading.Timer(self.timeout, self.handle_timeout)
        self.timer_thread.start()
        self.log(f"Timer avviato ({self.timeout}s)")
        
    def restart_timer(self):
        """Riavvia il timer (ferma e riavvia)"""
        self.stop_timer()
        self.start_timer()
        
    def stop_timer(self):
        """Ferma il timer attivo"""
        if self.timer_active and self.timer_thread:
            self.timer_thread.cancel()
            self.timer_active = False
            self.log("Timer fermato")
            
    def handle_timeout(self):
        """Gestisce il timeout - ritrasmette tutti i pacchetti non confermati"""
        with self.lock:
            if not self.running:
                return
                
            self.stats['timeouts'] += 1
            self.log(f"TIMEOUT! Ritrasmetto pacchetti {self.base}-{self.next_seq-1}")
            
            # Ritrasmette tutti i pacchetti nella finestra corrente
            for seq_num in range(self.base, self.next_seq):
                if seq_num in self.packet_data:
                    try:
                        # Rinvia il pacchetto
                        self.socket.sendto(self.packet_data[seq_num], self.server_addr)
                        self.sent_packets[seq_num] = self.packet_data[seq_num]
                        
                        self.stats['retransmissions'] += 1
                        self.log(f"Ritrasmesso pacchetto #{seq_num}")
                        
                    except Exception as e:
                        self.log(f"Errore ritrasmissione #{seq_num}: {e}")
                else:
                    self.log(f"Dati pacchetto #{seq_num} non trovati!")
                    
            # Riavvia il timer per il prossimo possibile timeout
            self.timer_active = False
            self.start_timer()
            
    def wait_for_completion(self):
        """Attende che tutti i pacchetti siano confermati"""
        self.log("Attendo conferma di tutti i pacchetti...")
        
        start_time = time.time()
        max_wait = 30  # Timeout massimo di attesa
        
        # Aspetta finché tutti i pacchetti non sono confermati
        while self.base < self.stats['total_packets'] and self.running:
            time.sleep(0.1)
            
            # Controlla timeout massimo
            if time.time() - start_time > max_wait:
                self.log("Timeout massimo raggiunto!")
                break
                
        # Controlla risultato finale
        if self.base >= self.stats['total_packets']:
            self.log("Tutti i pacchetti sono stati confermati!")
        else:
            self.log(f"Completato parzialmente: {self.base}/{self.stats['total_packets']} pacchetti")
            
    def stop(self):
        """Ferma il client e pulisce le risorse"""
        self.running = False
        self.stop_timer()
        
        if self.socket:
            self.socket.close()
            
        self.print_stats()
        
    def print_stats(self):
        """Stampa statistiche finali della trasmissione"""
        print("\n" + "="*50)
        print("STATISTICHE CLIENT")
        print("="*50)
        print(f"Pacchetti da inviare: {self.stats['total_packets']}")
        print(f"Pacchetti inviati: {self.stats['packets_sent']}")
        print(f"Pacchetti confermati: {self.base}")
        print(f"Pacchetti persi (simulati): {self.stats['packets_lost']}")
        print(f"ACK ricevuti: {self.stats['acks_received']}")
        print(f"Ritrasmissioni: {self.stats['retransmissions']}")
        print(f"Timeout: {self.stats['timeouts']}")
        
        # Calcola percentuali di performance
        if self.stats['total_packets'] > 0:
            success_rate = (self.base / self.stats['total_packets']) * 100
            print(f"Tasso di successo: {success_rate:.1f}%")
            
        if self.stats['packets_sent'] > 0:
            retrans_rate = (self.stats['retransmissions'] / self.stats['packets_sent']) * 100
            print(f"Tasso ritrasmissioni: {retrans_rate:.1f}%")

def main():
    # Parametri di configurazione del client
    SERVER_HOST = 'localhost'    # Indirizzo del server
    SERVER_PORT = 8080          # Porta del server
    WINDOW_SIZE = 4             # Dimensione finestra Go-Back-N
    TIMEOUT = 2.0               # Timeout in secondi
    PACKET_LOSS_RATE = 0.1      # 10% di perdita pacchetti simulata
    NUM_PACKETS = 15            # Numero totale di pacchetti da inviare
    
    # Crea e avvia il client
    client = GBNClient(SERVER_HOST, SERVER_PORT, WINDOW_SIZE, TIMEOUT, PACKET_LOSS_RATE)
    
    try:
        client.start(NUM_PACKETS)
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente")
        client.stop()

if __name__ == "__main__":
    main()