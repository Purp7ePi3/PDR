# Progetti di Rete

Due progetti universitari sui protocolli di rete in Python.

## GO-BACK2025/ (Anno 2025)

Implementazione del protocollo Go-Back-N ARQ per trasmissione affidabile di pacchetti.

- **Cosa fa**: Simula invio di pacchetti numerati con ritrasmissione automatica
- **Come funziona**: Finestra scorrevole, timeout e ACK cumulativi
- **Eseguire**: `python run.py` (avvia server e client insieme)

## Pinger2024/ (Anno 2024)

Tool di monitoraggio rete che controlla disponibilità di host tramite ping.

- **Cosa fa**: Verifica se host/server sono online o offline
- **Come funziona**: Ping ICMP continuo con statistiche e log
- **Eseguire**: `python pinger.py 192.168.1.1` (controlla un host)

---

**Go-Back-N**: Protocollo di trasporto affidabile  
**Pinger**: Tool di monitoraggio rete