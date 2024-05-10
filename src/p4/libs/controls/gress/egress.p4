/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    register<bit<1>>(BLOOM_FILTER_ENTRIES) bloom_filter;

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action set_needs_fw() {
        meta.needs_fw = 1;
    }
    
    action set_return_allowed(){
        hash(meta.register_position_one, HashAlgorithm.crc16, (bit<32>)0, {hdr.ipv4.srcAddr,
                                                                            hdr.ipv4.dstAddr,
                                                                            hdr.ports.srcPort,
                                                                            hdr.ports.dstPort,
                                                                            hdr.ipv4.protocol},
                                                                        (bit<32>)BLOOM_FILTER_ENTRIES);

        hash(meta.register_position_two, HashAlgorithm.crc32, (bit<32>)0, {hdr.ipv4.srcAddr,
                                                                            hdr.ipv4.dstAddr,
                                                                            hdr.ports.srcPort,
                                                                            hdr.ports.dstPort,
                                                                            hdr.ipv4.protocol},
                                                                        (bit<32>)BLOOM_FILTER_ENTRIES);
        bloom_filter.write(meta.register_position_one, 1);
        bloom_filter.write(meta.register_position_two, 1);
        meta.needs_fw = 0;
    }

    table check_controlled_networks{
        actions = {
            set_needs_fw;
            set_return_allowed;
        }
        key = {
            hdr.ipv4.srcAddr : lpm;
            hdr.ipv4.dstAddr : ternary;
        }
        default_action = set_return_allowed;
    }


    action check_allow_return(){
        //Get register position
        hash(meta.register_position_one, HashAlgorithm.crc16, (bit<32>)0, {hdr.ipv4.dstAddr,
                                                                                hdr.ipv4.srcAddr,
                                                                                hdr.ports.dstPort,
                                                                                hdr.ports.srcPort,
                                                                                hdr.ipv4.protocol},
                                                                            (bit<32>)BLOOM_FILTER_ENTRIES);

        hash(meta.register_position_two, HashAlgorithm.crc32, (bit<32>)0, {hdr.ipv4.dstAddr,
                                                                                hdr.ipv4.srcAddr,
                                                                                hdr.ports.dstPort,
                                                                                hdr.ports.srcPort,
                                                                                hdr.ipv4.protocol},
                                                                            (bit<32>)BLOOM_FILTER_ENTRIES);

        //Read bloom filter cells to check if there are 1's
        bloom_filter.read(meta.register_cell_one, meta.register_position_one);
        bloom_filter.read(meta.register_cell_two, meta.register_position_two);
    }

    action RulesSuccess(){
        meta.default_rules_allowed = 1;
    }

    action RulesBlocked(){
        meta.default_rules_allowed = 0;
    }

    table fwall_rules {
        key = { 
            hdr.ipv4.srcAddr : ternary;
            hdr.ipv4.dstAddr : ternary;
            hdr.ipv4.protocol : exact;
            hdr.ports.dstPort : exact;
        }
        actions = {
            RulesSuccess;
            RulesBlocked; 
        }
        default_action = RulesBlocked;
    }

    apply { 
        check_controlled_networks.apply();
        if (meta.needs_fw == 1 && meta.is_response_to_icmp == 0){
            fwall_rules.apply();
            if (meta.default_rules_allowed == 0) {
                check_allow_return();
                if (meta.register_cell_one != 1 || meta.register_cell_two != 1){
                    drop();
                    return;
                }
            }
        }
    }
}