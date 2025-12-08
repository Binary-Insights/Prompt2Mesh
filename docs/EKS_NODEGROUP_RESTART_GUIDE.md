# EKS Node Group Restart Guide

Guide for scaling down EKS nodes to save costs at night and restarting them in the morning.

## Overview

Scaling your EKS node group to 0 nodes at night can significantly reduce AWS costs. This guide provides step-by-step instructions for safely shutting down and restarting your cluster.

## 💰 Cost Savings

- **Running**: ~$0.096/hour per t3.large node ($70/month per node)
- **Stopped**: $0/hour (only pay for EBS storage ~$0.10/GB/month)
- **Potential savings**: ~$50-70/month per node for 12-hour daily shutdown

---

## 🌙 Scaling Down at Night

### Step 1: Check Current Node Group Status

```powershell
# View all node groups
aws eks list-nodegroups --cluster-name prompt2mesh-cluster --region us-east-1

# Get detailed info about the node group
aws eks describe-nodegroup --cluster-name prompt2mesh-cluster --nodegroup-name prompt2mesh-nodegroup --region us-east-1
```

### Step 2: Scale Down to 0 Nodes

```powershell
# Scale down to 0 nodes
aws eks update-nodegroup-config `
  --cluster-name prompt2mesh-cluster `
  --nodegroup-name prompt2mesh-nodegroup `
  --scaling-config minSize=0,maxSize=3,desiredSize=0 `
  --region us-east-1
```

**Expected output:**
```json
{
    "update": {
        "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "status": "InProgress",
        "type": "ConfigUpdate"
    }
}
```

### Step 3: Monitor the Scaling Process

```powershell
# Check update status
aws eks describe-update `
  --name prompt2mesh-cluster `
  --update-id <UPDATE_ID_FROM_ABOVE> `
  --region us-east-1

# Or watch node status
kubectl get nodes --watch
```

**Wait for:**
- All pods to terminate gracefully
- Nodes to drain and terminate
- Update status to show "Successful"
- This typically takes 3-5 minutes

### Step 4: Verify Shutdown

```powershell
# Confirm no nodes are running
kubectl get nodes

# Should show: "No resources found"

# Check node group scaling config
aws eks describe-nodegroup `
  --cluster-name prompt2mesh-cluster `
  --nodegroup-name prompt2mesh-nodegroup `
  --region us-east-1 `
  --query 'nodegroup.scalingConfig'
```

**Expected result:**
```json
{
    "minSize": 0,
    "maxSize": 3,
    "desiredSize": 0
}
```

---

## ☀️ Restarting in the Morning

### Step 1: Scale Up Node Group

```powershell
# Scale back to desired capacity (typically 2 nodes)
aws eks update-nodegroup-config `
  --cluster-name prompt2mesh-cluster `
  --nodegroup-name prompt2mesh-nodegroup `
  --scaling-config minSize=1,maxSize=3,desiredSize=2 `
  --region us-east-1
```

### Step 2: Wait for Nodes to Be Ready

```powershell
# Monitor nodes coming online
kubectl get nodes --watch

# Wait until you see:
# NAME                          STATUS   ROLES    AGE   VERSION
# ip-xxx-xxx-xxx-xxx.ec2...     Ready    <none>   2m    v1.xx.x
# ip-xxx-xxx-xxx-xxx.ec2...     Ready    <none>   2m    v1.xx.x
```

**This typically takes 3-5 minutes.**

### Step 3: Verify System Pods are Running

```powershell
# Check kube-system pods
kubectl get pods -n kube-system

# All pods should be Running or Completed
```

**Key pods to verify:**
- `aws-node-*` (VPC CNI)
- `coredns-*` (DNS)
- `kube-proxy-*` (Networking)
- `ebs-csi-*` (Storage)

### Step 4: Restart Application Deployments

```powershell
# Restart backend
kubectl rollout restart deployment/backend -n prompt2mesh

# Restart frontend
kubectl rollout restart deployment/frontend -n prompt2mesh

# Restart PostgreSQL
kubectl rollout restart deployment/postgres -n prompt2mesh

# Monitor rollout status
kubectl rollout status deployment/backend -n prompt2mesh
kubectl rollout status deployment/frontend -n prompt2mesh
kubectl rollout status deployment/postgres -n prompt2mesh
```

### Step 5: Verify All Services are Running

```powershell
# Check all pods in prompt2mesh namespace
kubectl get pods -n prompt2mesh

# Check services
kubectl get svc -n prompt2mesh

# Get frontend LoadBalancer URL
kubectl get svc frontend -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

**Expected result:**
```
a4492a6f36024441e8d6740b22fe8ee4-1878007781.us-east-1.elb.amazonaws.com
```

### Step 6: Test the Application

```powershell
# Get the frontend URL (add :8501 to the hostname)
$frontendUrl = kubectl get svc frontend -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
Write-Host "Application URL: http://${frontendUrl}:8501"

# Open in browser
Start-Process "http://${frontendUrl}:8501"
```

**Test checklist:**
- ✅ Frontend loads successfully
- ✅ Can create/login to account
- ✅ Backend API responds
- ✅ User Blender pods can be created
- ✅ MCP connections work

---

## 🔧 Troubleshooting

### Issue: Nodes Not Coming Online

