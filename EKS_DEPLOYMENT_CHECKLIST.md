# EKS Deployment Checklist

Use this checklist to track your deployment progress.

## Pre-Deployment

### AWS Infrastructure
- [ ] EKS cluster created and accessible
- [ ] kubectl configured to access cluster
- [ ] AWS Load Balancer Controller installed
- [ ] Cluster Autoscaler installed (optional but recommended)
- [ ] ECR repositories created:
  - [ ] prompt2mesh-backend
  - [ ] prompt2mesh-streamlit

### Domain & DNS
- [ ] Domain name registered
- [ ] DNS managed (Route53 or other)
- [ ] Wildcard DNS configured for per-user subdomains

### Secrets & Configuration
- [ ] Anthropic API key obtained
- [ ] LangChain/LangSmith API keys obtained (optional)
- [ ] JWT secret key generated
- [ ] PostgreSQL password chosen (secure)

## Docker Images

### Build Images
- [ ] Backend image built successfully
  ```bash
  docker build -t prompt2mesh-backend:latest -f docker/dockerfile --target backend .
  ```
- [ ] Images tested locally with docker-compose
  ```bash
  docker-compose -f docker/docker-compose.yml up
  ```

### Push to ECR
- [ ] AWS credentials configured
- [ ] Logged into ECR
  ```bash
  aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
  ```
- [ ] Backend image tagged and pushed
  ```bash
  docker tag prompt2mesh-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/prompt2mesh-backend:latest
  docker push <account>.dkr.ecr.<region>.amazonaws.com/prompt2mesh-backend:latest
  ```
- [ ] Streamlit image tagged and pushed
  ```bash
  docker tag prompt2mesh-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/prompt2mesh-streamlit:latest
  docker push <account>.dkr.ecr.<region>.amazonaws.com/prompt2mesh-streamlit:latest
  ```

## Configuration Updates

### Update Manifests
- [ ] Updated image URIs in `k8s/base/backend-deployment.yaml`
- [ ] Updated image URIs in `k8s/base/streamlit-deployment.yaml`
- [ ] Updated image URIs in `k8s/base/db-init-job.yaml`
- [ ] Updated image URIs in `k8s/per-user/user-instance-template.yaml`
- [ ] Updated domain in `k8s/base/ingress.yaml`
- [ ] Updated domain in `k8s/per-user/user-instance-template.yaml`

### Update Secrets
- [ ] Updated `k8s/base/secrets.yaml` with:
  - [ ] POSTGRES_PASSWORD
  - [ ] JWT_SECRET_KEY
  - [ ] ANTHROPIC_API_KEY
  - [ ] LANGCHAIN_API_KEY (optional)
  - [ ] LANGSMITH_API_KEY (optional)

### Update Configuration
- [ ] Reviewed `k8s/base/configmap.yaml`
- [ ] Updated timezone if needed
- [ ] Updated resource limits if needed

## Deployment

### Base Components
- [ ] Namespace created
  ```bash
  kubectl apply -f k8s/base/namespace.yaml
  ```
- [ ] Secrets applied
  ```bash
  kubectl apply -f k8s/base/secrets.yaml
  ```
- [ ] ConfigMap applied
  ```bash
  kubectl apply -f k8s/base/configmap.yaml
  ```
- [ ] PostgreSQL deployed
  ```bash
  kubectl apply -f k8s/base/postgres-pvc.yaml
  kubectl apply -f k8s/base/postgres-deployment.yaml
  ```
- [ ] PostgreSQL ready
  ```bash
  kubectl wait --for=condition=ready pod -l app=postgres -n prompt2mesh --timeout=300s
  ```
- [ ] Database initialized
  ```bash
  kubectl apply -f k8s/base/db-init-job.yaml
  kubectl wait --for=condition=complete job/db-init -n prompt2mesh --timeout=300s
  ```
- [ ] Backend deployed
  ```bash
  kubectl apply -f k8s/base/backend-deployment.yaml
  ```
- [ ] Streamlit deployed
  ```bash
  kubectl apply -f k8s/base/streamlit-deployment.yaml
  ```
- [ ] Blender deployed (optional)
  ```bash
  kubectl apply -f k8s/base/blender-deployment.yaml
  ```
- [ ] Ingress deployed
  ```bash
  kubectl apply -f k8s/base/ingress.yaml
  ```

## Verification

### Check Deployments
- [ ] All pods running
  ```bash
  kubectl get pods -n prompt2mesh
  ```
- [ ] Services created
  ```bash
  kubectl get svc -n prompt2mesh
  ```
- [ ] Ingress created with ALB
  ```bash
  kubectl get ingress -n prompt2mesh
  ```
- [ ] ALB DNS name obtained
  ```bash
  kubectl get ingress prompt2mesh-ingress -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
  ```

### Test Connectivity
- [ ] Backend health check works
  ```bash
  kubectl exec -it deployment/backend -n prompt2mesh -- curl http://localhost:8000/
  ```
- [ ] Streamlit health check works
  ```bash
  kubectl exec -it deployment/streamlit -n prompt2mesh -- curl http://localhost:8501/
  ```
