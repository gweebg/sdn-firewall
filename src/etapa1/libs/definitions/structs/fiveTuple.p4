struct fiveTuple {
    ip4Addr_t localAddr;
    ip4Addr_t remoteAddr;
    bit<16> localPort;
    bit<16> remotePort;
    bit<8> protocol;
}