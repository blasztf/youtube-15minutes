import time
import sys
from termcolor import colored

def __debug(enable=True):
    return lambda x : enable

def log(text, proc=None):
    timestamp = time.localtime()
    timestamp = time.strftime("%d/%m/%Y, %H:%M:%S", timestamp)

    if __debug('.')('.'):
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
        