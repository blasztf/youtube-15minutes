import time
import sys
from termcolor import colored

__verbose = False

# def __debug(enable=True):
#     return lambda x : enable
def printv():
    global __verbose
    print(__verbose)

def enable_log():
    global __verbose
    __verbose = True

def log(text, proc=None):
    global  __verbose

    timestamp = time.localtime()
    timestamp = time.strftime("%d/%m/%Y, %H:%M:%S", timestamp)

    if __verbose:
        ori_text = text
        text = f">> {timestamp} "
        if proc is not None:
            if proc:
                text += "[+]"
                text = colored(text, 'green')
            else:
                text += "[-]"
                text = colored(text, 'red')
        else:
            text += "|"
        print (f"{text} {ori_text}\n")

def out(*values):
    print(values, file=sys.stdout)
        
def err(*values):
    print(values, file=sys.stderr)

def use_hook(init=None):
    value = [ init ]
    def hooker(new_value):
        value[0] = new_value

    return ( value, hooker )

def rts(value):
    return '' if value is None or value == 'None' else value

def rtsg(value):
    value = None if value == '' or value == 'None' else value
    check_value = value.lower() if isinstance(value, str) else value
    value = False if check_value == 'false' else True if check_value == 'true' else value
    return value

class PerformError(Exception):
    def __init__(self, pmessage:'PerformResult') -> None:
        super().__init__(pmessage.error_message)
        self.message = pmessage.error_message
        self.result = pmessage

class PerformResult:
    def __init__(self, error_code:str='', error_message:str='') -> None:
        self.error_code = error_code
        self.error_message = error_message
        
        