/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action ipv4_fwd(ip4Addr_t nxt_hop, egressSpec_t port) {
        meta.next_hop_ipv4 = nxt_hop;
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
    } 

    table ipv4_lpm { 
        key = { 
            hdr.ipv4.dstAddr : lpm; 
        } 
        actions = {
            ipv4_fwd; drop; NoAction;
        }
        default_action = NoAction(); // NoAction is defined in vlmodel - does nothing
    }

    action rewrite_src_mac (macAddr_t src_mac) {
        hdr.ethernet.srcAddr = src_mac;
    }

    table src_mac {
        key = {
            standard_metadata.egress_spec : exact; 
        }
        actions = {
            rewrite_src_mac; drop;
        }
        default_action = drop;
    }

    action rewrite_dst_mac (macAddr_t dst_mac) {
        hdr.ethernet.dstAddr = dst_mac;
    }

    table dst_mac {
        key = { 
            meta.next_hop_ipv4 : exact; 
        }
        actions = {
            rewrite_dst_mac;
            drop; 
        }
        default_action = drop;
    }

    action reply_to_icmp(){
        if (hdr.icmp.type==8){
            ip4Addr_t dst = hdr.ipv4.dstAddr;
            hdr.ipv4.dstAddr = hdr.ipv4.srcAddr;
            hdr.ipv4.srcAddr = dst;
            hdr.icmp.type = 0;
            meta.is_response_to_icmp = 1;
        }
    }

    table self_icmp {
        key = {
            hdr.ipv4.dstAddr : exact;
        }
        actions = {
            reply_to_icmp;
            NoAction;
        }
        default_action = NoAction;
    }

    

    apply {
        if (hdr.ipv4.isValid()) {
            meta.is_response_to_icmp = 0;
            if (hdr.icmp.isValid()){
                self_icmp.apply();
            }
            ipv4_lpm.apply();
            src_mac.apply();
            dst_mac.apply();
        }
    }
}