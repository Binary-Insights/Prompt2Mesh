# Next Steps for EKS Deployment

## Current Status ✅

- ✅ Docker setup reviewed and working
- ✅ Kubernetes manifests created
- ✅ AWS configuration added to `.env` file
- ✅ Deployment scripts created
- ✅ CI/CD workflows configured

## What to Do Next

### Step 1: Build and Push Docker Images to ECR

I've created an automated setup script for you. Run this command:

```powershell
.\scripts\setup-eks.ps1
```

**What this script does:**
1. Loads AWS configuration from your `.env` file
2. Logs into Amazon ECR
3. Creates ECR repositories (prompt2mesh-backend, prompt2mesh-streamlit)
4. Builds Docker images
5. Tags and pushes images to ECR
6. Updates Kubernetes manifests with correct image URIs

**Manual alternative (if you prefer):**

```powershell
# Load AWS config from .env
$AWS_ACCOUNT_ID = "9201-2042-4620"
$AWS_REGION = "us-east-1"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Create ECR repositories
aws ecr create-repository --repository-name prompt2mesh-backend --region $AWS_REGION
aws ecr create-repository --repository-name prompt2mesh-streamlit --region $AWS_REGION

# Build image
docker build -t prompt2mesh-backend:latest -f docker/dockerfile --target backend .

# Tag and push to ECR
docker tag prompt2mesh-backend:latest "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-backend:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-backend:latest"

docker tag prompt2mesh-backend:latest "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-streamlit:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-streamlit:latest"
```

---

### Step 2: Update Kubernetes Secrets

Run this script to automatically update secrets from your `.env` file:

```powershell
.\scripts\update-k8s-secrets.ps1
```

This will update `k8s\base\secrets.yaml` with:
- POSTGRES_PASSWORD
- JWT_SECRET_KEY
- ANTHROPIC_API_KEY ✅ (already set in your .env)
- LANGCHAIN_API_KEY ✅ (already set in your .env)
- LANGSMITH_API_KEY ✅ (already set in your .env)

---

### Step 3: Configure Your EKS Cluster

If you haven't created an EKS cluster yet:

```powershell
# Option A: Using AWS Console
# 1. Go to AWS Console → EKS
# 2. Create cluster "prompt2mesh-cluster"
# 3. Add node group with t3.xlarge instances
# 4. Install AWS Load Balancer Controller

# Option B: Using eksctl (recommended)
eksctl create cluster `
  --name prompt2mesh-cluster `
  --region us-east-1 `
  --nodegroup-name standard-workers `
  --node-type t3.xlarge `
  --nodes 3 `
  --nodes-min 2 `
  --nodes-max 10 `
  --managed
```

Then configure kubectl:

```powershell
aws eks update-kubeconfig --name prompt2mesh-cluster --region us-east-1
```

Verify connection:

```powershell
kubectl cluster-info
kubectl get nodes
```

---

### Step 4: Install AWS Load Balancer Controller

The ALB controller is required for the Ingress to work:

```powershell
# Download IAM policy
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.0/docs/install/iam_policy.json

# Create IAM policy
aws iam create-policy `
  --policy-name AWSLoadBalancerControllerIAMPolicy `
  --policy-document file://iam-policy.json

# Create service account
eksctl create iamserviceaccount `
  --cluster=prompt2mesh-cluster `
  --namespace=kube-system `
  --name=aws-load-balancer-controller `
  --attach-policy-arn=arn:aws:iam::9201-2042-4620:policy/AWSLoadBalancerControllerIAMPolicy `
  --approve

# Install controller with Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller `
  -n kube-system `
  --set clusterName=prompt2mesh-cluster `
  --set serviceAccount.create=false `
  --set serviceAccount.name=aws-load-balancer-controller
```

---

### Step 5: Update Domain Configuration

Edit `k8s\base\ingress.yaml` and update the domain:

```yaml
spec:
  rules:
  - host: prompt2mesh.yourdomain.com  # Change this to your actual domain
    http:
      paths:
      # ...
```

Also update `k8s\per-user\user-instance-template.yaml`:

```yaml
spec:
  rules:
  - host: user-{{ USER_ID }}.prompt2mesh.yourdomain.com  # Change this
```

---

### Step 6: Deploy to EKS

Now you're ready to deploy! Run:

```powershell
.\k8s\deploy.ps1
```

This will:
1. Create the namespace
2. Apply secrets and configmaps
3. Deploy PostgreSQL
4. Initialize the database
5. Deploy backend and frontend
6. Create the ingress

