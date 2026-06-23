# Finance Tracker — Full DevOps Pipeline

A Flask/SQLAlchemy personal-finance web app taken through a complete DevOps lifecycle: Docker, GitHub Actions CI, Amazon ECR, Kubernetes, and Terraform-provisioned AWS EKS.

---

## Project History

The Flask application itself was originally built as a class project during my junior year of college. Everything in this repository around the app — Docker containerization, GitHub Actions CI/CD, Amazon ECR image publishing, Kubernetes manifests, Terraform-provisioned EKS infrastructure, and the full deployment workflow — was added afterward as independent, self-directed work. The goal was to take a real working application and run it through the kind of production DevOps pipeline you'd encounter on the job, from a local container all the way to a publicly-accessible load-balanced cluster on AWS.

---

## Project Overview

The application is a multi-user personal finance tracker. Key features:

- **User authentication** — registration and login with password hashing via Flask-Bcrypt
- **Transaction tracking** — log income and expense entries with category, date, and notes; delete entries with password confirmation
- **Savings goals** — set named goals with a target amount and due date; view and manage them from a dedicated goals page
- **Dashboard charts** — matplotlib generates a pie chart breaking down income vs. expenses on the fly
- **News page** — supplementary page served by the same app

---

## Tech Stack

| Layer | Technology |
|---|---|
| Application | Python 3.12, Flask 3, SQLAlchemy, Flask-WTF, Flask-Bcrypt, matplotlib |
| WSGI server | gunicorn |
| Database | SQLite (default) / any `DATABASE_URL`-compatible DB |
| Testing | pytest |
| Containerization | Docker (python:3.12-slim base) |
| CI | GitHub Actions |
| Image registry | Amazon ECR |
| Orchestration | Kubernetes (kind locally, AWS EKS in the cloud) |
| Infrastructure-as-Code | Terraform (AWS VPC + EKS modules) |

---

## DevOps Pipeline & Architecture

### Lifecycle

```
Developer pushes to main
        │
        ├──► CI (ci.yml): pytest → docker build  [also runs on PRs]
        │
        ▼
CD (cd.yml)
        │
        │  1. pytest (gate)
        │  2. docker build --platform linux/amd64
        │  3. push to ECR  (tagged: commit SHA + latest)
        │  4. kubectl set image + kubectl rollout status
        │
        ▼
┌──────────────────────┐
│     Amazon ECR       │
└──────────┬───────────┘
           │
           ▼
  ┌─────────────────────────────────────┐
  │           AWS EKS                   │
  │  Deployment (2 replicas, rolling)   │
  │  Service (LoadBalancer → port 80)   │
  │  Secret (env vars injected)         │
  └─────────────────────────────────────┘
           │
           │  cluster provisioned by
           ▼
  ┌────────────────┐
  │   Terraform    │
  │  VPC + EKS +   │
  │  node group    │
  └────────────────┘
```

### Step-by-step

1. **Containerize** — The `dockerfile` builds a `python:3.12-slim` image, installs dependencies, copies the app, and starts it with `gunicorn --bind 0.0.0.0:5000`. gunicorn replaces Flask's development server for production use.

2. **CI via GitHub Actions** (`.github/workflows/ci.yml`) — Every push and pull request to `main` runs two jobs:
   - `test`: installs Python 3.12, installs requirements, and runs `pytest tests/ -v`.
   - `docker-build`: builds the Docker image to validate the Dockerfile. This job is declared with `needs: test` so it only runs if the test suite passes.

3. **CD via GitHub Actions** (`.github/workflows/cd.yml`) — Every push to `main` also triggers the CD workflow alongside CI. It re-runs the test suite as its own gate, then authenticates to AWS using credentials stored as GitHub Secrets. It builds a `linux/amd64` image (required by EKS nodes) and pushes it to ECR tagged with the git commit SHA, so every deployed image is uniquely identified and traceable. It then runs `kubectl set image` to update the running deployment and `kubectl rollout status` to confirm the rollout completes within 120 seconds. A git push to `main` now flows automatically to the running cluster.

4. **Kubernetes manifests** (`k8s/`) define three resources:
   - `deployment.yaml` — runs 2 replicas of the container, pulling from ECR, injecting secrets via `envFrom`.
   - `service.yaml` — a `LoadBalancer` service that exposes port 80 externally and forwards to the container's port 5000.
   - `secret.yaml` — holds `FLASK_SECRET_KEY` (and optionally `DATABASE_URL`) as a Kubernetes Secret.

5. **Local → cloud promotion** — Manifests were developed and debugged against a local `kind` cluster (free, fast feedback). The same `kubectl apply -f k8s/` command is then run against the EKS cluster. Same manifests, different context.

6. **EKS infrastructure via Terraform** (`terraform/`) — The cluster is defined as code across four files:
   - `Provider.tf` — pins the AWS provider to `~> 5.0`, region `us-east-1`.
   - `Variables.tf` — `cluster_name` (default: `finance`) and `region`.
   - `Vpc.tf` — uses the official `terraform-aws-modules/vpc` module to create a VPC with public and private subnets across two AZs, a NAT gateway, and the subnet tags EKS requires for its load balancer.
   - `Eks.tf` — uses `terraform-aws-modules/eks` to create an EKS 1.30 cluster with a managed node group of `t3.small` instances (desired: 2, max: 3).

