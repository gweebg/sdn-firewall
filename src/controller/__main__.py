#!/usr/bin/env python3
import argparse
import os
import sys
from time import sleep

import grpc


## IMPORT LIBS FROM SOMEWHERE TO "UTILS" FOLDER
# TODO: Find a better way to do this
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),'utils'))
# Add the src directory to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from p4runtime_lib.error_utils import printGrpcError
from controller import TechController


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

        print("=" * 75)
        for router in controller.routers.keys():
            print(f"Injecting rules on {router}")
            fwd = controller.injectFwdRules(router, "ipv4_lpm", "ipv4_fwd")
            src = controller.injectSrcMacRules(router, "src_mac", "rewrite_src_mac")
            dst = controller.injectDstMacRules(router, "dst_mac", "rewrite_dst_mac")
            fwl =controller.injectFwallRules(router, "fwall_rules", "RulesSuccess")
            print(f"{'Forward: Success' if fwd else 'Forward: Failed'}")
            print(f"{'Src Mac: Success' if src else 'Src Mac: Failed'}")
            print(f"{'Dst Mac: Success' if dst else 'Dst Mac: Failed'}")
            print(f"{'Firewall: Success' if fwl else 'Firewall: Failed'}")
            if fwd and src and dst and fwl:
                print(f"Rules injected on {router}")
            else:
                print(f"Failed to inject some rules on {router}")
                            
            print("=" * 75)

        while True:
            sleep(10)
            if args.debug:
                print('\n----- Reading Rules -----')
                print("=" * 75)
                for router in controller.routers.keys():
                    controller.readTableRules(router)
                    print("=" * 75)


    except KeyboardInterrupt:
        print(" Shutting down.")
    except grpc.RpcError as e:
        printGrpcError(e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='P4Runtime Controller')
    parser.add_argument('--p4info', help='p4info proto in text format from p4c',
                        type=str, action="store", required=False,
                        default='json/simple-router.p4.p4info.txt')
    parser.add_argument('--bmv2-json', help='BMv2 JSON file from p4c',
                        type=str, action="store", required=False,
                        default='json/simple-router.json')
    parser.add_argument('--state', help='State file',
                        type=str, action="store", required=False,
                        default='config/network.yml')
    parser.add_argument('--debug', help='Debug mode',
                        action="store_true", required=False,
                        default=False)
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