# Documentation Agents Collection

## Overview

The Documentation Agents collection provides automated documentation generation, API documentation, and knowledge management capabilities.

## Agent Roster

### 1. **API Documentation Agent** (`api-docs/docs-api-openapi.md`)
- **Purpose**: OpenAPI/Swagger documentation generation
- **Capabilities**:
  - OpenAPI spec generation
  - Interactive documentation
  - Code examples
  - SDK generation
  - Versioning support
  - Authentication documentation
  - Error documentation
  - Webhook documentation

## Documentation Pipeline

```
┌─────────────────────────────────────────────────┐
│           Code Analysis                          │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│        Documentation Generation                  │
│  • API endpoints                                 │
│  • Data models                                   │
│  • Examples                                      │
│  • Tutorials                                     │
└─────────────────┬───────────────────────────────┘
                  ▼
┌─────────────────────────────────────────────────┐
│         Documentation Publishing                 │
│  • Static site generation                        │
│  • Version management                            │
│  • Search indexing                               │
└─────────────────────────────────────────────────┘
```

## Documentation Types

- API Reference
- Developer Guides
- Architecture Documentation
- Deployment Guides
- User Manuals
- Release Notes
- Migration Guides

## Best Practices

- Keep documentation close to code
- Automate generation
- Version documentation with code
- Include examples
- Maintain consistency
- Regular updates
- User feedback integration

---

For detailed specifications, refer to individual agent documentation.
