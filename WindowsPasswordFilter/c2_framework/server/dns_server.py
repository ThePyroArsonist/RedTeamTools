from dnslib.server import DNSServer, BaseResolver
from dnslib import RR, QTYPE, A
import base64
import random
import time
import threading

# Global storage for reassembly
sessions = {}
buffer = {}

class DNSHandler(BaseResolver):
    """
    DNSHandler processes incoming DNS queries and extracts encoded data
    from subdomains. It reconstructs messages per client session.
    """

    def resolve(self, request, handler):
        qname = str(request.q.qname)
        client_ip = handler.client_address[0]

        print(f"[+] Query from {client_ip}: {qname}")

        # Extract subdomain (before base domain)
        parts = qname.split('.')
        if len(parts) < 3:
            return request.reply()

        encoded_chunk = parts[0]

        # Store per-client session
        if client_ip not in sessions:
            sessions[client_ip] = []

        sessions[client_ip].append(encoded_chunk)

        # Attempt decode (best-effort)
        try:
            combined = ''.join(sessions[client_ip])
            decoded = base64.b64decode(combined).decode(errors='ignore')
            print(f"[DATA] {client_ip}: {decoded}")
        except Exception:
            pass

        # Response channel (bi-directional) ---
        reply = request.reply()
        reply.add_answer(RR(
            rname=request.q.qname,
            rtype=QTYPE.A,
            rclass=1,
            ttl=60,
            rdata=A("127.0.0.1")  # placeholder response
        ))

        return reply
    
    def receive_packet(client, seq, data):

        if client not in buffer:
            buffer[client] = {}

        buffer[client][seq] = data
        print(f"[RECV] {client} seq={seq}")

    def reassemble(client):
        if client not in buffer:
            return None

        ordered = [buffer[client][k] for k in sorted(buffer[client])]
        return "".join(ordered)


if __name__ == "__main__":
    resolver = DNSHandler()
    server = DNSServer(resolver, port=53, address="0.0.0.0")

    print("[*] DNS Server running...")
    server.start()