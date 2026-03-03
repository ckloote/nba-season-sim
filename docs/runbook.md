# NBA Sim — Deployment Runbook

> **Looking for a simpler option?** For hobby/personal use, [Railway](railway.md) is recommended — no VPC, ALB, or EFS to manage.

Operations guide for running `nba-sim` on AWS ECS Fargate with an Application Load Balancer and EFS-backed SQLite storage.

---

## Prerequisites

- AWS CLI configured (`aws configure`) with permissions for ECR, ECS, ELB, EFS, IAM, and CloudWatch Logs
- Docker installed locally
- An existing VPC with at least two public subnets (for ALB) and two private subnets (for ECS tasks)
- An ECS cluster (Fargate)

Set shell variables used throughout this guide:

```bash
export AWS_REGION=us-east-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export CLUSTER=nba-sim-cluster
export SERVICE=nba-sim
export ECR_REPO=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/nba-sim
```

---

## 1. ECR Repository

```bash
aws ecr create-repository --repository-name nba-sim --region $AWS_REGION
```

---

## 2. Build and Push the Image

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push
docker build -t nba-sim .
docker tag nba-sim:latest $ECR_REPO:latest
docker push $ECR_REPO:latest
```

Tag releases with a version alongside `latest` so rollbacks are simple:

```bash
docker tag nba-sim:latest $ECR_REPO:$(git rev-parse --short HEAD)
docker push $ECR_REPO:$(git rev-parse --short HEAD)
```

---

## 3. IAM Roles

### Task execution role (already exists in most accounts)

The standard `ecsTaskExecutionRole` with the `AmazonECSTaskExecutionRolePolicy` managed policy is sufficient. It allows ECS to pull the image from ECR and write logs to CloudWatch.

### Task role

The task itself doesn't call AWS APIs, so a minimal role with no extra policies is fine:

```bash
aws iam create-role \
  --role-name nba-sim-task-role \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{
      "Effect":"Allow",
      "Principal":{"Service":"ecs-tasks.amazonaws.com"},
      "Action":"sts:AssumeRole"
    }]
  }'
```

---

## 4. CloudWatch Log Group

```bash
aws logs create-log-group --log-group-name /ecs/nba-sim --region $AWS_REGION
```

---

## 5. EFS File System (SQLite Persistence)

EFS provides a persistent POSIX filesystem that survives task replacements and is accessible from any AZ. The SQLite database is written to `/data/nba_sim.db` inside the container, which maps to the EFS root.

```bash
# Create the file system
EFS_ID=$(aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=nba-sim-data \
  --query FileSystemId --output text)

echo "EFS_ID=$EFS_ID"

# Create a mount target in each private subnet (replace subnet IDs and SG)
for SUBNET in subnet-aaaaaaaa subnet-bbbbbbbb; do
  aws efs create-mount-target \
    --file-system-id $EFS_ID \
    --subnet-id $SUBNET \
    --security-groups sg-xxxxxxxx
done
```

**Security group rules for EFS:**
- Inbound: NFS (port 2049) from the ECS task security group
- Outbound: unrestricted (or NFS back to tasks)

Update `deploy/task-definition.json` — set `"fileSystemId"` to `$EFS_ID`.

> **Note:** SQLite uses WAL mode (already configured in `app/storage.py`) which is safe on EFS for a single writer. Do not run more than one ECS task writing to the same DB file simultaneously.

---

## 6. Register the Task Definition

Fill in the placeholders in `deploy/task-definition.json`, then:

```bash
sed \
  -e "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" \
  -e "s/<REGION>/$AWS_REGION/g" \
  -e "s/<EFS_FILE_SYSTEM_ID>/$EFS_ID/g" \
  deploy/task-definition.json > /tmp/task-def-rendered.json

aws ecs register-task-definition \
  --cli-input-json file:///tmp/task-def-rendered.json
```

---

## 7. ALB and Target Group

### Create the target group

```bash
TG_ARN=$(aws elbv2 create-target-group \
  --name nba-sim-tg \
  --protocol HTTP \
  --port 5000 \
  --target-type ip \
  --vpc-id vpc-xxxxxxxx \
  --health-check-protocol HTTP \
  --health-check-path /healthz \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher HttpCode=200 \
  --query TargetGroups[0].TargetGroupArn --output text)

echo "TG_ARN=$TG_ARN"
```

### Create (or reuse) an ALB

```bash
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name nba-sim-alb \
  --subnets subnet-aaaaaaaa subnet-bbbbbbbb \
  --security-groups sg-yyyyyyyy \
  --scheme internet-facing \
  --type application \
  --query LoadBalancers[0].LoadBalancerArn --output text)

# Add an HTTP listener forwarding to the target group
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

---

## 8. Create the ECS Service

```bash
aws ecs create-service \
  --cluster $CLUSTER \
  --service-name $SERVICE \
  --task-definition nba-sim \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-aaaaaaaa,subnet-bbbbbbbb],
    securityGroups=[sg-zzzzzzzz],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=nba-sim,containerPort=5000" \
  --health-check-grace-period-seconds 30
```

**ECS task security group rules:**
- Inbound: port 5000 from the ALB security group
- Outbound: 443 (ECR image pull, CloudWatch), 2049/NFS (EFS mount target)

---

## 9. Updating the Service

Build, push, and force a new deployment:

```bash
docker build -t nba-sim .
docker tag nba-sim:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

aws ecs update-service \
  --cluster $CLUSTER \
  --service $SERVICE \
  --force-new-deployment
```

ECS will drain the old task and start a new one. Because the DB is on EFS, the new task picks up exactly where the old one left off.

---

## 10. Monitoring

### Logs

```bash
# Stream recent log events
aws logs tail /ecs/nba-sim --follow
```

### Service health

```bash
aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount,events:events[:3]}'
```

### ALB health check

The `/healthz` endpoint returns `{"status":"ok"}` with HTTP 200. The ALB marks the target healthy after 2 consecutive successes (60 s from cold start).

### Simulation status

```bash
# Check the last run and available seasons
curl http://<ALB_DNS>/status
```

---

## 11. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Task stops immediately | Missing env var or bad DB_PATH | Check CloudWatch logs for Python traceback |
| Health check failing | Container still starting up | `startPeriod: 15s` gives it time; increase if needed |
| `schedule_games: 0` in `/status` | NBA API unreachable | Verify outbound 443 from ECS SG; simulation still runs on current records |
| EFS mount fails | SG missing NFS rule or mount target not in subnet | Confirm mount targets exist in all task subnets |
| Duplicate runs on same day | Two tasks running simultaneously | Ensure `desired-count=1`; the scheduler is single-writer by design |
| Old season data on homepage | Season rollover, no run yet this season | Hit `POST /admin/rerun` to trigger immediately |