---

## Running Locally with Docker

Build the image:

```bash
docker build -t finance-app .
```

Run it (the app requires a secret key at runtime):

```bash
docker run -p 5000:5000 \
  -e FLASK_SECRET_KEY=your-secret-key-here \
  finance-app
```

Then open `http://localhost:5000`.

**Database:** By default the app uses SQLite at `instance/finance.db` inside the container. The `dockerfile` declares `/app/instance` as a volume, so you can mount a host directory to persist data across container restarts:

```bash
docker run -p 5000:5000 \
  -e FLASK_SECRET_KEY=your-secret-key-here \
  -v "$(pwd)/instance:/app/instance" \
  finance-app
```

To use a different database, set `DATABASE_URL` to any SQLAlchemy-compatible connection string.

---

## Infrastructure (Terraform)

The `terraform/` directory provisions the full EKS cluster on AWS.

**Provision the cluster:**

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

After `apply` completes, Terraform prints the `configure_kubectl` output — an `aws eks update-kubeconfig` command. Run it to point your local `kubectl` at the new cluster.

**Deploy the app:**

```bash
kubectl apply -f k8s/
```

Check rollout status:

```bash
kubectl get pods
kubectl get service finance-service   # wait for EXTERNAL-IP to populate
```

**Tear down:**

```bash
terraform destroy
```

The cluster is torn down between sessions to avoid ongoing EC2 and NAT gateway charges. The Kubernetes manifests and Terraform config are the source of truth — the cluster can be recreated from scratch in a single `terraform apply`.

---

## Screenshots

App served by AWS EKS at the public LoadBalancer address (cluster torn down after to avoid charges):

![App running on EKS](docs/screenshot/aws%20webserver%20proof.png)

Running pods on the cluster:

![kubectl get pods](docs/screenshot/kubectl%20get%20pods.png)

Service showing the assigned external IP:

![kubectl get service](docs/screenshot/kubectl%20get%20service.png)

Cluster nodes:

![kubectl get nodes](docs/screenshot/kubectl%20get%20nodes.png)

GitHub Actions CI/CD pipeline overview:

![GitHub Actions CI/CD pipeline](docs/screenshots/cicd-pipeline.png)

CD workflow deploy-to-EKS steps:

![CD deploy steps](docs/screenshots/cd-deploy-detail.png)

---

## Key Engineering Decisions & Lessons Learned

**Secrets must be injected at runtime, not baked into the image.** Flask requires a `SECRET_KEY` for session signing. The first containerized run failed immediately because the key wasn't set. The fix was a Kubernetes Secret (or `-e` flag locally) — credentials never go in the image.

**Database schema initialization in a fresh container.** The SQLite file doesn't exist in a new container. The app calls `db.create_all()` inside an `app.app_context()` block at startup, which creates the schema on first run. This had to be wired correctly before the containerized app would accept any requests.

**Relative vs. absolute SQLite path.** gunicorn's working directory differs from Flask's `root_path`, which caused the SQLite path to resolve differently than it did under the dev server. Using `os.path.join(app.instance_path, 'finance.db')` with an explicit `os.makedirs(app.instance_path, exist_ok=True)` made the path deterministic regardless of how the process was launched.

**IAM scoping in a sandbox account.** The project started with a least-privilege IAM user scoped to ECR only. When it came time to provision EKS, `terraform apply` produced explicit `AccessDenied` errors across EC2, VPC, and IAM. Rather than debugging a minimal EKS policy set, a deliberate decision was made to grant broader permissions in this sandbox account and move on — the tradeoff between security hygiene and learning velocity is different in a personal lab than in production.

**Cross-architecture image builds.** Development happened on an Apple Silicon (arm64) Mac. EKS worker nodes run `linux/amd64`. Building without specifying the platform produced an arm64 image that wouldn't run on the cluster. The fix is explicit platform targeting:

```bash
docker build --platform linux/amd64 -t finance-app .
```

**Local Kubernetes before AWS.** Using `kind` to develop and validate the Kubernetes manifests locally meant all the debugging (wrong image names, missing secrets, port mismatches) happened for free before any AWS resources were running. The manifests worked correctly on EKS on the first real deploy.

---

## Future Improvements

- **OIDC for AWS authentication** — The CD workflow authenticates using long-lived AWS access keys stored as GitHub Secrets. Replacing these with GitHub's OIDC provider would let GitHub Actions assume an IAM role directly, with no static credentials to rotate or leak.
- **HTTPS with a custom domain** — The app is currently reachable over plain HTTP at the LoadBalancer's auto-assigned hostname. Adding a custom domain with TLS (via ACM and an ALB Ingress) and running it on an always-on host would make it suitable for a persistent public deployment.
