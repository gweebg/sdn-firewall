/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    register<bit<2>>(BLOOM_FILTER_ENTRIES) bloom_filter_state; // 0 is blocked; 1 is allowed; 2 is tcp waiting for ack of fin
    register<bit<16>>(BLOOM_FILTER_ENTRIES) bloom_filter_privatePort;
    register<ip4Addr_t>(BLOOM_FILTER_ENTRIES) bloom_filter_privateAddr;
    register<bit<16>>(BLOOM_FILTER_ENTRIES) bloom_filter_publicPort;
    register<ip4Addr_t>(BLOOM_FILTER_ENTRIES) bloom_filter_publicAddr;

    register<bit<8>>(1) currentServerID;


    // register<bit<16>>(BLOOM_FILTER_ENTRIES)     fiveT_localPort;
    // register<bit<16>>(BLOOM_FILTER_ENTRIES)     fiveT_remotePort;
    // register<ip4Addr_t>(BLOOM_FILTER_ENTRIES)   fiveT_localAddr;
    // register<ip4Addr_t>(BLOOM_FILTER_ENTRIES)   fiveT_remoteAddr;
    // register<bit<48>>(BLOOM_FILTER_ENTRIES)     entryTS;
    // register<bit<4>>(BLOOM_FILTER_ENTRIES)      direction;
    // register<bit<2>>(BLOOM_FILTER_ENTRIES)      newState;
    // register<bit<2>>(BLOOM_FILTER_ENTRIES)      read_state;
    // register<bit<16>>(BLOOM_FILTER_ENTRIES)     read_privatePort;
    // register<ip4Addr_t>(BLOOM_FILTER_ENTRIES)   read_privateAddr;
    // register<bit<16>>(BLOOM_FILTER_ENTRIES)     read_publicPort;
    // register<ip4Addr_t>(BLOOM_FILTER_ENTRIES)   read_publicAddr;
    // register<bit<32>>(1) debugRegisterPos;
    // action writeToDebug(){
    //     bit<32> index = 0;
    //     debugRegisterPos.read(index, 0);
    //     fiveT_localPort.write(index,  meta.tupleToCheck.localPort);
    //     fiveT_remotePort.write(index, meta.tupleToCheck.remotePort);
    //     fiveT_localAddr.write(index,  meta.tupleToCheck.localAddr);
    //     fiveT_remoteAddr.write(index, meta.tupleToCheck.remoteAddr);
    //     entryTS.write(index, standard_metadata.egress_global_timestamp);
    //     direction.write(index, meta.packetDirection);
    //     newState.write(index, meta.state);
    //     read_state.write(index, meta.register_cell_one.state);
    //     read_privatePort.write(index, meta.register_cell_one.privatePort);
    //     read_privateAddr.write(index, meta.register_cell_one.privateAddr);
    //     read_publicPort.write(index, meta.register_cell_one.publicPort);
    //     read_publicAddr.write(index, meta.register_cell_one.publicAddr);
    //     debugRegisterPos.write(0, index + 1);
    // }


    action drop() {
        mark_to_drop(standard_metadata);
    }


    action getRegisterPositions(){
        bit<32> bfEntrys = (bit<32>)BLOOM_FILTER_ENTRIES;
        //Get register position
        hash(meta.register_position_one, HashAlgorithm.crc16, (bit<32>)0, meta.tupleToCheck, bfEntrys);
        hash(meta.register_position_two, HashAlgorithm.crc32, (bit<32>)0, meta.tupleToCheck, bfEntrys);
    }

    action writeToBloomFiltersMetaState(){
        bloom_filter_state.write(meta.register_position_one, meta.state);
        bloom_filter_state.write(meta.register_position_two, meta.state);
    }

    action writeToBloomFilters(){
        bloom_filter_state.write(meta.register_position_one, meta.entryToWrite.state);
        bloom_filter_state.write(meta.register_position_two, meta.entryToWrite.state);

        bloom_filter_privatePort.write(meta.register_position_one, meta.entryToWrite.privatePort);
        bloom_filter_privatePort.write(meta.register_position_two, meta.entryToWrite.privatePort);

        bloom_filter_privateAddr.write(meta.register_position_one, meta.entryToWrite.privateAddr);
        bloom_filter_privateAddr.write(meta.register_position_two, meta.entryToWrite.privateAddr);

        bloom_filter_publicPort.write(meta.register_position_one, meta.entryToWrite.publicPort);
        bloom_filter_publicPort.write(meta.register_position_two, meta.entryToWrite.publicPort);

        bloom_filter_publicAddr.write(meta.register_position_one, meta.entryToWrite.publicAddr);
        bloom_filter_publicAddr.write(meta.register_position_two, meta.entryToWrite.publicAddr);
    }


    action readFromBloomFilters() {
        meta.register_cell_one = {0, 0, 0, 0, 0};
        meta.register_cell_two = {0, 0, 0, 0, 0};
        bloom_filter_state.read(meta.register_cell_one.state, meta.register_position_one);
        bloom_filter_state.read(meta.register_cell_two.state, meta.register_position_two);

        bloom_filter_privatePort.read(meta.register_cell_one.privatePort, meta.register_position_one);
        bloom_filter_privatePort.read(meta.register_cell_two.privatePort, meta.register_position_two);

        bloom_filter_privateAddr.read(meta.register_cell_one.privateAddr, meta.register_position_one);
        bloom_filter_privateAddr.read(meta.register_cell_two.privateAddr, meta.register_position_two);

        bloom_filter_publicPort.read(meta.register_cell_one.publicPort, meta.register_position_one);
        bloom_filter_publicPort.read(meta.register_cell_two.publicPort, meta.register_position_two);

        bloom_filter_publicAddr.read(meta.register_cell_one.publicAddr, meta.register_position_one);
        bloom_filter_publicAddr.read(meta.register_cell_two.publicAddr, meta.register_position_two);
    }

    action translateInboundPacket(){
        hdr.ipv4.dstAddr = meta.register_cell_one.privateAddr;
        hdr.ports.dstPort = meta.register_cell_one.privatePort;
        meta.AlreadyTranslated = 1;
    }

    action translateOutboundPacket(){
        hdr.ipv4.srcAddr = meta.register_cell_one.publicAddr;
        hdr.ports.srcPort = meta.register_cell_one.publicPort;
        meta.AlreadyTranslated = 1;
    }

    action RulesSuccess(bit<16> privPort){
        meta.default_rules_allowed = 1;
        // meta.entryToWrite.privatePort = privPort;
        meta.privatePort = privPort;
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
// table_add MyEgress.nextServerLookup setNextServer 0 => 10.4.0.10 10.4.0.1 3 0
    action setCurrentServer(ip4Addr_t privAddr, ip4Addr_t publicAddr, bit<8> nextSID){
        meta.cServer.privateAddr = privAddr;
        meta.cServer.publicAddr = publicAddr;
        meta.cServer.nextServerID = nextSID;
    }

    table ServerLookup {
        key = {
            meta.cServerID : exact;
        }
        actions = {
            setCurrentServer;
            NoAction;
        }
    }

    action setPublicPort(bit<16> pubPort){
        meta.publicPort = pubPort;
    }

    table privateToPublicPort {
        key = {
            meta.outboundPrivatePort: exact;
        }
        actions = {
            setPublicPort;
            NoAction;
        }
    }

    apply { 
        if (meta.AlreadyTranslated == 1 || meta.packetDirection == 3) {
            return;
        }
        currentServerID.read(meta.cServerID, 0);
        ServerLookup.apply();

        if ((hdr.tcp.isValid() && (hdr.tcp.rst == 1)) || (hdr.icmp.isValid() && hdr.icmp.type==0)){
            meta.state = 0;
        }
        else if (hdr.tcp.isValid() && hdr.tcp.fin == 1){
            meta.state = 2;
        }
        else {
            meta.state = 1;
        }

        if (!hdr.ports.isValid()){
            hdr.ports.srcPort = 0;
            hdr.ports.dstPort = 0;
        }

        if (meta.packetDirection == 1){
            if (meta.EnabledNAT == 0) {
                // five tuple outbound
                meta.tupleToCheck.localAddr = hdr.ipv4.srcAddr;
                meta.tupleToCheck.remoteAddr = hdr.ipv4.dstAddr;
                meta.tupleToCheck.localPort = hdr.ports.srcPort;
                meta.tupleToCheck.remotePort = hdr.ports.dstPort;
                meta.tupleToCheck.protocol = hdr.ipv4.protocol;    
            } else {
                meta.outboundPrivatePort = hdr.ports.srcPort;
                privateToPublicPort.apply();
                // five tuple nat outbound
                meta.tupleToCheck.localAddr = meta.cServer.publicAddr;
                meta.tupleToCheck.remoteAddr = hdr.ipv4.dstAddr;
                meta.tupleToCheck.localPort =  meta.publicPort;
                meta.tupleToCheck.remotePort = hdr.ports.dstPort;
                meta.tupleToCheck.protocol = hdr.ipv4.protocol;
            }
        } else if (meta.packetDirection == 2) {
            if (meta.EnabledNAT == 0) {
                // five tuple inbound
                meta.tupleToCheck.localAddr = hdr.ipv4.dstAddr;
                meta.tupleToCheck.remoteAddr = hdr.ipv4.srcAddr;
                meta.tupleToCheck.localPort = hdr.ports.dstPort;
                meta.tupleToCheck.remotePort = hdr.ports.srcPort;
                meta.tupleToCheck.protocol = hdr.ipv4.protocol;   
            } else {
                // five tuple nat inbound
                meta.tupleToCheck.localAddr = hdr.ipv4.dstAddr;
                meta.tupleToCheck.remoteAddr = hdr.ipv4.srcAddr;
                meta.tupleToCheck.localPort = hdr.ports.dstPort;
                meta.tupleToCheck.remotePort = hdr.ports.srcPort;
                meta.tupleToCheck.protocol = hdr.ipv4.protocol;    
            }
        }

        getRegisterPositions();
        readFromBloomFilters();

        // if (hdr.tcp.isValid()){
        //     writeToDebug();
        // }

        bool isStateAllowed = (meta.register_cell_one.state == 1 && meta.register_cell_two.state == 1);
        bool isAckAfterFin = hdr.tcp.isValid() && hdr.tcp.ack == 1 && meta.register_cell_one.state == 2;

        if (meta.packetDirection == 1) {
            if (meta.EnabledNAT == 0) {
                if (!hdr.tcp.isValid() || !isAckAfterFin){
                    meta.entryToWrite.state = meta.state;
                    meta.entryToWrite.privatePort = 0;
                    meta.entryToWrite.privateAddr = 0;
                    meta.entryToWrite.publicPort = 0;
                    meta.entryToWrite.publicAddr = 0;  
                    writeToBloomFilters();
                    return;
                } else {
                    return;
                }
            } else {
                if (!isStateAllowed){
                    if (!hdr.tcp.isValid() || !isAckAfterFin) {
                        // setFiveTupleNewNatOutbound();
                        meta.tupleToCheck.localAddr = meta.cServer.publicAddr;
                        meta.tupleToCheck.remoteAddr = hdr.ipv4.dstAddr;
                        meta.tupleToCheck.localPort = hdr.ports.srcPort;
                        meta.tupleToCheck.remotePort = hdr.ports.dstPort;
                        meta.tupleToCheck.protocol = hdr.ipv4.protocol;
                        getRegisterPositions();
                        // setFilterEntryNewNatOutbound();
                        meta.entryToWrite.state = meta.state;
                        meta.entryToWrite.privatePort = meta.tupleToCheck.localPort;
                        meta.entryToWrite.privateAddr = hdr.ipv4.srcAddr; 
                        meta.entryToWrite.publicPort = meta.tupleToCheck.localPort;
                        meta.entryToWrite.publicAddr = meta.cServer.publicAddr;
                        writeToBloomFilters();
                        meta.register_cell_one = meta.entryToWrite;
                    }
                } else {
                    writeToBloomFiltersMetaState();
                }
                translateOutboundPacket();
                recirculate_preserving_field_list(0);
            }
        }
        else if (meta.packetDirection == 2) {
            if (!isStateAllowed){
                if (!hdr.tcp.isValid() || !isAckAfterFin){
                    fwall_rules.apply();
                    if (meta.default_rules_allowed == 0) {
                        drop();
                        return;
                    }
                    if (meta.EnabledNAT == 0){
                        meta.entryToWrite.state = meta.state;
                        meta.entryToWrite.privatePort = 0;
                        meta.entryToWrite.privateAddr = 0;
                        meta.entryToWrite.publicPort = 0;
                        meta.entryToWrite.publicAddr = 0;  
                        writeToBloomFilters();
                    } else  {
                        // setFiveTupleNewNatInbound();
                        meta.tupleToCheck.localAddr = hdr.ipv4.dstAddr;
                        meta.tupleToCheck.remoteAddr = hdr.ipv4.srcAddr;
                        meta.tupleToCheck.localPort = hdr.ports.dstPort;
                        meta.tupleToCheck.remotePort = hdr.ports.srcPort;
                        meta.tupleToCheck.protocol = hdr.ipv4.protocol;
                        getRegisterPositions();
                        // setFilterEntryNewNatInbound();
                        meta.entryToWrite.state = meta.state;
                        meta.entryToWrite.privatePort = meta.privatePort;
                        meta.entryToWrite.privateAddr = meta.cServer.privateAddr;
                        meta.entryToWrite.publicPort = hdr.ports.dstPort;
                        meta.entryToWrite.publicAddr = meta.cServer.publicAddr; 
                        writeToBloomFilters();
                        meta.register_cell_one = meta.entryToWrite;
                        currentServerID.write(0, meta.cServer.nextServerID);
                    }
                }
            } else {
                writeToBloomFiltersMetaState();
            }

            if (meta.EnabledNAT == 1) {
                translateInboundPacket();
                recirculate_preserving_field_list(0);
            }
        }
    }
}