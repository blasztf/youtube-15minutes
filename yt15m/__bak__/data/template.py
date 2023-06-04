def read(template_path:str) -> str:
    contents = ""   
    with open(template_path) as ftemplate:
        contents = ftemplate.read()

    return contents