/**
* You can use this structure to pass 
* information between blocks/pipelines.
* This is user-defined. You can declare your own
* variables inside this structure.
*/
struct metadata {
    ip4Addr_t   next_hop_ipv4;
    bit<32> register_position_one;
    bit<32> register_position_two;

    bit<1> register_cell_one;
    bit<1> register_cell_two;
    bit<1> default_rules_allowed;
    bit<1> needs_fw;
    bit<1> is_response_to_icmp;
}