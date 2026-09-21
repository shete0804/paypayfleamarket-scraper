#!/usr/bin/env pwsh
# GitHub credential for automated push
# Usage: GIT_ASKPASS=./askpass.ps1 git push ...

# Check if stdin contains a prompt
$prompt = $args[0]

# For username prompt
if ($prompt -like "*Username*") {
    Write-Output "shete0804"
}
# For password prompt - expects token in environment variable
elseif ($prompt -like "*Password*") {
    # Try to read token from environment
    if ($env:GITHUB_TOKEN) {
        Write-Output $env:GITHUB_TOKEN
    } else {
        # Fallback: prompt user in terminal
        Write-Host "Please provide your GitHub Personal Access Token:"
        Read-Host -AsSecureString | ConvertFrom-SecureString -AsPlainText
    }
} else {
    Write-Output ""
}
