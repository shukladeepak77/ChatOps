$adapters = Get-ChildItem "HKLM:\SYSTEM\CurrentControlSet\Control\Network\{4D36E972-E325-11CE-BFC1-08002BE10318}" -ErrorAction SilentlyContinue
foreach ($a in $adapters) {
    $conn = $a.PSPath + "\Connection"
    if (Test-Path $conn) {
        $props = Get-ItemProperty $conn -ErrorAction SilentlyContinue
        if ($null -eq $props.Name) {
            Set-ItemProperty -Path $conn -Name "Name" -Value "Local Area Connection" -ErrorAction SilentlyContinue
            Write-Host "Fixed: $($a.PSChildName)"
        }
    }
}
Write-Host "Done."
