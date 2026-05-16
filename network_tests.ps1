# network_tests.ps1 - ChatOps network test suite for IOS-XE, IOS-XR, NX-OS
# Usage: .\network_tests.ps1          (interactive menu)
#        .\network_tests.ps1 xe       (IOS-XE  Cat8kv)
#        .\network_tests.ps1 xr       (IOS-XR  XRv9K)
#        .\network_tests.ps1 nx       (NX-OS   Nexus9K)

param([string]$os = "")

$base_url = "http://localhost:8001/chatops/network/devices"
$headers  = @{ Authorization = "Bearer $global:token" }

if (-not $os) {
    Write-Host ""
    Write-Host "  Select device OS:" -ForegroundColor Cyan
    Write-Host "  [1] IOS-XE  -- Cat8kv       (10.10.20.48)" -ForegroundColor Green
    Write-Host "  [2] IOS-XR  -- IOS-XRv 9K   (10.10.20.35)" -ForegroundColor Blue
    Write-Host "  [3] NX-OS   -- Nexus 9K      (10.10.20.40)" -ForegroundColor Magenta
    Write-Host "  [4] Linux   -- DevBox        (10.10.20.50)" -ForegroundColor Cyan
    Write-Host ""
    $choice = Read-Host "  Enter 1, 2, 3 or 4"
    $os = @{"1"="xe";"2"="xr";"3"="nx";"4"="db"}[$choice]
    if (-not $os) { Write-Host "Invalid choice. Exiting." -ForegroundColor Red; exit }
}

switch ($os.ToLower()) {
    "xe"    { $device = "cat8kv";  $os_label = "IOS-XE";  $color = "Green"   }
    "xr"    { $device = "ios-xrv"; $os_label = "IOS-XR";  $color = "Blue"    }
    "nx"    { $device = "nexus9k"; $os_label = "NX-OS";   $color = "Magenta" }
    "db"    { $device = "devbox";  $os_label = "Linux";   $color = "Cyan"    }
    default { Write-Host "Unknown OS '$os'. Use xe, xr, nx or db." -ForegroundColor Red; exit }
}

$base = "$base_url/$device"

function Section($title) {
    Write-Host ""
    Write-Host ("=" * 65) -ForegroundColor $color
    Write-Host "  [$os_label] $title" -ForegroundColor Yellow
    Write-Host ("=" * 65) -ForegroundColor $color
}

function Show-Error($msg) {
    Write-Host "  ERROR: $msg" -ForegroundColor Red
}

Section "DEVICE INFO (show version)"
try {
    $r = Invoke-RestMethod -Method GET -Uri "$base/info" -Headers $headers
    if ($r.status -eq "ok") {
        Write-Host "  Hostname : $($r.hostname)"
        Write-Host "  Model    : $($r.model)"
        Write-Host "  Version  : $($r.version)"
        Write-Host "  Uptime   : $($r.uptime)"
        if ($r.serial -and $r.serial -ne "unknown") { Write-Host "  Serial   : $($r.serial)" }
    } else { Show-Error $r.error }
} catch { Show-Error $_.Exception.Message }

if ($os -eq "xr") { Start-Sleep -Seconds 3 }
Section "INTERFACES (show ip interface brief)"
try {
    $r = Invoke-RestMethod -Method GET -Uri "$base/interfaces" -Headers $headers
    if ($r.status -eq "ok") {
        Write-Host ("  {0,-30} {1,-18} {2,-16} {3,-10} {4,10} {5,10}" -f "Interface","IP Address","Status","Protocol","In bps","Out bps")
        Write-Host ("  " + "-" * 95)
        foreach ($i in $r.interfaces) {
            $stColor = if ($i.status -eq "up") { "Green" } else { "DarkGray" }
            Write-Host ("  {0,-30} {1,-18} {2,-16} {3,-10} {4,10} {5,10}" -f $i.interface, $i.ip, $i.status, $i.protocol, $i.in_rate, $i.out_rate) -ForegroundColor $stColor
        }
    } else { Show-Error $r.error }
} catch { Show-Error $_.Exception.Message }

