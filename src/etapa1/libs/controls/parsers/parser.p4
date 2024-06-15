/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {
    /**
     * a parser always begins in the start state
     * a state can invoke other state with two methods
     * transition <next-state>
     * transition select(<expression>) -> works like a switch case
     */

    state parse_tcp {
        packet.extract(hdr.ports); // extract function populates the ports header
        packet.extract(hdr.tcp);
        transition accept;
    }

    state parse_udp {
        packet.extract(hdr.ports); // extract function populates the ports header
        packet.extract(hdr.udp);
        transition accept;
    }
    

    state parse_ipv4 {
        packet.extract(hdr.ipv4); // extract function populates the ipv4 header
        transition select(hdr.ipv4.protocol) {
            TYPE_TCP: parse_tcp;
            TYPE_UDP:  parse_udp;
            default: accept;
        }
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4:  parse_ipv4;
            default: accept;
        }
    }

    state start {
        transition parse_ethernet;
    }
}