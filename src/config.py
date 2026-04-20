import json5 as json, os
from pathlib import Path
MAIN_KEY = "config.json"
CATEGORIES_KEY = ".configs/categories.json"

configs = {}

def init():
    pass

def json_loader(filename, default=""):
    
    path = Path(filename)
    path.touch()

    with path.open("r+") as file:
        
        content = file.read()
        if not content:
            content = default
            file.seek(0)
            file.write(content)
            file.truncate()
            

    return json.loads(content)

def load_config(key, loader=json_loader, arg = None, default=""):
    c = None
    if arg is not None:
        c = loader(arg, default=default)
    else:
        c = loader(default=default)
    configs[key] = c
    return c

def load_main():
    return load_config(MAIN_KEY, arg=MAIN_KEY, default="{}")

def load_categories():
    return load_config(CATEGORIES_KEY, arg=CATEGORIES_KEY, default="[]")
    
def saveToFile(filename, content):
    with open(filename, "w") as file:
        json.dump(content, file, indent=4, quote_keys=True, trailing_commas=False)

def get(key:str):
    return configs.get(key)

def get_main():
    return get(MAIN_KEY)

def get_categories():
    return get(CATEGORIES_KEY)

def get_all():
    return configs

load_main()
load_categories()