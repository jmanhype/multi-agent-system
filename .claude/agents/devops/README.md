# DevOps Agents Collection

## Overview

The DevOps Agents collection provides CI/CD automation, infrastructure management, deployment orchestration, and operational excellence capabilities.

## Agent Roster

### 1. **CI/CD GitHub Agent** (`ci-cd/ops-cicd-github.md`)
- **Purpose**: GitHub Actions and CI/CD pipeline management
- **Capabilities**:
  - Pipeline creation and optimization
  - Automated testing integration
  - Deployment automation
  - Release management
  - Environment configuration
  - Secret management
  - Monitoring integration

## DevOps Pipeline

```
┌─────────────────────────────────────────────────┐
│              Code Commit                         │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│           Continuous Integration                 │
│  • Build                                         │
│  • Test                                          │
│  • Lint                                          │
│  • Security scan                                 │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│         Continuous Deployment                    │
│  • Staging deployment                            │
│  • Integration tests                             │
│  • Production deployment                         │
│  • Monitoring setup                              │
└─────────────────────────────────────────────────┘
```

## Infrastructure as Code

### Supported Platforms
- GitHub Actions
- GitLab CI/CD
- Jenkins
- CircleCI
- Azure DevOps
- AWS CodePipeline

## Best Practices

- Automated everything
- Infrastructure as code
- Immutable deployments
- Blue-green deployments
- Canary releases
- Comprehensive monitoring
- Disaster recovery planning

---

For detailed specifications, refer to individual agent documentation.
