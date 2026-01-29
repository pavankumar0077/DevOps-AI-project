# Self-Healing CI/CD Local Setup Script

$DOCKER_USERNAME = "pavan0077"
$VERSION = "latest"

Write-Host "Starting Local Setup..." -ForegroundColor Cyan

# Check for secrets.yaml
if (-not (Test-Path "secrets.yaml")) {
    Write-Host "WARNING: secrets.yaml not found!" -ForegroundColor Yellow
    Write-Host "Please copy secrets_template.yaml to secrets.yaml and fill in your values."
    Write-Host "cp secrets_template.yaml secrets.yaml"
    exit 1
}

# 1. Build and Push Images
Write-Host "`nBuilding and Pushing Docker Images..." -ForegroundColor Cyan

# Sample App
Write-Host "Building sample-app..."
docker build -t "$DOCKER_USERNAME/sample-app:$VERSION" ./sample-app
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed for sample-app"
    exit 1
}

Write-Host "Pushing sample-app..."
docker push "$DOCKER_USERNAME/sample-app:$VERSION"

# AI Agent
Write-Host "Building ai-agent..."
docker build -t "$DOCKER_USERNAME/ai-agent:$VERSION" ./ai-agent
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed for ai-agent"
    exit 1
}

Write-Host "Pushing ai-agent..."
docker push "$DOCKER_USERNAME/ai-agent:$VERSION"

# 2. Deploy to Kubernetes
Write-Host "`nDeploying to Kubernetes..." -ForegroundColor Cyan

# Apply Secrets
kubectl apply -f secrets.yaml

# Apply Manifests
kubectl apply -f ai-agent/k8s/deployment.yaml
kubectl apply -f sample-app/k8s/deployment.yaml

# 3. Wait for Pods
Write-Host "`nWaiting for pods to verify deployment..." -ForegroundColor Cyan
Start-Sleep -Seconds 5
kubectl get pods

Write-Host "`nSetup Complete!" -ForegroundColor Green
Write-Host "To access the services, run port-forwarding in separate terminals:"
Write-Host "kubectl port-forward svc/sample-app 8080:80"
Write-Host "kubectl port-forward svc/ai-agent 8000:80"
