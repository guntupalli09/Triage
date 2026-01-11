# PowerShell script to create GitHub repository and push code
# Run this script after creating the repository on GitHub

$repoName = "Triage"
$repoDescription = "Your AI Contract Risk evaluator"
$githubUsername = Read-Host "Enter your GitHub username"

Write-Host "`n=== Setting up GitHub repository ===" -ForegroundColor Cyan
Write-Host "Repository name: $repoName" -ForegroundColor Yellow
Write-Host "Description: $repoDescription" -ForegroundColor Yellow
Write-Host "`nIMPORTANT: First create the repository on GitHub:" -ForegroundColor Red
Write-Host "1. Go to https://github.com/new" -ForegroundColor White
Write-Host "2. Repository name: $repoName" -ForegroundColor White
Write-Host "3. Description: $repoDescription" -ForegroundColor White
Write-Host "4. Choose Public or Private" -ForegroundColor White
Write-Host "5. DO NOT initialize with README, .gitignore, or license" -ForegroundColor White
Write-Host "6. Click 'Create repository'" -ForegroundColor White

$continue = Read-Host "`nHave you created the repository on GitHub? (y/n)"
if ($continue -ne "y") {
    Write-Host "Please create the repository first, then run this script again." -ForegroundColor Red
    exit
}

# Add remote and push
Write-Host "`n=== Adding remote and pushing code ===" -ForegroundColor Cyan

git remote add origin "https://github.com/$githubUsername/$repoName.git"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Remote might already exist. Removing and re-adding..." -ForegroundColor Yellow
    git remote remove origin
    git remote add origin "https://github.com/$githubUsername/$repoName.git"
}

Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== Success! ===" -ForegroundColor Green
    Write-Host "Repository URL: https://github.com/$githubUsername/$repoName" -ForegroundColor Cyan
} else {
    Write-Host "`n=== Error occurred ===" -ForegroundColor Red
    Write-Host "Please check your GitHub credentials and try again." -ForegroundColor Yellow
    Write-Host "You may need to authenticate with:" -ForegroundColor Yellow
    Write-Host "  git config --global user.name 'Your Name'" -ForegroundColor White
    Write-Host "  git config --global user.email 'your.email@example.com'" -ForegroundColor White
}
