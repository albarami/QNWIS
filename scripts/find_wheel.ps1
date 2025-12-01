$response = Invoke-WebRequest -Uri "https://api.github.com/repos/turboderp-org/exllamav2/releases/latest" -UseBasicParsing
$json = $response.Content | ConvertFrom-Json
Write-Host "Latest release: $($json.tag_name)"
Write-Host ""
Write-Host "Windows wheels:"
$json.assets | Where-Object { $_.name -match "win" } | ForEach-Object {
    Write-Host "  $($_.name)"
    Write-Host "    URL: $($_.browser_download_url)"
}

