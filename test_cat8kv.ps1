$result = Invoke-RestMethod -Method GET -Uri "http://localhost:8001/chatops/network/devices/cat8kv/info" -Headers @{ Authorization = "Bearer $global:token" }
Write-Host ($result | ConvertTo-Json)
