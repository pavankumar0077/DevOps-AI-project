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
- Docker Desktop (or Minikube)
- Python 3.11+
- OpenAI API Key
- GitHub Token (Repo scope)

### 1. Build Docker Images
```bash
# Build Sample App
docker build -t sample-app:latest ./sample-app

# Build AI Agent
docker build -t ai-agent:latest ./ai-agent
```

### 2. Deploy to Kubernetes (Local)
```bash
# Apply Secrets (Edit this file first or create manually!)
# kubectl create secret generic ai-agent-secrets --from-literal=OPENAI_API_KEY=sk-...

# Apply Manifests
kubectl apply -f sample-app/k8s/
kubectl apply -f ai-agent/k8s/
```

### 3. Test the AI Healing
1. Port-forward the AI Agent:
   ```bash
   kubectl port-forward svc/ai-agent 8000:8000
   ```
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
3. Watch the logss:
   ```bash
   kubectl logs -f -l app=ai-agent
   ```
