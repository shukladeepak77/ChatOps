import json
import os

_NODES_FILE = os.path.join(os.path.dirname(__file__), "..", "chatops_nodes.json")

_DEFAULTS = {
    "localhost": {
        "host": "127.0.0.1",
        "user": os.environ.get("USER", "ubuntu"),
        "key_path": "~/.ssh/id_rsa",
    }
}


def _load() -> dict:
    if os.path.exists(_NODES_FILE):
        with open(_NODES_FILE) as f:
            return json.load(f)
    return dict(_DEFAULTS)


def _save(nodes: dict):
    with open(_NODES_FILE, "w") as f:
        json.dump(nodes, f, indent=2)


def list_nodes() -> dict:
    return _load()


def get_node(name: str):
    return _load().get(name)


def add_node(name: str, host: str, user: str = "ubuntu", key_path: str = "~/.ssh/id_rsa") -> dict:
    nodes = _load()
    nodes[name] = {"host": host, "user": user, "key_path": key_path}
    _save(nodes)
    return nodes[name]


def remove_node(name: str) -> bool:
    nodes = _load()
    if name not in nodes:
        return False
    del nodes[name]
    _save(nodes)
    return True


def set_node_thresholds(name: str, thresholds: dict) -> bool:
    nodes = _load()
    if name not in nodes:
        return False
    nodes[name]["thresholds"] = thresholds
    _save(nodes)
    return True
