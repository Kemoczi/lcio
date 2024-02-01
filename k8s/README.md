# Metabotnik

## Development

We use:

- Kubernetes (<https://docs.docker.com/desktop/kubernetes/>)
- Kustomize (<https://kustomize.io/>)
- Skaffold (<https://skaffold.dev/docs/install/>)

To start, after installation of above, type:

```
skaffold dev
```

The app will spin up in your local cluster and sync any changes made to `api/main.py`. You are now able to reach the app via: <http://localhost:8000>.

## Testing

```bash
curl -v https://metabotnik.platforms-test.cloud.brill.com/api/
```

## Deploy to hetzner test

Deployment to the hetzner test and production environment is already automated via [.gitlab-ci.yaml].

If you wish to do a manual deployment to test, type:

```
export AWS_PROFILE=aws-hetzner-test
aws sso login
aws eks update-kubeconfig --name brill-test-hetzner-eks
kubectl apply -k k8s/dev
```

You are now able to reach the app via: <http://metabotnik.platforms-test.cloud.brill.com>

## directory structure

```
├── README.md
├── base
│   ├── kustomization.yaml   - defines default manifests and transformations
│   ├── gitlab-registry-credentials.yaml - container registry access token
│   └── metabotnik.yaml    - application configuration
├── dev
│   └── kustomization.yaml   - overrides for dev/test environment
└── master
    └── kustomization.yaml   - overrides for production environment
```
