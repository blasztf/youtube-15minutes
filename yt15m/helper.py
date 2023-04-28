def debug(enable):
    return lambda : enable

def log(dbg, text):
    if dbg():
        print (f">> {text}\n")