import time
from dns_server import sessions

def show_sessions():
    """
    Displays active DNS sessions and reconstructed payloads.
    """
    while True:
        print("\n=== Active Sessions ===")
        for ip, chunks in sessions.items():
            print(f"\nClient: {ip}")
            print(f"Chunks: {len(chunks)}")

        time.sleep(5)


if __name__ == "__main__":
    show_sessions()