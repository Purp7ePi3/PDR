"""
Go-Back-N ARQ Protocol - Server Implementation
Riceve pacchetti numerati e invia ACK solo per quelli ricevuti in ordine
"""

import socket
import struct
import time
import random
import threading
from datetime import datetime

class GBNServer:
    def __init__(self, host='localhost', port=8080, loss_rate=0.1):
        self.host = host
        self.port = port
        self.loss_rate = loss_rate  # Probabilità di perdere un ACK
        self.expected_seq = 0  # Numero di sequenza atteso
        self.socket = None
        self.running = False
        self.stats = {
            'packets_received': 0,
            'packets_in_order': 0,
            'packets_out_of_order': 0,
            'acks_sent': 0,
            'acks_lost': 0
        }
        
    def log(self, message):
        """Logging con timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[SERVER {timestamp}] {message}")
        
    def start(self):
        """Avvia il server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(1.0)  # Timeout per permettere interruzioni
            self.running = True
            
            self.log(f"Server avviato su {self.host}:{self.port}")
            self.log(f"Tasso di perdita ACK: {self.loss_rate*100}%")
            self.log("In attesa di pacchetti...")
            
            self.listen()
            
        except Exception as e:
            self.log(f"Errore nell'avvio del server: {e}")
        finally:
            self.stop()
            
    def listen(self):
        """Ascolta i pacchetti in arrivo"""
        while self.running:
            try:
                # Ricevi pacchetto
                data, client_addr = self.socket.recvfrom(1024)
                self.stats['packets_received'] += 1
                
                # Decodifica il pacchetto (4 bytes per seq_num + dati)
                if len(data) < 4:
                    continue
                    
                seq_num = struct.unpack('!I', data[:4])[0]
                payload = data[4:].decode('utf-8', errors='ignore')
                
                self.log(f"Ricevuto pacchetto #{seq_num} da {client_addr}: '{payload}'")
                
                # Verifica se il pacchetto è quello atteso
                if seq_num == self.expected_seq:
                    self.stats['packets_in_order'] += 1
                    self.log(f"Pacchetto #{seq_num} accettato (in ordine)")
                    
                    # Invia ACK
                    self.send_ack(client_addr, seq_num)
                    
                    # Incrementa il numero di sequenza atteso
                    self.expected_seq += 1
                    
                elif seq_num < self.expected_seq:
                    # Pacchetto duplicato, invia comunque ACK
                    self.stats['packets_out_of_order'] += 1
                    self.log(f"Pacchetto #{seq_num} duplicato, invio ACK")
                    self.send_ack(client_addr, seq_num)
                    
                else:
                    # Pacchetto fuori ordine
                    self.stats['packets_out_of_order'] += 1
                    self.log(f"Pacchetto #{seq_num} fuori ordine (atteso #{self.expected_seq}), scarto")
                    # Non inviare ACK per pacchetti fuori ordine in Go-Back-N
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.log(f"Errore nella ricezione: {e}")
                    
    def send_ack(self, client_addr, seq_num):
        """Invia ACK al client (con possibile perdita simulata)"""
        try:
            # Simula perdita ACK
            if random.random() < self.loss_rate:
                self.stats['acks_lost'] += 1
                self.log(f"ACK #{seq_num} perso (simulato)")
                return
                
            # Crea pacchetto ACK
            ack_packet = struct.pack('!I', seq_num)
            self.socket.sendto(ack_packet, client_addr)
            
            self.stats['acks_sent'] += 1
            self.log(f"ACK #{seq_num} inviato a {client_addr}")
            
        except Exception as e:
            self.log(f"Errore nell'invio ACK: {e}")
            
    def stop(self):
        """Ferma il server"""
        self.running = False
        if self.socket:
            self.socket.close()
        self.print_stats()
        
    def print_stats(self):
        """Stampa statistiche finali"""
        print("\n" + "="*50)
        print("STATISTICHE SERVER")
        print("="*50)
        print(f"Pacchetti ricevuti totali: {self.stats['packets_received']}")
        print(f"Pacchetti in ordine: {self.stats['packets_in_order']}")
        print(f"Pacchetti fuori ordine/duplicati: {self.stats['packets_out_of_order']}")
        print(f"ACK inviati: {self.stats['acks_sent']}")
        print(f"ACK persi (simulati): {self.stats['acks_lost']}")
        if self.stats['packets_received'] > 0:
            in_order_rate = (self.stats['packets_in_order'] / self.stats['packets_received']) * 100
            print(f"Tasso pacchetti in ordine: {in_order_rate:.1f}%")

def main():
    print("=== Go-Back-N ARQ Protocol - Server ===\n")
    
    # Configurazione
    HOST = 'localhost'
    PORT = 8080
    LOSS_RATE = 0.15  # 15% di perdita ACK
    
    server = GBNServer(HOST, PORT, LOSS_RATE)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nChiusura server...")
        server.stop()

if __name__ == "__main__":
    main()