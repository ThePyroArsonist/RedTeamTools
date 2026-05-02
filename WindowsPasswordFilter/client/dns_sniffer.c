#include <pcap.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#endif

#define LOG_FILE "dns_log.txt"

FILE *logFile;

//  DEBUG 
int DEBUG = 1;

void debug_print(const char *msg) {
    if (DEBUG) printf("%s\n", msg);
}

// DNS PARSER
void parse_dns_name(const unsigned char *dns, char *output) {
    int i = 12; // skip DNS header
    int j = 0;

    while (dns[i] != 0 && j < 255) {
        int len = dns[i++];
        for (int k = 0; k < len; k++) {
            output[j++] = dns[i++];
        }
        output[j++] = '.';
    }

    if (j > 0) output[j - 1] = '\0';
}

// PACKET HANDLER
void packet_handler(unsigned char *args,
                    const struct pcap_pkthdr *header,
                    const unsigned char *packet) {

    printf("\n[RAW] Packet: %d bytes\n", header->caplen);

    const unsigned char *ip = NULL;
    int ip_version = 0;
    int ip_header_len = 0;

    // AUTO DETECT Functionality

    // Try raw (loopback)
    ip = packet;
    ip_version = ip[0] >> 4;

    if (ip_version != 4 && ip_version != 6) {
        // Try Ethernet offset
        ip = packet + 14;
        ip_version = ip[0] >> 4;
    }

    if (ip_version != 4 && ip_version != 6) {
        debug_print("[SKIP] Unknown packet type");
        return;
    }

    // IPv4
    if (ip_version == 4) {
        ip_header_len = (ip[0] & 0x0F) * 4;
        unsigned char protocol = ip[9];

        printf("[DEBUG] IPv4 detected | protocol=%d\n", protocol);

        if (protocol != 17) return; // not UDP

        const unsigned char *udp = ip + ip_header_len;
        unsigned short src_port = (udp[0] << 8) | udp[1];
        unsigned short dst_port = (udp[2] << 8) | udp[3];

        if (src_port != 53 && dst_port != 53) return;

        const unsigned char *dns = udp + 8;

        char domain[256] = {0};
        parse_dns_name(dns, domain);

        time_t now = time(NULL);

        printf("[DNS] %s\n", domain);
        fprintf(logFile, "[%lld] IPv4 DNS: %s\n", (long long)now, domain);
        fflush(logFile);
    }

    // IPv6
    else if (ip_version == 6) {
        printf("[DEBUG] IPv6 detected\n");

        unsigned char next_header = ip[6];
        if (next_header != 17) return; // not UDP

        const unsigned char *udp = ip + 40;

        unsigned short src_port = (udp[0] << 8) | udp[1];
        unsigned short dst_port = (udp[2] << 8) | udp[3];

        if (src_port != 53 && dst_port != 53) return;

        const unsigned char *dns = udp + 8;

        char domain[256] = {0};
        parse_dns_name(dns, domain);

        time_t now = time(NULL);

        printf("[DNSv6] %s\n", domain);
        fprintf(logFile, "[%lld] IPv6 DNS: %s\n", (long long)now, domain);
        fflush(logFile);
    }
}

// MAIN 
int main() {
    pcap_t *handle;
    char errbuf[PCAP_ERRBUF_SIZE];

    logFile = fopen(LOG_FILE, "a");
    if (!logFile) {
        printf("[-] Failed to open log file\n");
        return 1;
    }

    // INTERFACE SELECTION
    char *dev = pcap_lookupdev(errbuf);
    if (dev == NULL) {
        printf("[-] No device found: %s\n", errbuf);
        return 1;
    }

    printf("[+] Using interface: %s\n", dev);

    handle = pcap_open_live(dev, 65536, 1, 1000, errbuf);
    if (!handle) {
        printf("[-] Failed to open device: %s\n", errbuf);
        return 1;
    }

    // FILTER 
    struct bpf_program fp;
    char filter_exp[] = "udp port 53";

    if (pcap_compile(handle, &fp, filter_exp, 0, PCAP_NETMASK_UNKNOWN) == -1) {
        printf("[-] Filter compile error\n");
        return 1;
    }

    if (pcap_setfilter(handle, &fp) == -1) {
        printf("[-] Filter set error\n");
        return 1;
    }

    printf("[+] DNS sniffer running...\n");

    pcap_loop(handle, 0, packet_handler, NULL);

    pcap_close(handle);
    fclose(logFile);

    return 0;
}