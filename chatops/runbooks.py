import subprocess
from typing import Dict, Optional, List

RUNBOOKS: Dict[str, dict] = {
    "clear_tmp": {
        "description": "Delete files in /tmp older than 1 day",
        "command": ["find", "/tmp", "-maxdepth", "1", "-type", "f", "-mtime", "+1", "-print", "-delete"],
        "preview": "find /tmp -maxdepth 1 -type f -mtime +1 -print -delete",
    },
    "disk_breakdown": {
        "description": "Show disk usage by mounted filesystem",
        "command": ["df", "-h", "--output=source,size,used,avail,pcent,target"],
        "preview": "df -h --output=source,size,used,avail,pcent,target",
    },
    "large_logs": {
        "description": "List log files over 50MB in /var/log",
        "command": ["find", "/var/log", "-type", "f", "-size", "+50M", "-ls"],
        "preview": "find /var/log -type f -size +50M -ls",
    },
    "listening_services": {
        "description": "List all listening services with PIDs",
        "command": ["ss", "-tlnp"],
        "preview": "ss -tlnp",
    },
    "flush_cache": {
        "description": "Flush OS page/dentry/inode cache to free memory",
        "command": "sync && echo 3 > /proc/sys/vm/drop_caches && echo 'Cache flushed.' && free -h",
        "preview": "sync && echo 3 > /proc/sys/vm/drop_caches",
        "shell": True,
    },
    "rotate_logs": {
        "description": "Force log rotation for all configured log files",
        "command": "logrotate -f /etc/logrotate.conf 2>&1 && echo 'Log rotation complete.'",
        "preview": "logrotate -f /etc/logrotate.conf",
        "shell": True,
    },
    "rotate_secret": {
        "description": "Generate a new random application secret (64-char hex)",
        "command": "python3 -c \"import secrets; s=secrets.token_hex(32); print(f'New secret generated:\\n  {s}\\n\\nStore this securely and update your application config.')\"",
        "preview": "python3 -c \"import secrets; print(secrets.token_hex(32))\"",
        "shell": True,
    },
}

_pending: Optional[str] = None


def list_runbooks() -> List[dict]:
    return [
        {"name": k, "description": v["description"], "preview": v["preview"]}
        for k, v in RUNBOOKS.items()
    ]


def request_runbook(name: str) -> dict:
    global _pending
    rb = RUNBOOKS.get(name)
    if not rb:
        available = ", ".join(RUNBOOKS.keys())
        return {
            "status": "error",
            "message": f"Unknown runbook '{name}'. Available: {available}",
        }
    _pending = name
    return {
        "status": "confirm",
        "message": (
            f"Runbook: {rb['description']}\n"
            f"Command: {rb['preview']}\n\n"
            f"Reply 'confirm {name}' to execute, or 'cancel' to abort."
        ),
    }


def confirm_runbook(name: str) -> dict:
    global _pending
    if _pending != name:
        return {
            "status": "error",
            "message": f"No pending confirmation for '{name}'. Use 'run {name}' first.",
        }
    rb = RUNBOOKS.get(name)
    if not rb:
        return {"status": "error", "message": f"Unknown runbook '{name}'."}
    _pending = None
    try:
        result = subprocess.run(
            rb["command"], shell=rb.get("shell", False),
            capture_output=True, text=True, timeout=30
        )
        stdout = result.stdout.strip()
        stderr = "\n".join(l for l in result.stderr.splitlines() if "Permission denied" not in l).strip()
        output = stdout or stderr or "Done. Nothing to delete."
        return {"status": "ok", "output": output[:1500]}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Runbook timed out after 30 seconds."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def cancel_runbook() -> dict:
    global _pending
    _pending = None
    return {"status": "ok", "message": "Cancelled."}
