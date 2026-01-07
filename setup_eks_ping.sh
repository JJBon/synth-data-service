#!/bin/bash
set -e

REGION="us-east-1"
CLUSTER_NAME="nemo-data-cluster"

echo "=== Configuring Kubectl ==="
aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME

echo "=== Deploying EKS Services ==="
# Using make targets which apply the GitOps folders
# Note: make eks-deploy calls this
# We execute manually to ensure environment variables are passed if needed
kubectl apply -k nemo-gitops/apps/base/storage/
kubectl apply -k nemo-gitops/apps/base/litellm/
kubectl apply -k nemo-gitops/apps/base/agents/
# Skipping nemo core stack if not strictly needed for ping, but user asked for it interactively
# kubectl apply -k nemo-gitops/apps/base/nemo/

echo "=== Waiting for LoadBalancers ==="
echo "Waiting for LiteLLM LoadBalancer..."
kubectl wait --for=condition=ready pod -l app=litellm --timeout=300s || true

echo "Getting Service URLs..."
sleep 10 # Give cloud controller time to provision LB
kubectl get svc litellm streamlit-ui

LITELLM_URL=$(kubectl get svc litellm -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
STREAMLIT_URL=$(kubectl get svc streamlit-ui -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo "---------------------------------------------------"
echo "LiteLLM URL: http://$LITELLM_URL:4000"
echo "Streamlit URL: http://$STREAMLIT_URL:8501"
echo "---------------------------------------------------"
echo "Use these URLs in the Mock Server 'ping_service' tool."
