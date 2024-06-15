import subprocess
from termcolor import colored


"""
main_commands:
- list devices;
- select <device_name>;
- exit;
- help;
- clear;

device_commands:
- list tables;
- inject <rule>;
- show <table>;
- clear;
- help;
- exit;

"""

class Interactive:
    def __init__(self):
        self.prompt = ">>> "
        self.router = None
        self.commands = {
            "main": {
                "list-devices": self.list_devices,
                "select": self.select_device,
                "exit": self.exit,
                "help": self.help,
                "clear": self.clear
            },
            "device": {
                "list-tables": self.list_tables,
                "inject": self.inject_rule,
                "show": self.show_table,
                "clear": self.clear,
                "help": self.help,
                "exit": self.exit
            }
        }

    def help(self, state=None, args=None):
        if self.router is None:
            return self.help_main(state, args)
        return self.help_device(state, args)
    
    def exit(self, state=None, args=None):
        if self.router is None:
            return self.exit_main(state, args)
        return self.exit_device(state, args)

    def help_main(self, state=None, args=None):
        # Use the colored function to colorize the output
        print(colored("Main commands:", "green"))
        print("- list-devices;")
        print("- select <device_name>;")
        print("- exit;")
        print("- help;")
        print("- clear;")
        print()
        return True
    
    def help_device(self, state=None, args=None):
        print(colored("Device commands:", "green"))
        print("- list-tables;")
        print("- inject <rule>;");
        print("- show <table>;");
        print("- clear;")
        print("- help;")
        print("- exit;")
        print()
        return True

    def list_devices(self, state, args=None):
        print(colored("Devices:", "green"))
        for router in state.routers.keys():
            print(router)
        print()
        return True
    
    def select_device(self, state, router):
        if router in state.routers.keys():
            self.router = state.routers[router]
            print(colored(f"Selected {router}", "green"))
        else:
            print(colored(f"Device {router} not found", "red"))
        return True

    def exit_main(self, state=None, args=None):
        return False
    
    def exit_device(self, state=None, args=None):
        self.router = None
        return True
    
    def clear(self, state=None, args=None):
        """Clear the screen"""
        subprocess.run("clear", shell=True, stderr=subprocess.DEVNULL)
        return True

    def list_tables(self, state=None, args=None):
        if self.router is None:
            print(colored("No device selected", "red"))
            return
        print(colored(f"Tables for {self.router.nodeName}:", "green"))
        command = "echo 'show_tables' | simple_switch_CLI --thrift-port %d | grep My" % self.router.thrift_port
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(colored("Error while listing tables", "red"))
            return
        print(result.stdout.decode())
        return True

    def inject_rule(self,state, rule):
        if self.router is None:
            print(colored("No device selected", "red"))
            return
        command = f"echo '{rule}' | simple_switch_CLI --thrift-port {self.router.thrift_port}"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(colored("Error while injecting rule", "red"))
            return
        print(result.stdout.decode())
        return True

    def show_table(self, state, table):
        if self.router is None:
            print(colored("No device selected", "red"))
            return
        command = f"echo 'table_dump {table}' | simple_switch_CLI --thrift-port {self.router.thrift_port}"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(colored("Error while showing table", "red"))
            return
        print(result.stdout.decode())
        return True
    
    def run(self, state):
        running = True
        while running:
            if self.router is None:
                self.prompt = ">>> "
            else:
                self.prompt = f"{colored(self.router.nodeName,'magenta',attrs=['bold'])} >>> "
            print(self.prompt, end="")
            user_input = input()
            if user_input == "":
                continue
            user_input = user_input.strip().split(" ",1)
            if type(user_input) is not list:
                user_input = [user_input]
            if user_input[0] in self.commands["main"]:
                running = self.commands["main"][user_input[0]](state, user_input[1] if len(user_input) > 1 else None)
            elif user_input[0] in self.commands["device"]:
                running = self.commands["device"][user_input[0]](state, user_input[1] if len(user_input) > 1 else None)
            else:
                print(colored("Invalid command", "red"))
        print(colored("Exiting...", "green"))




    

