# Go-Back-N ARQ Protocol

Implementazione del protocollo Go-Back-N con socket UDP in Python che garantisce consegna affidabile con finestra scorrevole.

## Come Eseguire

```bash
python run.py        # Avvia server e client automaticamente
python test.py       # Esegue suite di test con diverse configurazioni
```

## Come Funziona

Il protocollo invia pacchetti numerati in una finestra scorrevole. Se un pacchetto si perde, il timer scade e ritrasmette tutti i pacchetti dalla base della finestra. Il server accetta solo pacchetti in ordine sequenziale e invia ACK cumulativi. Simula perdite casuali per testare la robustezza del protocollo.

**Risultato garantito**: Tutti i pacchetti arrivano al 100%, anche con perdite elevate.
