# Requires pip install dnspython

import dns.resolver

def main():
    target_ip = input("Enter DNS server IP (e.g. 8.8.8.8): ").strip()

    if not target_ip:
        target_ip = "8.8.8.8"

    domain = input("Enter domain to query (e.g. google.com): ").strip()

    if not domain:
        domain = "google.com"

    resolver = dns.resolver.Resolver()

    # Force custom DNS server
    resolver.nameservers = [target_ip]

    try:
        print(f"\n[+] Querying {domain} via {target_ip}...\n")
        answers = resolver.resolve(domain, "A")

        for rdata in answers:
            print("Result:", rdata.to_text())

    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()