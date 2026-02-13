<#
.SYNOPSIS
    Launch the Agentic Framework Colab deployment.

.DESCRIPTION
    1. Commits and pushes any local changes to GitHub
    2. Opens the Colab deployment notebook in your browser
    3. Prints instructions for running the deployment

.NOTES
    Requirements: Git must be configured with push access to the repo.
#>

param(
    [switch]$NoPush,
    [switch]$Help
)

$ErrorActionPreference = "Continue"

# Logging setup
$ScriptStartTime = Get-Date
$LogDir = Join-Path $PSScriptRoot "logs"
$LogFile = Join-Path $LogDir "launch_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$LatestLogFile = Join-Path $LogDir "launch_latest.log"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Logging functions
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
    $logEntry = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $logEntry
    Add-Content -Path $LatestLogFile -Value $logEntry
}

function Write-LogError {
    param(
        [string]$Message,
        [System.Management.Automation.ErrorRecord]$ErrorRecord = $null
    )
    Write-Log $Message "ERROR"
    if ($ErrorRecord) {
        Write-Log "Exception: $($ErrorRecord.Exception.Message)" "ERROR"
        Write-Log "Stack Trace: $($ErrorRecord.ScriptStackTrace)" "ERROR"
    }
}

# Colors
function Write-Header($msg) { 
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
    Write-Log "=== $msg ===" "INFO"
}

function Write-Ok($msg) { 
    Write-Host "  [OK] $msg" -ForegroundColor Green
    Write-Log "[OK] $msg" "INFO"
}

function Write-Warn($msg) { 
    Write-Host "  [!]  $msg" -ForegroundColor Yellow
    Write-Log "[WARN] $msg" "WARN"
}

function Write-Err($msg) { 
    Write-Host "  [X]  $msg" -ForegroundColor Red
    Write-Log "[ERROR] $msg" "ERROR"
}

function Write-Step($n, $msg) { 
    Write-Host "  $n. $msg" -ForegroundColor White
    Write-Log "Step $n: $msg" "INFO"
}

function Write-Debug($msg) {
    Write-Host "  [DEBUG] $msg" -ForegroundColor Gray
    Write-Log "[DEBUG] $msg" "DEBUG"
}

$ColabUrl = "https://colab.research.google.com/github/landonking-gif/ai_final/blob/main/deploy/colab_notebook.ipynb"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Initialize logging
Write-Log "========================================" "INFO"
Write-Log "Script Started: launch.ps1" "INFO"
Write-Log "Start Time: $ScriptStartTime" "INFO"
Write-Log "Log File: $LogFile" "INFO"
Write-Log "Parameters: NoPush=$NoPush, Help=$Help" "INFO"
Write-Log "Script Path: $($MyInvocation.MyCommand.Path)" "INFO"
Write-Log "Repo Root: $RepoRoot" "INFO"
Write-Log "Colab URL: $ColabUrl" "INFO"
Write-Log "PowerShell Version: $($PSVersionTable.PSVersion)" "INFO"
Write-Log "User: $env:USERNAME" "INFO"
Write-Log "Computer: $env:COMPUTERNAME" "INFO"
Write-Log "Current Directory: $(Get-Location)" "INFO"
Write-Log "========================================" "INFO"

if ($Help) {
    Write-Host ""
    Write-Host "  Agentic Framework - Colab Deployment Launcher"
    Write-Host "  ================================================"
    Write-Host ""
    Write-Host "  Usage:"
    Write-Host "    .\deploy\launch.ps1           # Push changes and open Colab"
    Write-Host "    .\deploy\launch.ps1 -NoPush   # Open Colab without pushing"
    Write-Host "    .\deploy\launch.ps1 -Help     # Show this help"
    Write-Host ""
    Write-Host "  What it does:"
    Write-Host "    1. Stages and commits any uncommitted changes"
    Write-Host "    2. Pushes to GitHub (main branch)"
    Write-Host "    3. Opens the Colab notebook in your default browser"
    Write-Host "    4. You select GPU runtime and click Run All"
    Write-Host ""
    Write-Log "Help displayed - exiting" "INFO"
    exit 0
}

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "  Agentic Framework - Colab Deployment Launcher" -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan

