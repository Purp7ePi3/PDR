import threading
import time
from server import GBNServer
from client import GBNClient

def main():
    # Avvia server
    server = GBNServer()
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    time.sleep(1)
    client = GBNClient()
    client.start()

if __name__ == "__main__":
    main()