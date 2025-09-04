# Architecture Agents Collection

## Overview

The Architecture Agents collection provides system design, architectural planning, and technical decision-making capabilities. These agents ensure robust, scalable, and maintainable system architectures.

## Agent Roster

### 1. **System Design Agent** (`system-design/arch-system-design.md`)
- **Purpose**: Comprehensive system architecture and design
- **Capabilities**:
  - System architecture planning
  - Component design and interaction
  - Technology stack selection
  - Scalability planning
  - Performance architecture
  - Security architecture
  - Database design
  - API architecture
  - Microservices design
  - Cloud architecture

## Architecture Patterns

### Supported Patterns
- **Microservices**: Service decomposition and orchestration
- **Event-Driven**: Event sourcing and CQRS
- **Serverless**: FaaS and BaaS architectures
- **Monolithic**: Modular monolith design
- **Hybrid**: Mixed architecture approaches

### Design Principles
- SOLID principles
- DRY (Don't Repeat Yourself)
- KISS (Keep It Simple, Stupid)
- YAGNI (You Aren't Gonna Need It)
- Separation of Concerns
- High Cohesion, Low Coupling

## Architecture Workflow

### Phase 1: Requirements Analysis
```javascript
const requirements = await analyzeRequirements({
  functional: ['user-auth', 'payment-processing', 'notifications'],
  nonFunctional: {
    performance: '< 200ms response time',
    scalability: '10,000 concurrent users',
    availability: '99.99% uptime'
  }
});
```

### Phase 2: Architecture Design
1. **Component Design**
   - Service boundaries
   - Data flow
   - Integration points
   - Communication protocols

2. **Technology Selection**
   - Programming languages
   - Frameworks and libraries
   - Databases and storage
   - Infrastructure choices

3. **Security Design**
   - Authentication/Authorization
   - Data encryption
   - Network security
   - Compliance requirements

### Phase 3: Documentation
```javascript
const documentation = await generateArchitectureDocs({
  diagrams: ['component', 'sequence', 'deployment'],
  specifications: ['API', 'database', 'security'],
  decisions: ['ADRs', 'trade-offs', 'rationale']
});
```

## Architecture Diagrams

### System Architecture
```
┌─────────────────────────────────────────────────┐
│                Load Balancer                     │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────┴─────────┬─────────────┐
        ▼                   ▼             ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  API Gateway │  │  Web Server  │  │  Admin Panel │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                  │
       └─────────┬───────┴──────────────────┘
                 ▼
┌─────────────────────────────────────────────────┐
│              Service Layer                       │
├─────────────┬──────────────┬───────────────────┤
│Auth Service │ Core Service │ Payment Service   │
└─────┬───────┴──────┬───────┴──────┬────────────┘
      │              │               │
      └──────────────┼───────────────┘
                     ▼
┌─────────────────────────────────────────────────┐
│              Data Layer                          │
├──────────┬──────────────┬──────────────────────┤
│PostgreSQL│   MongoDB     │    Redis Cache       │
└──────────┴──────────────┴──────────────────────┘
```

## Decision Records

### Architecture Decision Records (ADRs)
```markdown
# ADR-001: Microservices Architecture

## Status
Accepted

## Context
Need for independent scaling and deployment of services

## Decision
Adopt microservices architecture with service mesh

## Consequences
- Increased complexity
- Better scalability
- Independent deployments
- Need for service orchestration
```

## Technology Stack

### Recommended Stacks
| Layer | Technology | Rationale |
|-------|------------|----------|
| Frontend | React/Next.js | Component reusability, SSR support |
| Backend | Node.js/Go | Performance, ecosystem |
| Database | PostgreSQL | ACID compliance, reliability |
| Cache | Redis | Performance, pub/sub |
| Queue | RabbitMQ/Kafka | Reliability, scalability |
| Container | Docker/K8s | Orchestration, scaling |

## Quality Attributes

### Performance
- Response time targets
- Throughput requirements
- Resource utilization
- Caching strategies

### Scalability
- Horizontal scaling
- Vertical scaling
- Auto-scaling policies
- Load distribution

### Security
- Authentication mechanisms
- Authorization models
- Data encryption
- Network security

### Reliability
- Fault tolerance
- Disaster recovery
- Backup strategies
- Monitoring and alerting

## Integration Patterns

### API Design
```yaml
api:
  style: RESTful
  versioning: URL-based
  authentication: JWT
  rate-limiting: 1000/hour
  documentation: OpenAPI 3.0
```

### Message Patterns
- Request-Response
- Publish-Subscribe
- Message Queue
- Event Streaming

## Best Practices

### 1. Design First
- Start with requirements
- Create prototypes
- Validate assumptions
- Iterate on design

### 2. Document Everything
- Architecture diagrams
- Decision records
- API specifications
- Deployment guides

### 3. Plan for Change
- Loose coupling
- Interface contracts
- Version management
- Migration strategies

## Memory Management

### Persistent Keys
```javascript
const architectureMemory = {
  'architecture/current': 'Current system architecture',
  'architecture/decisions': 'Architecture decision records',
  'architecture/patterns': 'Applied design patterns',
  'architecture/stack': 'Technology stack choices',
  'architecture/risks': 'Identified architectural risks'
};
```

## Coordination Protocol

When working with other agents:
1. Share architecture constraints
2. Provide integration specifications
3. Define service contracts
4. Establish communication protocols
5. Document dependencies

---

For detailed specifications and examples, refer to individual agent documentation in subdirectories.