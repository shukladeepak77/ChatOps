$body = '{"name":"cat8kv","host":"10.10.20.48","port":22,"username":"developer","password":"C1sco12345","device_type":"cisco_xe"}'
$result = Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/network/devices" -ContentType "application/json" -Headers @{ Authorization = "Bearer $global:token" } -Body $body
Write-Host ($result | ConvertTo-Json)
