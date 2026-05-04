import os
import subprocess

REMOTE_CMDS = {
    "disk":        "df / | awk 'NR==2{t=$2/1048576; u=$3/1048576; f=$4/1048576; p=u/t*100; printf \"Disk: %.1f%% used (%.1f GB / %.1f GB  free: %.1f GB)\", p,u,t,f}'",
    "memory":      "free -k | awk 'NR==2{t=$2/1024; u=$3/1024; p=u*100/t; printf \"Memory: %.1f%% used (%d MB / %d MB)\", p,int(u),int(t)}'",
    "cpu":         "cat /proc/loadavg | awk '{printf \"Load avg: %s (1m)  %s (5m)  %s (15m)\", $1,$2,$3}'",
    "uptime":      "uptime -p",
    "processes":   "ps aux --sort=-%cpu | awk 'NR>1 && NR<=6{printf \"  [%s] %-20s CPU:%.1f%%  MEM:%.1f%%\\n\",$2,$11,$3,$4}'",
    "ports":       "printf 'Open ports: '; ss -tuln | awk 'NR>1{n=split($5,a,\":\");if(a[n]+0>0)print a[n]}' | sort -un | tr '\\n' ' '",
    "ip":          "ip -br addr",
    "routes":      "ip route",
    "network":     "ip -s link",
    "connections": "ss -tn state established 2>/dev/null | tail -n +2 | wc -l | xargs -I{} echo 'Established connections: {}'",
    "health":      "d=`df / | awk 'NR==2{printf \"%.1f\", $3*100/$2}'`; m=`free -k | awk 'NR==2{printf \"%.1f\", $3*100/$2}'`; n=`nproc`; c=`awk -v n=$n '{printf \"%.1f\", $1/n*100}' /proc/loadavg`; u=`uptime -p`; printf 'Disk: %s%%\\nMemory: %s%%\\nCPU: %s%%\\nUptime: %s' $d $m $c \"$u\"",
}


def run_remote(node: dict, command: str, timeout: int = 10) -> str:
    host = node["host"]
    user = node.get("user", "ubuntu")
    key_path = os.path.expanduser(node.get("key_path", "~/.ssh/id_rsa"))
    ssh_cmd = [
        "ssh", "-i", key_path,
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=5",
        f"{user}@{host}",
        command,
    ]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return f"Error: {result.stderr.strip() or 'command failed'}"
        return result.stdout.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Connection timed out after {timeout}s"
    except Exception as e:
        return f"SSH error: {e}"


def get_remote_metrics(node: dict) -> dict:
    """Single SSH call returning disk%, memory%, estimated cpu% for a remote node."""
    cmd = (
        "d=$(df / | awk 'NR==2{printf \"%.1f\", $3*100/$2}'); "
        "m=$(free -k | awk 'NR==2{printf \"%.1f\", $3*100/$2}'); "
        "c=$(awk '{print $1}' /proc/loadavg); "
        "n=$(nproc); "
        "echo \"$d $m $c $n\""
    )
    out = run_remote(node, cmd)
    if out.startswith(("Error", "Connection", "SSH")):
        raise RuntimeError(out)
    parts = out.strip().split()
    if len(parts) < 4:
        raise RuntimeError(f"Unexpected output: {out!r}")
    load_avg = float(parts[2])
    nproc = max(int(parts[3]), 1)
    return {
        "disk":   float(parts[0]),
        "memory": float(parts[1]),
        "cpu":    min(round(load_avg / nproc * 100, 1), 100.0),
    }