if ($os -eq "xr") { Start-Sleep -Seconds 3 }
Section "ROUTING TABLE (show ip route)"
try {
    $r = Invoke-RestMethod -Method GET -Uri "$base/routes" -Headers $headers
    if ($r.status -eq "ok") {
        if ($r.raw) { Write-Host $r.raw }
        elseif ($r.routes.Count -gt 0) {
            Write-Host ("  {0,-6} {1,-22} {2,-8} {3,-8} {4}" -f "Code","Network","Dist","Metric","Next Hop")
            Write-Host ("  " + "-" * 60)
            foreach ($rt in $r.routes) {
                Write-Host ("  {0,-6} {1,-22} {2,-8} {3,-8} {4}" -f $rt.code, $rt.network, $rt.distance, $rt.metric, $rt.next_hop)
            }
        } else { Write-Host "  No routes parsed." -ForegroundColor DarkGray }
    } else { Show-Error $r.error }
} catch { Show-Error $_.Exception.Message }

if ($os -eq "xr") { Start-Sleep -Seconds 3 }
Section "BGP NEIGHBORS (show bgp summary)"
if ($os -eq "db") {
    Write-Host "  N/A -- Linux host, BGP not applicable." -ForegroundColor DarkGray
} else {
try {
    $r = Invoke-RestMethod -Method GET -Uri "$base/bgp" -Headers $headers
    if ($r.status -eq "ok") {
        if ($r.neighbors.Count -gt 0) {
            Write-Host ("  {0,-18} {1,-8} {2,-16} {3,-12} {4}" -f "Neighbor","AS","State","Prefixes","Up/Down")
            Write-Host ("  " + "-" * 65)
            foreach ($n in $r.neighbors) {
                $nColor = if ($n.state -eq "Established") { "Green" } else { "Red" }
                Write-Host ("  {0,-18} {1,-8} {2,-16} {3,-12} {4}" -f $n.neighbor, $n.as, $n.state, $n.prefixes, $n.updown) -ForegroundColor $nColor
            }
        } else {
            Write-Host "  No BGP neighbors (BGP not configured on this device)." -ForegroundColor DarkGray
        }
    } else { Show-Error $r.error }
} catch { Show-Error $_.Exception.Message }
}

if ($os -eq "xr") { Start-Sleep -Seconds 3 }
$cpuTitle = if ($os -eq "db") { "CPU & MEMORY (top / free -m)" } else { "CPU & MEMORY (show processes)" }
$memUnit  = if ($os -eq "db") { "" } else { " bytes" }
Section $cpuTitle
try {
    $r = Invoke-RestMethod -Method GET -Uri "$base/cpu" -Headers $headers
    if ($r.status -eq "ok") {
        Write-Host "  CPU (5sec) : $($r.cpu_5sec)%"
        Write-Host "  Mem Used   : $($r.mem_used_bytes)$memUnit"
        Write-Host "  Mem Free   : $($r.mem_free_bytes)$memUnit"
        Write-Host ""
        Write-Host "  Raw output:" -ForegroundColor DarkGray
        Write-Host "  $($r.cpu_raw)" -ForegroundColor DarkGray
    } else { Show-Error $r.error }
} catch { Show-Error $_.Exception.Message }

if ($os -eq "xr") { Start-Sleep -Seconds 3 }
Section "ARP TABLE (show arp)"
try {
    $r = Invoke-RestMethod -Method GET -Uri "$base/arp" -Headers $headers
    if ($r.status -eq "ok") {
        if ($r.entries.Count -gt 0) {
            Write-Host ("  {0,-18} {1,-22} {2}" -f "IP Address","MAC Address","Interface")
            Write-Host ("  " + "-" * 55)
            foreach ($e in $r.entries) {
                Write-Host ("  {0,-18} {1,-22} {2}" -f $e.ip, $e.mac, $e.interface)
            }
        } else {
            Write-Host "  No ARP entries." -ForegroundColor DarkGray
        }
    } else { Show-Error $r.error }
} catch { Show-Error $_.Exception.Message }

Write-Host ""
Write-Host ("=" * 65) -ForegroundColor $color
Write-Host "  [$os_label / $device] ALL TESTS COMPLETE" -ForegroundColor Green
Write-Host ("=" * 65) -ForegroundColor $color
Write-Host ""
