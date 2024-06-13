struct filterEntry {
    bit<2> state;
    bit<16> privatePort;
    ip4Addr_t privateAddr;
    bit<16> publicPort;
    ip4Addr_t publicAddr;
}