# Step 1: Push to GitHub
if (-not $NoPush) {
    Write-Header "PUSHING TO GITHUB"
    Write-Log "Starting Git operations" "INFO"
    
    try {
        Write-Debug "Changing to repo root: $RepoRoot"
        Push-Location $RepoRoot
        Write-Log "Changed directory to: $RepoRoot" "INFO"
        
        # Check Git is available
        $gitVersion = git --version 2>&1
        Write-Debug "Git version: $gitVersion"
        Write-Log "Git version: $gitVersion" "INFO"
        
        # Check current branch
        $currentBranch = git branch --show-current 2>&1
        Write-Debug "Current branch: $currentBranch"
        Write-Log "Current branch: $currentBranch" "INFO"
        
        # Check remote
        $remoteUrl = git remote get-url origin 2>&1
        Write-Debug "Remote URL: $remoteUrl"
        Write-Log "Remote URL: $remoteUrl" "INFO"
        
        # Check for changes
        Write-Debug "Checking git status..."
        $statusStartTime = Get-Date
        $status = git status --porcelain 2>&1
        $statusDuration = (Get-Date) - $statusStartTime
        Write-Log "Git status check completed in $($statusDuration.TotalMilliseconds)ms" "INFO"
        
        if ($status) {
            Write-Ok "Found uncommitted changes - staging and committing..."
            Write-Log "Uncommitted changes detected:" "INFO"
            Write-Log "$status" "INFO"
            
            Write-Debug "Running git add -A..."
            $addStartTime = Get-Date
            $addResult = git add -A 2>&1
            $addDuration = (Get-Date) - $addStartTime
            Write-Log "Git add completed in $($addDuration.TotalMilliseconds)ms" "INFO"
            if ($addResult) {
                Write-Log "Git add output: $addResult" "INFO"
            }
            
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $commitMessage = "deploy: auto-commit before Colab deployment ($timestamp)"
            Write-Debug "Committing with message: $commitMessage"
            $commitStartTime = Get-Date
            $commitResult = git commit -m $commitMessage 2>&1
            $commitDuration = (Get-Date) - $commitStartTime
            Write-Log "Git commit completed in $($commitDuration.TotalMilliseconds)ms" "INFO"
            Write-Log "Commit output: $commitResult" "INFO"
            Write-Ok "Committed"
        } else {
            Write-Ok "No uncommitted changes"
            Write-Log "Working directory is clean" "INFO"
        }
        
        # Get commit info
        $lastCommit = git log -1 --oneline 2>&1
        Write-Debug "Last commit: $lastCommit"
        Write-Log "Last commit: $lastCommit" "INFO"
        
        Write-Ok "Pushing to origin/main..."
        Write-Debug "Starting git push..."
        $pushStartTime = Get-Date
        $pushResult = git push origin main 2>&1
        $pushDuration = (Get-Date) - $pushStartTime
        $pushExitCode = $LASTEXITCODE
        
        Write-Log "Git push completed in $($pushDuration.TotalSeconds) seconds" "INFO"
        Write-Log "Push exit code: $pushExitCode" "INFO"
        Write-Log "Push output: $pushResult" "INFO"
        
        if ($pushExitCode -eq 0) {
            Write-Ok "Push successful"
            Write-Log "Successfully pushed to origin/main" "INFO"
        } else {
            Write-Warn "Push may have failed: $pushResult"
            Write-Warn "Continuing anyway - Colab will use whatever is on GitHub"
            Write-LogError "Git push failed with exit code: $pushExitCode" 
            Write-Log "Push error output: $pushResult" "ERROR"
        }
        
        Write-Debug "Returning to original directory"
        Pop-Location
        Write-Log "Returned to original directory" "INFO"
        
    } catch {
        Write-Err "Error during Git operations: $($_.Exception.Message)"
        Write-LogError "Git operations failed" $_
        Pop-Location
    }
} else {
    Write-Warn "Skipping git push (-NoPush flag)"
    Write-Log "Git push skipped due to -NoPush parameter" "INFO"
}

# Step 2: Open Colab
Write-Header "OPENING COLAB"
Write-Log "Attempting to open Colab notebook" "INFO"
Write-Ok "URL: $ColabUrl"
Write-Log "Target URL: $ColabUrl" "INFO"

try {
    Write-Debug "Launching browser with Start-Process..."
    $processStartTime = Get-Date
    Start-Process $ColabUrl
    $processDuration = (Get-Date) - $processStartTime
    Write-Log "Browser process started in $($processDuration.TotalMilliseconds)ms" "INFO"
    Write-Ok "Browser opened"
    Write-Log "Successfully launched browser with Colab URL" "INFO"
} catch {
    Write-Err "Could not open browser automatically"
    Write-LogError "Failed to open browser" $_
    Write-Host "  Open this URL manually:" -ForegroundColor White
    Write-Host "  $ColabUrl" -ForegroundColor Yellow
    Write-Log "User instructed to open URL manually" "WARN"
}

# Step 3: Instructions
Write-Header "NEXT STEPS (in Google Colab)"
Write-Step "1" "Select GPU runtime: Runtime -> Change runtime type -> T4 GPU"
Write-Step "2" "Run all cells: Runtime -> Run all (or Ctrl+F9)"
Write-Step "3" "Wait ~5 minutes for full deployment"
Write-Step "4" "Your public API and Dashboard URLs will be printed at the end"
Write-Host ""
Write-Step "" "To check status later, run Cell 2 (Diagnostics)"
Write-Step "" "To restart a service, run Cell 3 (Recovery)"
Write-Host ""
Write-Host "  ================================================" -ForegroundColor Green
Write-Host "  Deployment will be fully automatic after Run All" -ForegroundColor Green
Write-Host "  ================================================" -ForegroundColor Green
Write-Host ""

# Final logging
$ScriptEndTime = Get-Date
$ScriptDuration = $ScriptEndTime - $ScriptStartTime
Write-Log "========================================" "INFO"
Write-Log "Script Completed Successfully" "INFO"
Write-Log "End Time: $ScriptEndTime" "INFO"
Write-Log "Total Duration: $($ScriptDuration.TotalSeconds) seconds" "INFO"
Write-Log "========================================" "INFO"

Write-Host ""
Write-Host "  [LOG] Full execution log saved to:" -ForegroundColor Cyan
Write-Host "        $LogFile" -ForegroundColor Gray
Write-Host "  [LOG] Latest log also at:" -ForegroundColor Cyan
Write-Host "        $LatestLogFile" -ForegroundColor Gray
Write-Host ""
