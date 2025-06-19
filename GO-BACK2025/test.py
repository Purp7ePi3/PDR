"""
Test suite per il protocollo Go-Back-N
Testa diversi scenari: nessuna perdita, perdita moderata, perdita alta
"""

import time
import threading
import sys
import os

# Importa le classi dai file corretti
try:
    from server import GBNServer
    from client import GBNClient
except ImportError as e:
    print(f"Errore importazione: {e}")
    sys.exit(1)

class GBNTester:
    def __init__(self):
        self.test_results = []
        
    def run_test(self, test_name, server_loss, client_loss, window_size, num_packets, timeout, max_duration=60):
        """Esegue un singolo test con timeout massimo"""
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"{'='*60}")
        print(f"Configurazione:")
        print(f"  Perdita ACK server: {server_loss*100}%")
        print(f"  Perdita pacchetti client: {client_loss*100}%") 
        print(f"  Finestra: {window_size}")
        print(f"  Pacchetti: {num_packets}")
        print(f"  Timeout: {timeout}s")
        print(f"  Durata massima: {max_duration}s")
        
        # Stima probabilità di successo
        combined_loss = server_loss + client_loss
        if combined_loss > 1.0:
            expected_difficulty = "ESTREMO"
        elif combined_loss > 0.6:
            expected_difficulty = "MOLTO DIFFICILE"
        elif combined_loss > 0.3:
            expected_difficulty = "DIFFICILE"
        elif combined_loss > 0.1:
            expected_difficulty = "MODERATO"
        else:
            expected_difficulty = "FACILE"
        print(f"  Difficoltà attesa: {expected_difficulty}")
        print()
        
        # Setup test
        test_port = 8081 + len(self.test_results)
        server = GBNServer('localhost', test_port, server_loss)
        client = GBNClient('localhost', test_port, window_size, timeout, client_loss)
        
        # Avvia server
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True
        server_thread.start()
        time.sleep(0.5)
        
        # Esegui client con timeout
        start_time = time.time()
        test_completed = False
        test_timeout = False
        
        def run_client():
            nonlocal test_completed
            try:
                client.start(num_packets)
                test_completed = True
            except Exception as e:
                print(f"Errore client: {e}")
        
        client_thread = threading.Thread(target=run_client)
        client_thread.start()
        client_thread.join(timeout=max_duration)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Controlla se il test è andato in timeout
        if client_thread.is_alive():
            test_timeout = True
            client.running = False
            print(f"TIMEOUT: Test terminato dopo {max_duration}s")
        
        server.stop()
        
        # Calcola metriche
        success_rate = (client.base / num_packets) * 100 if num_packets > 0 else 0
        retrans_rate = (client.stats['retransmissions'] / client.stats['packets_sent']) * 100 if client.stats['packets_sent'] > 0 else 0
        
        # Determina esito
        if test_timeout:
            test_result = "TIMEOUT"
        elif success_rate == 100:
            test_result = "PASS"
        elif success_rate >= 80:
            test_result = "PARTIAL"
        else:
            test_result = "FAIL"
        
        result = {
            'name': test_name,
            'success_rate': success_rate,
            'duration': duration,
            'packets_sent': client.stats['packets_sent'],
            'retransmissions': client.stats['retransmissions'],
            'retrans_rate': retrans_rate,
            'timeouts': client.stats['timeouts'],
            'acks_received': client.stats['acks_received'],
            'test_result': test_result,
            'test_timeout': test_timeout,
            'expected_difficulty': expected_difficulty
        }
        
        self.test_results.append(result)
        
        # Stampa risultati
        print(f"RISULTATI TEST '{test_name}':")
        print(f"  Successo: {success_rate:.1f}%")
        print(f"  Durata: {duration:.2f}s")
        print(f"  Pacchetti inviati: {client.stats['packets_sent']}")
        print(f"  Ritrasmissioni: {client.stats['retransmissions']} ({retrans_rate:.1f}%)")
        print(f"  Timeout eventi: {client.stats['timeouts']}")
        print(f"  ACK ricevuti: {client.stats['acks_received']}")
        print(f"  ESITO: {test_result}")
        
        if test_result == "PASS":
            print("  STATUS: Test superato completamente")
        elif test_result == "PARTIAL":
            print("  STATUS: Test parzialmente superato")
        elif test_result == "TIMEOUT":
            print("  STATUS: Test terminato per timeout (normale con perdite estreme)")
        else:
            print("  STATUS: Test fallito")
            
        return result
    
    def run_all_tests(self):
        """Esegue tutti i test predefiniti"""
        print("SUITE DI TEST GO-BACK-N ARQ")
        print("Include test progressivamente più difficili fino a condizioni estreme")
        print()
        
        # Test 1: Condizioni ideali
        self.run_test(
            "Condizioni Ideali",
            server_loss=0.0,
            client_loss=0.0,
            window_size=4,
            num_packets=10,
            timeout=2.0,
            max_duration=30
        )
        
        # Test 2: Perdite moderate
        self.run_test(
            "Perdita Moderata", 
            server_loss=0.1,
            client_loss=0.1,
            window_size=4,
            num_packets=15,
            timeout=2.0,
            max_duration=45
        )
        
        # Test 3: Perdite significative
        self.run_test(
            "Perdita Alta",
            server_loss=0.25,
            client_loss=0.2,
            window_size=3,
            num_packets=12,
            timeout=1.5,
            max_duration=60
        )
        
        # Test 4: Finestra grande
        self.run_test(
            "Finestra Grande",
            server_loss=0.15,
            client_loss=0.1,
            window_size=8,
            num_packets=20,
            timeout=3.0,
            max_duration=60
        )
        
        # Test 5: Stress test severo
        self.run_test(
            "Stress Test",
            server_loss=0.3,
            client_loss=0.25,
            window_size=2,
            num_packets=25,
            timeout=0.5,
            max_duration=45
        )
        
        # Test 6: Test progettato per fallire
        self.run_test(
            "100% Failure",
            server_loss=0.98,
            client_loss=0.95,
            window_size=1,
            num_packets=25,
            timeout=0.05,
            max_duration=3
        )
                    
        self.print_summary()
    
    def print_summary(self):
        print(f"\n{'='*90}")
        print("RIASSUNTO COMPLETO DEI TEST")
        print(f"{'='*90}")
        
        print(f"{'Test':<20} {'Difficoltà':<15} {'Esito':<8} {'Successo':<9} {'Durata':<8} {'Ritrasm.':<9}")
        print("-" * 90)
        
        total_tests = len(self.test_results)
        passed_tests = 0
        timeout_tests = 0
        
        for result in self.test_results:
            if result['test_result'] in ['PASS', 'PARTIAL']:
                passed_tests += 1
            if result['test_timeout']:
                timeout_tests += 1
                
            print(f"{result['name']:<20} {result['expected_difficulty']:<15} {result['test_result']:<8} "
                  f"{result['success_rate']:>6.1f}% {result['duration']:>6.2f}s {result['retransmissions']:>7d}")
        
        print("-" * 90)
        print(f"STATISTICHE SUITE:")
        print(f"  Test completati: {total_tests}")
        print(f"  Test superati: {passed_tests}")
        print(f"  Test falliti: {total_tests - passed_tests}")
        print(f"  Test per timeout: {timeout_tests}")
        print(f"  Tasso successo: {(passed_tests/total_tests)*100:.1f}%")
      
        total_packets = sum(r['packets_sent'] for r in self.test_results)
        total_retrans = sum(r['retransmissions'] for r in self.test_results)
        total_timeouts = sum(r['timeouts'] for r in self.test_results)
        avg_success = sum(r['success_rate'] for r in self.test_results) / total_tests
        
        print(f"\nSTATISTICHE AGGREGATE:")
        print(f"  Pacchetti totali inviati: {total_packets}")
        print(f"  Ritrasmissioni totali: {total_retrans}")
        print(f"  Eventi timeout totali: {total_timeouts}")
        print(f"  Tasso successo medio: {avg_success:.1f}%")
        
        if total_packets > 0:
            overall_retrans_rate = (total_retrans / total_packets) * 100
            print(f"  Tasso ritrasmissioni globale: {overall_retrans_rate:.1f}%")
                    
def main():   
    print("TEST SUITE GO-BACK-N ARQ PROTOCOL")
    print("="*50)
    
    # Verifica file necessari
    required_files = ['server.py', 'client.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("ERRORE: File mancanti:")
        for file in missing_files:
            print(f"  - {file}")
        return
    
    tester = GBNTester()
    
    try:
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\nTest interrotti dall'utente")
    except Exception as e:
        print(f"\nErrore durante i test: {e}")

if __name__ == "__main__":
    main()