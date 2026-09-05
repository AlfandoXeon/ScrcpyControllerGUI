<#
.SYNOPSIS
    Creates a local Code Signing certificate for 'AlfandoXeon' and signs
    the compiled application executable and/or installer.

.DESCRIPTION
    Windows Defender SmartScreen and UAC display 'Unknown Publisher' unless
    an executable is signed with an Authenticode digital certificate.
    This script generates a Code Signing certificate, signs ScrcpyController.exe,
    and signs installer executables using Set-AuthenticodeSignature.
#>

param (
    [string]$PublisherName = "AlfandoXeon",
    [string]$TargetExe = "dist\ScrcpyController\ScrcpyController.exe",
    [string]$InstallerPattern = "installer\*.exe",
    [switch]$InstallToTrustedRoot = $false
)

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Code Signing Utility for $PublisherName" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# 1. Find or create Code Signing Certificate
$cert = Get-ChildItem -Path "Cert:\CurrentUser\My" -CodeSigningCert | Where-Object { $_.Subject -like "*$PublisherName*" } | Select-Object -First 1

if (-not $cert) {
    Write-Host "[INFO] No existing code signing certificate found for '$PublisherName'. Creating new..." -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=$PublisherName" `
        -KeySpec Signature `
        -KeyUsage DigitalSignature `
        -FriendlyName "$PublisherName Code Signing" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddYears(5)
    
    Write-Host "[OK] Certificate created (Thumbprint: $($cert.Thumbprint))" -ForegroundColor Green
} else {
    Write-Host "[OK] Found existing certificate for '$PublisherName' (Thumbprint: $($cert.Thumbprint))" -ForegroundColor Green
}

# Optional: Install to Trusted Root on this local machine so SmartScreen never blocks on this PC
if ($InstallToTrustedRoot) {
    Write-Host "[INFO] Installing to Trusted Root Certification Authorities (Local Machine)..." -ForegroundColor Yellow
    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store "Root", "CurrentUser"
    $rootStore.Open("ReadWrite")
    $rootStore.Add($cert)
    $rootStore.Close()
    Write-Host "[OK] Certificate added to Trusted Root store for current user." -ForegroundColor Green
}

# 2. Sign the Main Executable
if (Test-Path $TargetExe) {
    Write-Host "[INFO] Signing $TargetExe..." -ForegroundColor Yellow
    $status = Set-AuthenticodeSignature `
        -FilePath $TargetExe `
        -Certificate $cert `
        -TimestampServer "http://timestamp.digicert.com" `
        -HashAlgorithm SHA256
    
    Write-Host "[OK] $TargetExe signed. Status: $($status.Status)" -ForegroundColor Green
} else {
    Write-Host "[WARN] $TargetExe not found. Run build.bat first." -ForegroundColor Yellow
}

# 3. Sign any Inno Setup installer executables
$installers = Get-ChildItem -Path $InstallerPattern -ErrorAction SilentlyContinue
foreach ($inst in $installers) {
    Write-Host "[INFO] Signing installer: $($inst.FullName)..." -ForegroundColor Yellow
    $status = Set-AuthenticodeSignature `
        -FilePath $inst.FullName `
        -Certificate $cert `
        -TimestampServer "http://timestamp.digicert.com" `
        -HashAlgorithm SHA256
    Write-Host "[OK] $($inst.Name) signed. Status: $($status.Status)" -ForegroundColor Green
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Signing Complete!" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
