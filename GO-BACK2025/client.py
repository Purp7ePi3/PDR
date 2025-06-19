#!/usr/bin/env python3
"""
Go-Back-N ARQ Protocol - Client Implementation (Bug Fix Definitivo)
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
        self.server_addr = (server_host, server_port)
        self.window_size = window_size
        self.timeout = timeout
        self.packet_loss_rate = packet_loss_rate
        
        self.base = 0
        self.next_seq = 0
        self.socket = None
        self.running = False
        self.timer_active = False
        self.timer_thread = None
        self.ack_thread = None
        
        # Statistiche
        self.stats = {
            'packets_sent': 0,
            'packets_lost': 0,
            'retransmissions': 0,
            'acks_received': 0,
            'timeouts': 0,
            'total_packets': 0
        }
        
        self.packet_data = {}
        self.sent_packets = {}
        
        self.lock = threading.Lock()
        
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[CLIENT {timestamp}] {message}")
        
    def start(self, num_packets=20):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(0.1)
            self.running = True
            self.stats['total_packets'] = num_packets
            
            self.log(f"Client avviato - Server: {self.server_addr}")
            self.log(f"Finestra: {self.window_size}, Timeout: {self.timeout}s")
            self.log(f"Perdita pacchetti: {self.packet_loss_rate*100}%")
            self.log(f"Pacchetti da inviare: {num_packets}")
            self.ack_thread = threading.Thread(target=self.receive_acks)
            self.ack_thread.daemon = True
            self.ack_thread.start()
            self.send_packets(num_packets)
            self.wait_for_completion()
            
        except Exception as e:
            self.log(e)
        finally:
            self.stop()
            
    def send_packets(self, num_packets):
        """Invia pacchetti seguendo il protocollo Go-Back-N"""
        while self.base < num_packets and self.running:
            with self.lock:
                while (self.next_seq < self.base + self.window_size and 
                       self.next_seq < num_packets and self.running):
                    self.send_packet(self.next_seq)
                    self.next_seq += 1
                    
                if not self.timer_active and self.base < self.next_seq:
                    self.start_timer()
                    
            time.sleep(0.1)
            
    def send_packet(self, seq_num):
        try:
            payload = f"Messaggio {seq_num:03d}"
            packet = struct.pack('!I', seq_num) + payload.encode('utf-8')
            
            self.packet_data[seq_num] = packet
            
            if random.random() <= self.packet_loss_rate:
                self.stats['packets_lost'] += 1
                self.log(f"Pacchetto #{seq_num} perso (simulato)")
                return
            self.socket.sendto(packet, self.server_addr)
            
            self.sent_packets[seq_num] = packet
            
            self.stats['packets_sent'] += 1
            self.log(f"Inviato pacchetto #{seq_num}: '{payload}'")
            
        except Exception as e:
            self.log(f"Errore nell'invio pacchetto #{seq_num}: {e}")
            
    def receive_acks(self):
        while self.running:
            try:
                data, _ = self.socket.recvfrom(1024)
                
                if len(data) == 4:
                    ack_num = struct.unpack('!I', data)[0]
                    self.handle_ack(ack_num)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.log(f"Errore nella ricezione ACK: {e}")
                    
    def handle_ack(self, ack_num):
        with self.lock:
            self.log(f"Ricevuto ACK #{ack_num}")
            self.stats['acks_received'] += 1
            
            if ack_num >= self.base:
                old_base = self.base
                self.base = ack_num + 1
                
                self.log(f"Finestra spostata: base {old_base} -> {self.base}")
                
                for seq in list(self.sent_packets.keys()):
                    if seq <= ack_num:
                        del self.sent_packets[seq]
                        
                for seq in list(self.packet_data.keys()):
                    if seq <= ack_num:
                        del self.packet_data[seq]
                        
                if self.base < self.next_seq:
                    self.restart_timer()
                else:
                    self.stop_timer()
                    
    def start_timer(self):
        if self.timer_active:
            return
            
        self.timer_active = True
        self.timer_thread = threading.Timer(self.timeout, self.handle_timeout)
        self.timer_thread.start()
        self.log(f"Timer avviato ({self.timeout}s)")
        
    def restart_timer(self):
        self.stop_timer()
        self.start_timer()
        
    def stop_timer(self):
        if self.timer_active and self.timer_thread:
            self.timer_thread.cancel()
            self.timer_active = False
            self.log("Timer fermato")
            
    def handle_timeout(self):
        with self.lock:
            if not self.running:
                return
                
            self.stats['timeouts'] += 1
            self.log(f"TIMEOUT! Ritrasmetto pacchetti {self.base}-{self.next_seq-1}")
            
            for seq_num in range(self.base, self.next_seq):
                if seq_num in self.packet_data:
                    try:
                        self.socket.sendto(self.packet_data[seq_num], self.server_addr)
                        self.sent_packets[seq_num] = self.packet_data[seq_num]
                        
                        self.stats['retransmissions'] += 1
                        self.log(f"Ritrasmesso pacchetto #{seq_num}")
                        
                    except Exception as e:
                        self.log(f"Errore ritrasmissione #{seq_num}: {e}")
                else:
                    self.log(f"Dati pacchetto #{seq_num} non trovati!")                        
            self.timer_active = False
            self.start_timer()
            
    def wait_for_completion(self):
        self.log("Attendo conferma di tutti i pacchetti...")
        
        start_time = time.time()
        max_wait = 30
        
        while self.base < self.stats['total_packets'] and self.running:
            time.sleep(0.1)
            
            if time.time() - start_time > max_wait:
                self.log("Timeout massimo raggiunto!")
                break
                
        if self.base >= self.stats['total_packets']:
            self.log("Tutti i pacchetti sono stati confermati!")
        else:
            self.log(f"Completato parzialmente: {self.base}/{self.stats['total_packets']} pacchetti")
            
    def stop(self):
        self.running = False
        self.stop_timer()
        
        if self.socket:
            self.socket.close()
            
        self.print_stats()
        
    def print_stats(self):
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
        
        if self.stats['total_packets'] > 0:
            success_rate = (self.base / self.stats['total_packets']) * 100
            print(f"Tasso di successo: {success_rate:.1f}%")
            
        if self.stats['packets_sent'] > 0:
            retrans_rate = (self.stats['retransmissions'] / self.stats['packets_sent']) * 100
            print(f"Tasso ritrasmissioni: {retrans_rate:.1f}%")

def main():

    SERVER_HOST = 'localhost'
    SERVER_PORT = 8080
    WINDOW_SIZE = 4
    TIMEOUT = 2.0
    PACKET_LOSS_RATE = 0.1
    NUM_PACKETS = 15
    
    client = GBNClient(SERVER_HOST, SERVER_PORT, WINDOW_SIZE, TIMEOUT, PACKET_LOSS_RATE)
    
    try:
        client.start(NUM_PACKETS)
    except KeyboardInterrupt:
        client.stop()

if __name__ == "__main__":
    main()