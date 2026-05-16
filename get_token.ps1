try {
    $response = Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/auth/login" -ContentType "application/json" -Body '{"username":"admin","password":"admin"}'
    Write-Host "Full response:"
    $response | ConvertTo-Json
    $global:token = $response.token
    Write-Host "Token set: $($global:token.Substring(0,20))..."
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host "Body: $($_.ErrorDetails.Message)"
}
