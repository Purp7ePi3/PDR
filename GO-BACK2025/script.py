"""
Script di dimostrazione del protocollo Go-Back-N
Avvia automaticamente server e client per testare il protocollo
"""

import subprocess
import time
import threading
import sys
import os

def run_server():
    """Avvia il server in un processo separato"""
    try:
        print("Avvio server...")
        # Controlla se il file server esiste
        if not os.path.exists('server.py'):
            print("File server.py non trovato!")
            print("Assicurati che il file server.py sia nella stessa directory")
            return
            
        process = subprocess.Popen([sys.executable, 'server.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT,
                                 universal_newlines=True,
                                 bufsize=1)
        
        # Stampa output del server in tempo reale
        for line in process.stdout:
            if line.strip():  # Solo se la riga non è vuota
                print(f"[SERVER] {line.strip()}")
            
    except Exception as e:
        print(f"Errore nell'avvio server: {e}")

def run_client():
    """Avvia il client dopo una pausa"""
    try:
        print("Attendo 2 secondi prima di avviare il client...")
        time.sleep(2)
        
        print("Avvio client...")
        # Controlla se il file client esiste
        if not os.path.exists('client.py'):
            print("File client.py non trovato!")
            return
            
        process = subprocess.Popen([sys.executable, 'client.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT,
                                 universal_newlines=True,
                                 bufsize=1)
        
        # Stampa output del client in tempo reale
        for line in process.stdout:
            if line.strip():  # Solo se la riga non è vuota
                print(f"[CLIENT] {line.strip()}")
            
    except Exception as e:
        print(f"Errore nell'avvio client: {e}")

def main():
    """
    ============================================================
        DEMO GO-BACK-N ARQ PROTOCOL
    ============================================================

    Questo script dimostrerà:
    - Invio di pacchetti numerati con finestra scorrevole
    - Gestione timeout e ritrasmissioni
    - Simulazione perdita pacchetti e ACK
    - Statistiche dettagliate

    Configurazione:
    - Finestra: 4 pacchetti
    - Timeout: 2 secondi
    - Perdita pacchetti: 10%
    - Perdita ACK: 15%
    - Pacchetti totali: 15
    """

    missing_files = []
    if not os.path.exists('server.py'):
        missing_files.append('server.py')
    if not os.path.exists('client.py'):
        missing_files.append('client.py')
        
    if missing_files:
        print("File mancanti:")
        for file in missing_files:
            print(f"   - {file}")
        return
    
    # Avvia server in un thread separato
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    try:
        run_client()
    except KeyboardInterrupt:
        print()
if __name__ == "__main__":
    main()