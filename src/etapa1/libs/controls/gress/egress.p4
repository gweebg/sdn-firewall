/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    register<bit<2>>(BLOOM_FILTER_ENTRIES) bloom_filter;

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action setPortsToZero(){
        hdr.ports.srcPort = 0;
        hdr.ports.dstPort = 0;
    }

    action setFiveTupleOutbound(){
        meta.tupleToCheck.localAddr = hdr.ipv4.srcAddr;
        meta.tupleToCheck.remoteAddr = hdr.ipv4.dstAddr;
        meta.tupleToCheck.localPort = hdr.ports.srcPort;
        meta.tupleToCheck.remotePort = hdr.ports.dstPort;
        meta.tupleToCheck.protocol = hdr.ipv4.protocol;    
    }
    
    action setFiveTupleInbound(){
        meta.tupleToCheck.localAddr = hdr.ipv4.dstAddr;
        meta.tupleToCheck.remoteAddr = hdr.ipv4.srcAddr;
        meta.tupleToCheck.localPort = hdr.ports.dstPort;
        meta.tupleToCheck.remotePort = hdr.ports.srcPort;
        meta.tupleToCheck.protocol = hdr.ipv4.protocol;   
    }

    action getRegisterPositions(){
        bit<32> bfEntrys = (bit<32>)BLOOM_FILTER_ENTRIES;
        //Get register position
        hash(meta.register_position_one, HashAlgorithm.crc16, (bit<32>)0, meta.tupleToCheck, bfEntrys);
        hash(meta.register_position_two, HashAlgorithm.crc32, (bit<32>)0, meta.tupleToCheck, bfEntrys);
    }

    action writeState(){
        bloom_filter.write(meta.register_position_one, meta.state);
        bloom_filter.write(meta.register_position_two, meta.state);
    }

    action readState(){
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
        if (hdr.tcp.isValid() && hdr.tcp.rst == 1){
            meta.state = 0;
        }
        else if (hdr.tcp.isValid() && hdr.tcp.fin == 1){
            meta.state = 2;
        }
        else {
            meta.state = 1;
        }
        
        if (!hdr.ports.isValid()){
           setPortsToZero();
        }

        if (meta.packetDirection == 1) {
            setFiveTupleOutbound();
        } else if (meta.packetDirection == 2) {
            setFiveTupleInbound();
        }
        getRegisterPositions();
        readState();

        if (meta.packetDirection == 1 && (!hdr.tcp.isValid() || !(hdr.tcp.isValid() && hdr.tcp.ack == 1 && meta.register_cell_one == 2))) {
            writeState();
        }
        else if (meta.packetDirection == 2) {
            if (meta.register_cell_one != 1 || meta.register_cell_two != 1){
                if (hdr.tcp.isValid() && hdr.tcp.ack == 1 && meta.register_cell_one == 2){
                    meta.default_rules_allowed = 1;
                    meta.state = 2;
                } else {
                    fwall_rules.apply();
                }
                if (meta.default_rules_allowed == 0) {
                    drop();
                    return;
                } else { //escrever novo estado quando estado era 0 ou 2
                    writeState();
                }
            } else { //escrever novo estado quando estado era 1
                writeState();
            }
        } 
        else {
            NoAction();
        }
    }
}