/**
* You can use this structure to pass 
* information between blocks/pipelines.
* This is user-defined. You can declare your own
* variables inside this structure.
*/
struct metadata {
    @field_list(0)
    bit<1> EnabledICMP;
    @field_list(0)
    bit<1> EnabledNAT;
    @field_list(0)
    bit<1> AlreadyTranslated;
    
    bit<32> register_position_one;
    bit<32> register_position_two;

    @field_list(0)
    bit<4> packetDirection; // 1:outbound; 2:inbound; 3: passing

    ip4Addr_t   next_hop_ipv4;

    filterEntry register_cell_one;
    filterEntry register_cell_two;

    bit<1> default_rules_allowed;

    bit<16> tcpLength;
    bit<16> privatePort;
    bit<16> outboundPrivatePort;
    bit<16> publicPort;
    
    bit<8> cServerID;
    currentServer cServer;

    bit<2> state;

    fiveTuple tupleToCheck;
    filterEntry entryToWrite;
}