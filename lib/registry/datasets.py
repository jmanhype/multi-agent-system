import hashlib, json

def register_snapshot(path: str) -> dict:
    with open(path,'rb') as f: b=f.read()
    meta = {
        "path": path,
        "dataset_sha": "sha256:" + hashlib.sha256(b).hexdigest()
    }
    with open(path+".meta.json","w") as f: json.dump(meta, f)
    return meta