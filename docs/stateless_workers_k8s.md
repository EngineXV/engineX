# Stateless Workers on Kubernetes

## Objective
Deploy EngineX workers as stateless pods that can scale horizontally without sticky sessions, using shared storage and claim-based session assignment.

## Architecture
- **Shared Storage**: NFS, EFS, or a database (e.g., PostgreSQL) for session state.
- **Claim API**: Workers call `ClaimManager.try_claim()` on startup.
- **Horizontal Scaling**: Any pod can handle any session.

## Deployment Steps
1. Provision shared volume and mount at `/enginex/data`.
2. Set `ENGINEX_STORAGE_BASE` and `ENGINEX_WORKER_ID`.
3. Health checks: readiness/liveness probes.
4. Graceful shutdown: on SIGTERM, release claims and flush.

## Claim Lifecycle
- TTL (60s) – expired claims are re‑claimable.
- Background reaper to clear orphaned claims.

## Example Deployment Snippet
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: enginex-worker
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: worker
        image: enginex:latest
        env:
        - name: ENGINEX_STORAGE_BASE
          value: /enginex/data
        - name: ENGINEX_WORKER_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        volumeMounts:
        - name: shared-storage
          mountPath: /enginex/data
        livenessProbe:
          exec:
            command: ["enginex", "health"]
        readinessProbe:
          exec:
            command: ["enginex", "ready"]
      volumes:
      - name: shared-storage
        nfs:
          server: nfs-server.example.com
          path: /exports/enginex

