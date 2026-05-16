$adapters = Get-ChildItem "HKLM:\SYSTEM\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002BE10318}" -ErrorAction SilentlyContinue
foreach ($a in $adapters) {
    $conn = $a.PSPath + "\Connection"
    if (Test-Path $conn) {
        $props = Get-ItemProperty $conn -ErrorAction SilentlyContinue
        $nameVal = $props.Name
        $nameType = if ($nameVal -ne $null) { $nameVal.GetType().Name } else { "NULL" }
        Write-Host "$($a.PSChildName) -> Name='$nameVal' Type=$nameType"
    }
}
