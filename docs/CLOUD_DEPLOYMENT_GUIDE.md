# Prompt2Mesh Cloud Deployment: Step-by-Step Guide

This guide explains the deployment process for Prompt2Mesh on AWS EKS, including Docker image management, Kubernetes configuration, and Anthropic API integration.

---

## 1. Prerequisites
- AWS account with EKS, ECR, IAM permissions
- Docker installed locally
- kubectl configured for your EKS cluster
- Anthropic API key (for backend)

---

## 2. Build Docker Images

### Backend
```powershell
cd C:\Prompt2Mesh
# Build backend image
docker build -t 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/backend:latest -f docker/dockerfile --target backend .
```

### Frontend
```powershell
cd C:\Prompt2Mesh
# Build frontend image
docker build -t 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/frontend:latest -f docker/dockerfile --target frontend .
```

### Blender MCP
```powershell
cd C:\Prompt2Mesh
# Build Blender MCP image
docker build -t 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/blender-mcp:latest -f docker/dockerfile .
```

---

## 3. Push Images to AWS ECR
```powershell
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 785186658816.dkr.ecr.us-east-1.amazonaws.com

# Push images
docker push 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/backend:latest
docker push 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/frontend:latest
docker push 785186658816.dkr.ecr.us-east-1.amazonaws.com/prompt2mesh/blender-mcp:latest
```

---

## 4. Update Kubernetes Deployments

### Restart Deployments to Use Latest Images
```powershell
kubectl rollout restart deployment/backend -n prompt2mesh
kubectl rollout restart deployment/frontend -n prompt2mesh
kubectl rollout restart deployment/blender-mcp -n prompt2mesh
```

---

## 5. Verify Pod Status
```powershell
kubectl get pods -n prompt2mesh
```
All pods should show `1/1 Running`.

---

## 6. Ingress & LoadBalancer
- Nginx Ingress controller manages external access.
- If Blender UI shows 404, logout/login to recreate Ingress with correct LoadBalancer IP.

---

## 7. Anthropic API Key
- By default, backend uses a system-wide Anthropic API key (stored as a Kubernetes secret or env variable).
- All users are billed to this key unless a user API key system is implemented.

---

## 8. Health Probes & Timeouts
- Liveness probe: 120s period, 40 failures (80min tolerance)
- Readiness probe: 60s period, 20 failures (20min tolerance)
- Backend `/chat` and `/refine-prompt` endpoints: 1-hour timeout
- Async job system for long-running operations

---

## 9. End-to-End Test
- Access frontend URL
- Login and connect to Blender
- Create a 3D object (e.g., tree) with comprehensive refinement
- Confirm screenshot and result

---

## 10. Troubleshooting
- If pods crash, check logs:
  ```powershell
  kubectl logs -n prompt2mesh deployment/backend --tail=200
  ```
- If frontend/Blender UI inaccessible, check Ingress and LoadBalancer IPs.

---

## 11. Notes
- All Anthropic API usage is billed to the system key unless user API key system is added.
- For cost control, consider usage limits or per-user API keys.

---

## 12. References
- [QUICKSTART.md](C:/Prompt2Mesh/docs/QUICKSTART.md)
- [K8S_DEPLOYMENT.md](C:/Prompt2Mesh/docs/K8S_DEPLOYMENT.md)
- [CONFIGURATION.md](C:/Prompt2Mesh/docs/CONFIGURATION.md)
