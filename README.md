# AAgentic AI-Driven Self-Healing CI/CD Platform

## Overvieww
This project demonstrates an AI-powered CI/CD pipeline that can detect failures, analyze them using RAG (Vector DB) + LLM, and automatically Propose fixes.

## Project Structure
- `sample-app/`: A Python Flask app with a built-in "failure mode" to test the AI.
- `ai-agent/`: The FastAPI service that acts as the "Healer". It uses OpenAI and ChromaDB.
- `terraform/disabled/`: Reference Terraform code for AWS EKS (not used locally).
- `k8s/`: Kubernetes manifests for local deployment.

## How to Run Locally

### Prerequisites
- Docker Desktop (active and running)
- PowerShell
- OpenAI API Key
- GitHub Token (Repo scope)

### 1. Configure Secrets
Copy the template and fill in your API keys:
```powershell
cp secrets_template.yaml secrets.yaml
# Open secrets.yaml and add your keys
```

### 2. Run Setup Script (One-Click Deploy)
We have provided a PowerShell script that handles building images, pushing them (if configured), and deploying to your local cluster.
```powershell
.\setup_local.ps1
```

### 3. Verification
The script will tell you how to access the services. Typically:
1. **Sample App**: `http://localhost:8080` (Run `kubectl port-forward svc/sample-app 8080:80`)
2. **AI Agent**: `http://localhost:8000/docs` (Run `kubectl port-forward svc/ai-agent 8000:80`)

### 4. Test the AI Healing
1. Port-forward the AI Agent (if not already done).
2. Send a Mock Healing Request:
   ```bash
   curl -X POST http://localhost:8000/heal \
     -H "Content-Type: application/json" \
     -d '{
       "repo": "your-user/self-healing-cicd",
       "run_id": "123456",
       "job": "test",
       "branch": "main"
     }'
   ```
3. Watch the logs:
   ```bash
   kubectl logs -f -l app=ai-agent
   ```
