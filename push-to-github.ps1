# push-to-github.ps1
# Pushes the crm_app commits to GitHub. RUN THIS YOURSELF - Claude is blocked from pushing.
#
# It asks you for the repo URL and a Personal Access Token. Nothing is written to disk and
# the token is never stored in git config: it is used only for the single push command below.
#
#   Usage:  powershell -ExecutionPolicy Bypass -File "D:\Claude Cowork\Frappe App\crm_app\push-to-github.ps1"
#
# ASCII only on purpose: Windows PowerShell 5.1 reads .ps1 as the system codepage, so any
# fancy dash or box character corrupts the parse. Keep this file plain ASCII.

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host ""
Write-Host "=== Push crm_app to GitHub ===" -ForegroundColor Cyan
Write-Host ""

# Show what will be pushed.
Write-Host "Commits on your local 'main':" -ForegroundColor Yellow
git log --oneline -6
Write-Host ""

# 1. Repo URL. Default is the name noted in memory; press Enter to accept or type another.
$default = "https://github.com/amitmetaliks/crm_app.git"
$repo = Read-Host "GitHub repo URL [$default]"
if ([string]::IsNullOrWhiteSpace($repo)) { $repo = $default }

# Strip protocol, any embedded credentials, and a trailing slash to get a clean host/path.
$bare = ($repo -replace '^https?://', '' -replace '^.*@', '').TrimEnd('/')

# 2. Token - entered by you, held only in memory. GitHub's own format is
#    https://x-access-token:<TOKEN>@github.com/... so no separate username is needed.
$secure = Read-Host "GitHub Personal Access Token (starts with ghp_, input hidden)" -AsSecureString
$token = ([System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))).Trim()

# Catch the common paste mistakes before git chokes on a mangled URL.
if ([string]::IsNullOrWhiteSpace($token)) {
    Write-Host "No token entered - aborting." -ForegroundColor Red
    exit 1
}
if (($token -match '^https?://') -or ($token -match '\s')) {
    Write-Host "That does not look like a token - it looks like a URL or has spaces." -ForegroundColor Red
    Write-Host "You may have pasted the repo URL into the token prompt. Re-run and paste the ghp_... token." -ForegroundColor Red
    exit 1
}

# 3. Keep a clean (token-free) 'origin' for future fetches; push via a one-shot tokenized URL.
$plainRemote = "https://$bare"
if (git remote | Select-String -SimpleMatch "origin") {
    git remote set-url origin $plainRemote
} else {
    git remote add origin $plainRemote
}

$authUrl = "https://x-access-token:${token}@${bare}"
Write-Host ""
Write-Host "Pushing 'main' to $plainRemote ..." -ForegroundColor Cyan
git push $authUrl main

# 4. Scrub the token from memory.
$token = $null
$authUrl = $null
[System.GC]::Collect()

Write-Host ""
Write-Host "Done. 'origin' is set to $plainRemote (no token stored)." -ForegroundColor Green
Write-Host "IMPORTANT: revoke any OLD token pasted in an earlier session:" -ForegroundColor Red
Write-Host "  https://github.com/settings/tokens" -ForegroundColor Red