**Monitor the deployment:**

```powershell
# Watch pods starting
kubectl get pods -n prompt2mesh -w

# Check deployment status
kubectl get all -n prompt2mesh

# View logs if there are issues
kubectl logs -f deployment/backend -n prompt2mesh
kubectl logs -f deployment/streamlit -n prompt2mesh
```

---

### Step 7: Configure DNS

Get the ALB DNS name:

```powershell
kubectl get ingress prompt2mesh-ingress -n prompt2mesh
```

Create DNS records in your DNS provider (Route53, Cloudflare, etc.):

```
prompt2mesh.yourdomain.com → <alb-dns-name> (CNAME)
*.prompt2mesh.yourdomain.com → <alb-dns-name> (CNAME for wildcard)
```

---

### Step 8: Test Per-User Instance Creation

Once everything is running, test creating a user instance:

```powershell
# Create instance for test user
python k8s\user_instance_manager.py create test-user

# Check if it's running
kubectl get pods -n prompt2mesh -l user-id=test-user

# List all user instances
python k8s\user_instance_manager.py list

# Delete when done testing
python k8s\user_instance_manager.py delete test-user
```

---

## Quick Command Reference

```powershell
# Check cluster status
kubectl cluster-info
kubectl get nodes

# View all resources
kubectl get all -n prompt2mesh

# View logs
kubectl logs -f deployment/backend -n prompt2mesh
kubectl logs -f deployment/streamlit -n prompt2mesh

# Restart a deployment
kubectl rollout restart deployment/backend -n prompt2mesh

# Scale a deployment
kubectl scale deployment/backend -n prompt2mesh --replicas=3

# Port forward for local testing
kubectl port-forward service/backend 8000:8000 -n prompt2mesh
kubectl port-forward service/streamlit 8501:8501 -n prompt2mesh

# Delete everything
kubectl delete namespace prompt2mesh
```

---

## Troubleshooting

### Images won't pull from ECR
```powershell
# Check if ECR credentials are correct
aws ecr describe-repositories --region us-east-1

# Verify IAM permissions for EKS nodes to pull from ECR
```

### Pods stuck in Pending
```powershell
# Check events
kubectl describe pod <pod-name> -n prompt2mesh

# Check if nodes have enough resources
kubectl top nodes
```

### ALB not created
```powershell
# Check Load Balancer Controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Verify controller is running
kubectl get deployment -n kube-system aws-load-balancer-controller
```

### Database connection errors
```powershell
# Check postgres logs
kubectl logs deployment/postgres -n prompt2mesh

# Test connection from backend pod
kubectl exec -it deployment/backend -n prompt2mesh -- python3 -c "import psycopg2; psycopg2.connect('postgresql://postgres:postgres@postgres:5432/prompt2mesh_auth')"
```

---

## What You Have Now

📁 **Scripts** (`scripts/`):
- `setup-eks.ps1` - Automated build and push to ECR
- `update-k8s-secrets.ps1` - Update secrets from .env

📁 **Kubernetes Manifests** (`k8s/`):
- All base components configured
- Per-user instance templates ready
- Deployment scripts ready

📁 **Documentation**:
- `EKS_DEPLOYMENT_SUMMARY.md` - Complete architecture overview
- `EKS_DEPLOYMENT_CHECKLIST.md` - Detailed checklist
- `k8s/README.md` - Kubernetes deployment guide
- `NEXT_STEPS.md` - This file

✅ **Configuration**:
- AWS credentials in `.env` file
- API keys already set
- Docker setup validated

---

## Recommended Execution Order

1. ✅ **NOW**: Run `.\scripts\setup-eks.ps1` to build and push images
2. ⏭️ **Next**: Run `.\scripts\update-k8s-secrets.ps1` to update secrets
3. ⏭️ **Then**: Create/configure EKS cluster
4. ⏭️ **Then**: Install AWS Load Balancer Controller
5. ⏭️ **Then**: Update domain in ingress files
6. ⏭️ **Then**: Deploy with `.\k8s\deploy.ps1`
7. ⏭️ **Finally**: Configure DNS and test

---

## Need Help?

- Review `EKS_DEPLOYMENT_SUMMARY.md` for architecture details
- Check `EKS_DEPLOYMENT_CHECKLIST.md` for step-by-step guide
- Read `k8s/README.md` for Kubernetes specifics
- AWS EKS docs: https://docs.aws.amazon.com/eks/

**You're ready to start! Begin with Step 1: `.\scripts\setup-eks.ps1`** 🚀
