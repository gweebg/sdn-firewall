#!/usr/bin/env python3
import argparse
import os
import sys
from time import sleep

import grpc

# Import P4Runtime lib from utils dir
# Probably there's a better way of doing this.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),'utils/'))

import p4runtime_lib.bmv2
import p4runtime_lib.helper

from ..topology.config.loader import getState, State, Host, Router, Switch, PortL3, Rule


class TechController:
    def __init__(self, p4info_file: str = None, bmv2_file: str = None, state_file: str = None):
        if p4info_file is not None:
            self.p4info_file = p4info_file
        else:
            self.p4info_file = 'build/s-router.p4.p4info.txt'
        if bmv2_file is not None:
            self.bmv2_file = bmv2_file
        else:
            self.bmv2_file = 'build/s-router.json'
        if state_file is not None:
            self.state_file = state_file
        else:
            self.state_file = 'config/network.yml'

        self.runtime_connections: dict[str, p4runtime_lib.bmv2.Bmv2SwitchConnection] = {}
        self.state = getState(self.state_file)
        self.routers = self.state.routers
        self.p4info_helper = p4runtime_lib.helper.P4InfoHelper(self.p4info_file)

        ## initialize connections
        for router in self.routers.keys():
            self.runtime_connections[router] = self.connect(router)


    def connect(self, router: str) -> p4runtime_lib.bmv2.Bmv2SwitchConnection:
        r = p4runtime_lib.bmv2.Bmv2SwitchConnection(
            name=router,
            address=f'127.0.0.1:{self.routers[router].grpc_port}',
            device_id=self.routers[router].macDeviceId,
            proto_dump_file=f'logs/{router}-p4runtime-request.txt'
        )
        r.MasterArbitrationUpdate()
        r.SetForwardingPipelineConfig(p4info=self.p4info_helper.p4info,
                                      bmv2_json_file_path=self.bmv2_file)
        
        ## reset_state
        ## table_set_default ipv4_lpm drop
        ## table_set_default dst_mac drop
        ## table_set_default src_mac drop
        ## table_set_default check_controlled_networks set_return_allowed

        r.WriteTableEntry(self.p4info_helper.buildTableEntry(
            table_name="ipv4_lpm",
            default_action=True,
            action_name="drop"
        ))
        r.WriteTableEntry(self.p4info_helper.buildTableEntry(
            table_name="dst_mac",
            default_action=True,
            action_name="drop"
        ))
        r.WriteTableEntry(self.p4info_helper.buildTableEntry(
            table_name="src_mac",
            default_action=True,
            action_name="drop"
        ))
        r.WriteTableEntry(self.p4info_helper.buildTableEntry(
            table_name="check_controlled_networks",
            default_action=True,
            action_name="set_return_allowed"
        ))
        return r
    
    def __printCounter(self, router: str, counter_name: str, index: int):
        for response in self.runtime_connections[router].ReadCounters(self.p4info_helper.get_counters_id(counter_name), index):
            for entity in response.entities:
                counter = entity.counter_entry
                print(f"{router} {counter_name} {index}: {counter.data.packet_count} packets ({counter.data.byte_count} bytes)")

    def __readTableRules(self, router: str):
        print(f'\n----- Reading tables rules for {router} -----')
        for response in self.runtime_connections[router].ReadTableEntries():
            for entity in response.entities:
                entry = entity.table_entry
                table_name = self.p4info_helper.get_tables_name(entry.table_id)
                print(f'{table_name}: ', end=' ')
                for m in entry.match:
                    print(self.p4info_helper.get_match_field_name(table_name, m.field_id), end=' ')
                    print(f'{self.p4info_helper.get_match_field_value(m)}', end=' ')
                action = entry.action.action
                action_name = self.p4info_helper.get_actions_name(action.action_id)
                print('->', action_name, end=' ')
                for p in action.params:
                    print(self.p4info_helper.get_action_param_name(action_name, p.param_id), end=' ')
                    print(f'{p.value}', end=' ')
                print()

    ## table_add ipv4_lpm ipv4_fwd 10.0.1.10/32 => 10.0.1.10 1
    def __injectFwdRules(self, router: str, table_name: str, action_name: str):
        r = self.routers[router]
        for l in r.linksL3.values():
            remotePort: PortL3 = l.getOtherPortFromLocalName(router.nodeName)
            mask = 24 if remotePort.ip.host == 1 else 32
            strIp = remotePort.ip.getCompleteIp()
            table_entry = self.p4info_helper.buildTableEntry(
                table_name=table_name,
                match_fields={
                    "hdr.ipv4.dstAddr": (strIp, mask)
                },
                action_name=action_name,
                action_params={
                    "nxt_hop": strIp,
                    "port": l.ports[r.nodeName].portId,
                })
            self.runtime_connections[router].WriteTableEntry(table_entry)
        print(f"Installed FWD rule on {router}")

    ##table_add fwall_rules RulesSuccess {rule.srcIp.GetCompleteTernaryFormat()} {rule.dstIp.GetCompleteTernaryFormat()} {rule.protocol} {rule.Port} 1 1
    def __injectFwallRules(self, router: str, table_name: str, action_name: str):
        router_ = self.routers[router]
        for rule in router_.rules:
            table_entry = self.p4info_helper.buildTableEntry(
                table_name=table_name,
                match_fields={
                    "srcIp": rule.srcIp.GetCompleteTernaryFormat(),
                    "dstIp": rule.dstIp.GetCompleteTernaryFormat(),
                    "protocol": rule.protocol,
                    "Port": rule.Port
                },
                action_name=action_name,
                action_params={},
                priority=1,
                timeout=1
                )
            self.runtime_connections[router].WriteTableEntry(table_entry)

        
    def __injectSrcMacRules(self, router: str, table_name: str, action_name: str):
        for port in self.routers[router].ports.values():
            table_entry = self.p4info_helper.buildTableEntry(
                table_name=table_name,
                match_fields={
                    "standard_metadata.ingress_port": port.portId
                },
                action_name=action_name,
                action_params={
                    "src_mac": port.mac
                })
            self.runtime_connections[router].WriteTableEntry(table_entry)
        print(f"Installed SRC_MAC rule on {router}")

    def __injectDstMacRules(self, router: str, table_name: str, action_name: str):
        for l in self.routers[router].linksL3.values():
            remotePort: PortL3 = l.getOtherPortFromLocalName(router)
            table_entry = self.p4info_helper.buildTableEntry(
                table_name=table_name,
                match_fields={
                    "hdr.ipv4.dstAddr": remotePort.ip.getCompleteIp()
                },
                action_name=action_name,
                action_params={
                    "dst_mac": remotePort.mac
                })
            self.runtime_connections[router].WriteTableEntry(table_entry)
        print(f"Installed DST_MAC rule on {router}")