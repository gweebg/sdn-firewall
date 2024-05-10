const bit<16> TYPE_IPV4 = 0x800;
const bit<8> TYPE_ICMP = 0x1;
const bit<8> TYPE_TCP  = 0x06;
const bit<8> TYPE_UDP  = 0x11;

#define BLOOM_FILTER_ENTRIES 4096

/* simple typedef to ease your task */

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;