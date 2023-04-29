import csv

def write(dst_path:str, metadata:list, headers:list):
    with open(dst_path, 'w', newline='') as fmetadata:
        writer = csv.DictWriter(fmetadata, fieldnames=headers, delimiter=';')

        writer.writeheader()
        
        for meta in metadata:
            writer.writerow(meta)

def read(src_path:str, headers:list):
    data = []
    with open(src_path, 'r') as fmetadata:
        metadata = csv.DictReader(fmetadata, fieldnames=headers, delimiter=';')
        next(metadata, None)
        for meta in metadata:
            data.append(meta)
    return data

def is_not_update(src_path:str, latest_headers:list):
    headers = []

    with open(src_path, 'r') as fmetadata:
        metadata = csv.reader(fmetadata, delimiter=';')

        for meta in metadata:
            headers.append(meta)
            break

    for header in headers:
        if header not in latest_headers:
            return False

    return True