```powershell
# Check node group events
aws eks describe-nodegroup `
  --cluster-name prompt2mesh-cluster `
  --nodegroup-name prompt2mesh-nodegroup `
  --region us-east-1 `
  --query 'nodegroup.health'

# Check EC2 instances
aws ec2 describe-instances `
  --filters "Name=tag:eks:nodegroup-name,Values=prompt2mesh-nodegroup" `
  --region us-east-1 `
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name]'
```

### Issue: Pods Stuck in Pending

```powershell
# Describe pod to see events
kubectl describe pod <POD_NAME> -n prompt2mesh

# Common causes:
# - Nodes not ready yet (wait 2-3 more minutes)
# - Insufficient resources (scale up to more nodes)
# - PVC binding issues (check PVs)
```

### Issue: PersistentVolumes Not Attaching

```powershell
# Check PV status
kubectl get pv

# Check PVC status
kubectl get pvc -n prompt2mesh

# If PVs are stuck, restart EBS CSI driver
kubectl rollout restart deployment/ebs-csi-controller -n kube-system
```

### Issue: LoadBalancer Not Ready

```powershell
# Check LoadBalancer service
kubectl describe svc frontend -n prompt2mesh

# Verify AWS Load Balancer Controller
kubectl get pods -n kube-system | grep aws-load-balancer-controller

# If needed, wait 5-10 minutes for LoadBalancer provisioning
```

---

## 🤖 Automation Script (Optional)

### Scale Down Script (`scale-down.ps1`)

```powershell
# scale-down.ps1 - Run this at night
Write-Host "Scaling down EKS cluster..." -ForegroundColor Yellow

aws eks update-nodegroup-config `
  --cluster-name prompt2mesh-cluster `
  --nodegroup-name prompt2mesh-nodegroup `
  --scaling-config minSize=0,maxSize=3,desiredSize=0 `
  --region us-east-1

Write-Host "✅ Cluster scaling down. Check status in 5 minutes." -ForegroundColor Green
Write-Host "Verify with: kubectl get nodes" -ForegroundColor Cyan
```

### Scale Up Script (`scale-up.ps1`)

```powershell
# scale-up.ps1 - Run this in the morning
Write-Host "Starting EKS cluster..." -ForegroundColor Yellow

# Step 1: Scale up nodes
Write-Host "Step 1: Scaling up node group..." -ForegroundColor Cyan
aws eks update-nodegroup-config `
  --cluster-name prompt2mesh-cluster `
  --nodegroup-name prompt2mesh-nodegroup `
  --scaling-config minSize=1,maxSize=3,desiredSize=2 `
  --region us-east-1

Write-Host "Waiting for nodes to be ready (this takes ~5 minutes)..." -ForegroundColor Yellow
Start-Sleep -Seconds 180

# Step 2: Check nodes
Write-Host "`nStep 2: Checking node status..." -ForegroundColor Cyan
kubectl get nodes

# Step 3: Restart deployments
Write-Host "`nStep 3: Restarting application deployments..." -ForegroundColor Cyan
kubectl rollout restart deployment/backend -n prompt2mesh
kubectl rollout restart deployment/frontend -n prompt2mesh
kubectl rollout restart deployment/postgres -n prompt2mesh

Write-Host "`nWaiting for deployments to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Step 4: Check status
Write-Host "`nStep 4: Checking application status..." -ForegroundColor Cyan
kubectl get pods -n prompt2mesh

# Step 5: Get URL
Write-Host "`nStep 5: Getting application URL..." -ForegroundColor Cyan
$frontendUrl = kubectl get svc frontend -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
Write-Host "`n✅ Cluster is ready!" -ForegroundColor Green
Write-Host "Application URL: http://${frontendUrl}:8501" -ForegroundColor Cyan
Write-Host "`nOpening browser..." -ForegroundColor Yellow
Start-Process "http://${frontendUrl}:8501"
```

### Usage

```powershell
# At night (or when not using the cluster)
.\scripts\scale-down.ps1

# In the morning (or when you need the cluster)
.\scripts\scale-up.ps1
```

---

## 📊 Quick Reference

| Action | Command |
|--------|---------|
| **Scale to 0** | `aws eks update-nodegroup-config --cluster-name prompt2mesh-cluster --nodegroup-name prompt2mesh-nodegroup --scaling-config minSize=0,maxSize=3,desiredSize=0 --region us-east-1` |
| **Scale to 2** | `aws eks update-nodegroup-config --cluster-name prompt2mesh-cluster --nodegroup-name prompt2mesh-nodegroup --scaling-config minSize=1,maxSize=3,desiredSize=2 --region us-east-1` |
| **Check nodes** | `kubectl get nodes` |
| **Check pods** | `kubectl get pods -n prompt2mesh` |
| **Restart all** | `kubectl rollout restart deployment/backend deployment/frontend deployment/postgres -n prompt2mesh` |
| **Get URL** | `kubectl get svc frontend -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'` |

---

## ⚠️ Important Notes

1. **Data Persistence**: User data and Blender scenes are stored in EBS volumes (PersistentVolumes). These persist even when nodes are scaled to 0.

2. **Database**: PostgreSQL data is also on a PersistentVolume and will remain intact.

3. **Startup Time**: Allow 5-7 minutes total for complete cluster restart.

4. **Active Users**: Always scale down when no users are active to avoid disrupting sessions.

5. **Cost Optimization**: Consider using AWS Instance Scheduler or EventBridge rules for automatic scheduling.

## 🔄 Regular Startup Sequence Summary

1. Scale node group to 2 nodes (3-5 min)
2. Wait for nodes to be Ready
3. Restart application deployments (2-3 min)
4. Verify pods are Running
5. Test application access
6. **Total time: ~5-7 minutes**
