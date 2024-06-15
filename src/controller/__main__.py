#!/usr/bin/env python3
import argparse
import os
import sys
from time import sleep

import grpc

import sys
from termcolor import colored

def print_banner():
    banner ="""
===========================================================================
 _____ ______  _   _         ______  _                               _  _ 
/  ___||  _  \| \ | |        |  ___|(_)                             | || |
\ `--. | | | ||  \| | ______ | |_    _  _ __   ___ __      __  __ _ | || |
 `--. \| | | || . ` ||______||  _|  | || '__| / _ \\\\ \ /\ / / / _` || || |
/\__/ /| |/ / | |\  |        | |    | || |   |  __/ \ V  V / | (_| || || |
\____/ |___/  \_| \_/        \_|    |_||_|    \___|  \_/\_/   \__,_||_||_|

===========================================================================
"""
    print(colored(banner, 'light_cyan', attrs=['bold']))
    sleep(1)

def print_warning_and_prompt():
    # Define the warning message
    warning_message = (
        "Using '--inject-anyways' can lead to out of sync table entries between the controller and target.\n"
        "This can cause unexpected behavior in the controller."
    )
    
    # Print the warning message in a fancy way
    print(colored('='*75, 'red'))
    print()
    print(colored(warning_message, 'red', attrs=['bold']))
    print()
    print(colored('='*75, 'red'))
    
    # Prompt the user to continue or not
    while True:
        user_input = input(colored("Do you want to continue? (yes/no): ", 'yellow', attrs=['bold']))
        if user_input.lower() in ['yes', 'y']:
            print(colored("Continuing with the operation.", 'green'))
            return True
        elif user_input.lower() in ['no', 'n']:
            print(colored("Operation aborted by the user.", 'green'))
            sys.exit(0)
        else:
            print(colored("Invalid input. Please enter 'yes' or 'no'.", 'red'))


## IMPORT LIBS FROM SOMEWHERE TO "UTILS" FOLDER
# TODO: Find a better way to do this
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),'utils'))
# Add the src directory to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from p4runtime_lib.error_utils import printGrpcError
from controller import TechController
from interactive import Interactive


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
    inject_anyways = args.inject_anyways
    interactive_mode = args.interactive
    verbose = args.verbose
    debug = args.debug
    print_banner()

    if (inject_anyways):
        print_warning_and_prompt()
    

    try:
        controller = TechController(p4info_file, bmv2_file, state_file) 

        print("=" * 75)
        for router in controller.routers.keys():
            print(colored(f"Injecting rules for {router}", "light_blue", attrs=['bold']))
            for rule in controller.routers[router].TableEntries:
                failled = controller.injectRule(rule, router, inject_anyways=inject_anyways, verbose=verbose, debug=debug)
                                        
            print("=" * 75)

        if interactive_mode:
            print()
            print("=" * 75)
            print(colored("Running in interactive mode", "light_green", attrs=['bold']))
            print("=" * 75)
            print()
            interactive = Interactive()
            interactive.run(controller.state)
        else:
            print(colored("Running in non-interactive mode", "yellow", attrs=['bold']))
            print(colored("Press Ctrl+C to stop", "red", attrs=['bold']))
            while True:
                sleep(10)

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
    parser.add_argument('--inject-anyways', help='Force injection mode',
                        action="store_true", required=False,
                        default=False)
    parser.add_argument('--interactive', help='Interactive mode',
                        action="store_true", required=False,
                        default=False)
    parser.add_argument('-v', '--verbose', help='Verbose mode',
                        action="store_true", required=False,
                        default=False)
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