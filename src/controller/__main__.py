#!/usr/bin/env python3
import argparse
import os
import sys
from time import sleep

import grpc
from p4runtime_lib.error_utils import printGrpcError

from controller.controller import TechController


## IMPORT LIBS FROM SOMEWHERE TO "UTILS" FOLDER
# TODO: Find a better way to do this
def import_utils():
    # Import P4Runtime lib from utils dir
    # Probably there's a better way of doing this.
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),'utils/'))
    pass

def printGrpcError(e):
    print("gRPC Error:", e.details(), end=' ')
    status_code = e.code()
    print("(%s)" % status_code.name, end=' ')
    traceback = sys.exc_info()[2]
    print("[%s:%d]" % (traceback.tb_frame.f_code.co_filename, traceback.tb_lineno))


def main(args: argparse.Namespace):
    p4info_file = args.p4info
    bmv2_file = args.bmv2_json
    state_file = args.state
    

    try:
        controller = TechController(p4info_file, bmv2_file, state_file) 

        for router in controller.routers.keys():
            controller.__injectFwdRules(router, "ipv4_lpm", "ipv4_fwd")
            controller.__injectSrcMacRules(router, "src_mac", "set_src_mac")
            controller.__injectDstMacRules(router, "dst_mac", "set_dst_mac")
            controller.__injectFwallRules(router, "fwall_rules", "RulesSuccess")
            print(f"Injected all rules on {router}")      


        while True:
            sleep(10)
            print('\n----- Reading counters -----')
            for router in controller.routers.keys():
                controller.__printCounter(router, "MyIngress.c", 0)
                controller.__printCounter(router, "MyIngress.c", 1)

    except KeyboardInterrupt:
        print(" Shutting down.")
    except grpc.RpcError as e:
        printGrpcError(e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='P4Runtime Controller')
    parser.add_argument('--p4info', help='p4info proto in text format from p4c',
                        type=str, action="store", required=False,
                        default='build/s-router.p4.p4info.txt')
    parser.add_argument('--bmv2-json', help='BMv2 JSON file from p4c',
                        type=str, action="store", required=False,
                        default='build/s-router.json')
    parser.add_argument('--state', help='State file',
                        type=str, action="store", required=False,
                        default='config/network.yml')
    args = parser.parse_args()

    if not os.path.exists(args.p4info):
        parser.print_help()
        print("\np4info file not found:")
        parser.exit(1)
    if not os.path.exists(args.bmv2_json):
        parser.print_help()
        print("\nBMv2 JSON file not found:")
        parser.exit(1)
    main(args)