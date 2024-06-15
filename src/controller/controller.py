#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from time import sleep

from termcolor import colored

import grpc

# Import P4Runtime lib from utils dir
# Probably there's a better way of doing this.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),'utils/'))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../topology'))) # Add the src directory to the system path

import p4runtime_lib.bmv2
import p4runtime_lib.helper

from topology.config.loader import getState, PortL3
from topology.rules.rules import Rule

def printGrpcError(e):
    print("gRPC Error:", e.details(), end=' ')
    status_code = e.code()
    print("(%s)" % status_code.name, end=' ')
    traceback = sys.exc_info()[2]
    print("[%s:%d]" % (traceback.tb_frame.f_code.co_filename, traceback.tb_lineno))

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
        self.state = getState(self.state_file,3)
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
        return r
    
    def printCounter(self, router: str, counter_name: str, index: int):
        for response in self.runtime_connections[router].ReadCounters(self.p4info_helper.get_counters_id(counter_name), index):
            for entity in response.entities:
                counter = entity.counter_entry
                print(f"{router} {counter_name} {index}: {counter.data.packet_count} packets ({counter.data.byte_count} bytes)")

    def readTableRules(self, router: str):
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

    def injectRule(self, rule: Rule, router: str, inject_anyways: bool = False, verbose: bool = False, debug: bool = False):            
        try:
            r = self.routers[router]
            action_params = {rule.ActionArgs[i]: rule.values[rule.ActionArgs[i]][1] if type(rule.values[rule.ActionArgs[i]]) is tuple else rule.values[rule.ActionArgs[i]] for i in range(len(rule.ActionArgs))}
            if rule.IsSettingDefault:
                table_entry = self.p4info_helper.buildTableEntry(
                    table_name=rule.TableName,
                    action_name=rule.ActionName,
                    action_params=action_params,
                    default_action=True,
                    priority=1 if rule.hasPrio else None)
            else:
                match_fields = {rule.Keys[i]: rule.values[rule.Keys[i]][1] if type(rule.values[rule.Keys[i]]) is tuple else rule.values[rule.Keys[i]] for i in range(len(rule.Keys))}
                if "hdr.ipv4.protocol" in match_fields.keys():
                    match_fields["hdr.ipv4.protocol"] = int(match_fields["hdr.ipv4.protocol"],16)
                action_params = None if len(action_params.keys()) == 0 else action_params
                table_entry = self.p4info_helper.buildTableEntry(
                    table_name=rule.TableName,
                    match_fields=match_fields,
                    action_name=rule.ActionName,
                    action_params=action_params,
                    priority=1 if rule.hasPrio else None)                
            try:
                self.runtime_connections[router].WriteTableEntry(table_entry)
                if debug:
                    print(table_entry)
                if verbose:
                    print(colored(f"Rule {type(rule)} {rule} injected.", "green"))
            except Exception as e:
                if not inject_anyways:
                    raise e
                else:
                    if verbose:
                        print(colored(f"Rule {type(rule)} {rule} failed. Trying to inject it manually.", "light_red"))
                    result = subprocess.run(f"echo {rule} | simple_switch_CLI --thrift-port {r.thrift_port}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if verbose:
                        if result.returncode != 0:
                            print(colored(f"Rule {type(rule)} {rule} failed to inject manually.", "red", attrs=['bold']))
                        else:
                            print(colored(f"Rule {type(rule)} {rule} injected manually.", "blue", attrs=['bold']))
                ## If the rule fails to inject, inject it manually and raise the exception, the table entry will be out of sync with the controller
            return True
        except Exception as e:
            if verbose:
                print(colored(f"Rule {type(rule)} {rule} failed to inject.", "light_red"))
            if debug:
                print(f"Error {e}")
                print("-" * 75)
            return False