- [ ] Database connection works
  ```bash
  kubectl exec -it deployment/backend -n prompt2mesh -- python3 -c "import psycopg2; psycopg2.connect('postgresql://postgres:postgres@postgres:5432/prompt2mesh_auth')"
  ```
- [ ] External access works (via ALB DNS or domain)

### Test User Instance
- [ ] Created test user instance
  ```bash
  python k8s/user_instance_manager.py create test-user
  ```
- [ ] User pods running
  ```bash
  kubectl get pods -n prompt2mesh -l user-id=test-user
  ```
- [ ] User service created
  ```bash
  kubectl get svc -n prompt2mesh -l user-id=test-user
  ```
- [ ] User ingress created
  ```bash
  kubectl get ingress -n prompt2mesh user-test-user-ingress
  ```
- [ ] User subdomain accessible
- [ ] Deleted test user instance
  ```bash
  python k8s/user_instance_manager.py delete test-user
  ```

## DNS Configuration

- [ ] Created DNS record for main domain → ALB
  ```
  prompt2mesh.example.com → <alb-dns-name>
  ```
- [ ] Created wildcard DNS record for user subdomains → ALB
  ```
  *.prompt2mesh.example.com → <alb-dns-name>
  ```
- [ ] DNS propagation verified
  ```bash
  nslookup prompt2mesh.example.com
  ```

## SSL/TLS (Optional but Recommended)

- [ ] Certificate requested in ACM
- [ ] Certificate validated
- [ ] Certificate ARN added to ingress annotations
- [ ] HTTPS redirect enabled in ingress
- [ ] HTTPS access verified

## Monitoring & Logging

- [ ] Prometheus installed (optional)
- [ ] Grafana installed (optional)
- [ ] CloudWatch Container Insights enabled
- [ ] Log aggregation configured
- [ ] Dashboards created
- [ ] Alerts configured

## Auto-Scaling

- [ ] HPA configured for backend
  ```bash
  kubectl autoscale deployment backend -n prompt2mesh --cpu-percent=70 --min=2 --max=10
  ```
- [ ] HPA configured for streamlit
  ```bash
  kubectl autoscale deployment streamlit -n prompt2mesh --cpu-percent=70 --min=2 --max=10
  ```
- [ ] Cluster Autoscaler configured
- [ ] Scaling tested under load

## CI/CD

- [ ] GitHub Actions secrets configured:
  - [ ] AWS_ROLE_ARN (for OIDC)
- [ ] Build workflow tested
- [ ] Deploy workflow tested
- [ ] Rollback procedure documented

## Security Hardening

- [ ] Network Policies created
- [ ] RBAC configured
- [ ] Pod Security Standards enabled
- [ ] Secrets moved to AWS Secrets Manager (recommended)
- [ ] External Secrets Operator installed (if using Secrets Manager)
- [ ] IAM roles for service accounts configured
- [ ] Security scans configured for images
- [ ] Vulnerability scanning enabled

## Backup & Disaster Recovery

- [ ] Database backup strategy defined
- [ ] Automated backups configured
- [ ] Backup restoration tested
- [ ] Disaster recovery plan documented
- [ ] RDS migration considered (for production)

## Documentation

- [ ] Operational runbook created
- [ ] Troubleshooting guide updated
- [ ] Team onboarding docs created
- [ ] Architecture diagram updated
- [ ] Cost analysis performed

## Production Readiness

- [ ] Load testing performed
- [ ] Performance benchmarks established
- [ ] Resource limits tuned
- [ ] Cost optimization reviewed
- [ ] SLAs defined
- [ ] On-call rotation established
- [ ] Incident response plan created

## Post-Deployment

- [ ] Monitored for 24-48 hours
- [ ] No critical errors in logs
- [ ] Performance acceptable
- [ ] User feedback collected
- [ ] Scaling tested
- [ ] Backup verified
- [ ] Documentation complete

## Future Improvements

- [ ] Implement automatic user instance cleanup
- [ ] Add resource quotas per user
- [ ] Implement rate limiting
- [ ] Add distributed tracing
- [ ] Optimize costs
- [ ] Multi-region deployment
- [ ] Custom Kubernetes operator
- [ ] GPU support for rendering

---

## Quick Commands Reference

### View all resources
```bash
kubectl get all -n prompt2mesh
```

### View logs
```bash
kubectl logs -f deployment/<name> -n prompt2mesh
```

### Restart deployment
```bash
kubectl rollout restart deployment/<name> -n prompt2mesh
```

### Scale deployment
```bash
kubectl scale deployment/<name> -n prompt2mesh --replicas=<count>
```

### Describe resource
```bash
kubectl describe <resource> <name> -n prompt2mesh
```

### Port forward for local testing
```bash
kubectl port-forward service/<name> <local-port>:<service-port> -n prompt2mesh
```

### Execute command in pod
```bash
kubectl exec -it deployment/<name> -n prompt2mesh -- <command>
```

### Delete all resources
```bash
kubectl delete namespace prompt2mesh
```
