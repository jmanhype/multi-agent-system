# Analysis Agents Collection

## Overview

The Analysis Agents collection provides comprehensive code analysis, quality assessment, and automated review capabilities. These agents work together to ensure code quality, identify issues, and provide actionable insights throughout the development lifecycle.

## Agent Roster

### 1. **Code Analyzer** (`code-analyzer.md`)
- **Purpose**: Advanced code quality analysis and comprehensive reviews
- **Capabilities**:
  - Code quality assessment and metrics
  - Performance bottleneck detection
  - Security vulnerability scanning
  - Architectural pattern analysis
  - Dependency analysis
  - Code complexity evaluation
  - Technical debt identification
  - Best practices validation
  - Code smell detection
  - Refactoring suggestions

### 2. **Code Review Agents** (`code-review/`)
- **Purpose**: Automated code review and quality gates
- **Sub-agents**:
  - **analyze-code-quality.md**: Quality metrics and standards enforcement
  - Additional review specialists for specific domains

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Analysis Request                    │
│         (PR, Commit, Manual Trigger)             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│            Code Analyzer Agent                   │
│  • Static Analysis                               │
│  • Pattern Recognition                           │
│  • Dependency Mapping                            │
│  • Security Scanning                             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│          Code Review Sub-Agents                  │
│  • Quality Metrics                               │
│  • Standards Compliance                          │
│  • Best Practices                                │
│  • Documentation                                 │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│           Analysis Report Generation             │
│  • Actionable Insights                           │
│  • Priority Recommendations                      │
│  • Trend Analysis                                │
└─────────────────────────────────────────────────┘
```

## Analysis Workflow

### Phase 1: Initial Assessment
```javascript
// Trigger comprehensive analysis
const analysis = await analyzeCodebase({
  scope: 'full',
  depth: 'deep',
  includeMetrics: true,
  includeSecurity: true,
  includePerformance: true
});
```

### Phase 2: Deep Analysis
1. **Static Code Analysis**
   - Syntax validation
   - Type checking
   - Linting rules
   - Code formatting

2. **Dynamic Analysis**
   - Runtime behavior
   - Memory profiling
   - Performance bottlenecks
   - Resource utilization

3. **Security Analysis**
   - Vulnerability scanning
   - Dependency auditing
   - Secret detection
   - OWASP compliance

### Phase 3: Report Generation
```javascript
// Generate comprehensive report
const report = await generateAnalysisReport({
  format: 'detailed',
  includeRecommendations: true,
  priorityThreshold: 'medium',
  actionableOnly: true
});
```

## Integration Points

### With Development Pipeline
- **Pre-commit hooks**: Validate code quality before commits
- **Pull Request checks**: Automated review on PRs
- **CI/CD integration**: Quality gates in build pipeline
- **IDE integration**: Real-time feedback during development

### With Other Agents
- **Core Agents**: Provide analysis data to development team
- **Testing Agents**: Identify areas needing test coverage
- **Documentation Agents**: Highlight documentation gaps
- **Optimization Agents**: Supply performance metrics

## Analysis Metrics

### Code Quality Metrics
| Metric | Description | Threshold |
|--------|-------------|-----------|
| Cyclomatic Complexity | Code path complexity | < 10 |
| Code Coverage | Test coverage percentage | > 80% |
| Duplication | Duplicate code percentage | < 5% |
| Technical Debt | Estimated fix time | < 5 days |
| Documentation | Code documentation coverage | > 70% |

### Security Metrics
| Metric | Description | Severity |
|--------|-------------|----------|
| Vulnerabilities | Security issues found | Critical/High/Medium/Low |
| Dependencies | Outdated/vulnerable packages | Risk assessment |
| Secrets | Exposed credentials | Critical |
| OWASP | Top 10 compliance | Pass/Fail |

### Performance Metrics
| Metric | Description | Target |
|--------|-------------|--------|
| Response Time | API endpoint latency | < 200ms |
| Memory Usage | Resource consumption | < 512MB |
| CPU Usage | Processing efficiency | < 70% |
| Database Queries | Query optimization | < 100ms |

## Configuration

### Analysis Settings
```yaml
analysis:
  depth: deep              # shallow, medium, deep
  scope: full             # full, changes-only, targeted
  
  quality:
    enabled: true
    complexity_threshold: 10
    duplication_threshold: 5
    coverage_threshold: 80
    
  security:
    enabled: true
    scan_dependencies: true
    detect_secrets: true
    owasp_check: true
    
  performance:
    enabled: true
    profile_memory: true
    analyze_queries: true
    benchmark_apis: true
    
  reporting:
    format: detailed      # summary, detailed, json
    include_trends: true
    actionable_only: false
    priority_filter: all  # all, high, critical
```

### Custom Rules
```javascript
// Define custom analysis rules
const customRules = {
  naming: {
    functions: /^[a-z][a-zA-Z0-9]*$/,
    classes: /^[A-Z][a-zA-Z0-9]*$/,
    constants: /^[A-Z_]+$/
  },
  
  complexity: {
    maxCyclomatic: 10,
    maxNesting: 4,
    maxParameters: 5,
    maxLines: 200
  },
  
  documentation: {
    requireJSDoc: true,
    requireParamDesc: true,
    requireReturnDesc: true
  }
};
```

## Usage Examples

### Manual Analysis Trigger
```bash
# Run comprehensive analysis
npx claude-flow analyze --scope full --depth deep

# Analyze specific module
npx claude-flow analyze --target src/payments --include-deps

# Security-focused analysis
npx claude-flow analyze --security-only --scan-secrets

# Performance profiling
npx claude-flow analyze --performance --profile-memory
```

### Programmatic Integration
```javascript
const { AnalysisAgent } = require('@claude/analysis');

async function runAnalysis(projectPath) {
  const agent = new AnalysisAgent({
    path: projectPath,
    config: './analysis.config.yml'
  });
  
  // Run full analysis
  const results = await agent.analyze({
    quality: true,
    security: true,
    performance: true
  });
  
  // Generate report
  const report = await agent.generateReport(results, {
    format: 'markdown',
    includeCharts: true
  });
  
  // Apply automatic fixes
  if (results.autoFixAvailable) {
    await agent.applyFixes(results.fixes);
  }
  
  return report;
}
```

### CI/CD Integration
```yaml
# GitHub Actions
name: Code Analysis
on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Analysis
        run: |
          npx claude-flow analyze \
            --scope changes-only \
            --fail-on critical
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: analysis-report
          path: analysis-report.html
```

## Analysis Reports

### Report Structure
```markdown
# Code Analysis Report

## Executive Summary
- Overall Score: 8.5/10
- Critical Issues: 2
- Total Issues: 47
- Technical Debt: 3.2 days

## Critical Issues
1. SQL Injection vulnerability in UserController
2. Memory leak in DataProcessor

## Quality Metrics
- Code Coverage: 82%
- Complexity: 7.3 (average)
- Duplication: 3.2%

## Recommendations
1. Immediate: Fix critical security issues
2. Short-term: Improve test coverage
3. Long-term: Refactor complex modules
```

### Trend Analysis
```javascript
// Track quality trends over time
const trends = {
  weekly: {
    coverage: [78, 80, 82, 85],
    complexity: [8.1, 7.8, 7.3, 7.0],
    issues: [62, 55, 47, 41]
  },
  
  improvements: {
    fixedIssues: 21,
    addedTests: 47,
    refactoredFiles: 12
  },
  
  projections: {
    debtReduction: '2 days/week',
    coverageTarget: '90% in 4 weeks',
    complexityTarget: '6.0 in 6 weeks'
  }
};
```

## Best Practices

### 1. Continuous Analysis
- Run analysis on every commit
- Set up quality gates
- Track metrics over time
- Automate fix application

### 2. Incremental Improvement
- Focus on critical issues first
- Set realistic targets
- Celebrate improvements
- Learn from trends

### 3. Team Collaboration
- Share analysis reports
- Discuss findings in reviews
- Document decisions
- Maintain standards

## Memory Management

### Persistent Keys
```javascript
const memoryKeys = {
  'analysis/latest': 'Most recent analysis results',
  'analysis/trends': 'Historical trend data',
  'analysis/baseline': 'Quality baseline metrics',
  'analysis/rules': 'Custom analysis rules',
  'analysis/exceptions': 'Approved exceptions'
};
```

### Cache Strategy
- Cache analysis results for 24 hours
- Invalidate on code changes
- Store trend data permanently
- Archive monthly reports

## Performance Optimization

### Analysis Speed
- Parallel file processing
- Incremental analysis
- Smart caching
- Distributed scanning

### Resource Usage
- Memory limit: 2GB
- CPU cores: 4 (max)
- Timeout: 10 minutes
- Queue limit: 1000 files

## Security Considerations

### Sensitive Data
- Never log passwords
- Mask API keys in reports
- Encrypt analysis cache
- Secure report storage

### Access Control
- Role-based permissions
- Audit trail logging
- Secure API endpoints
- Encrypted communications

## Troubleshooting

### Common Issues

#### Analysis Timeout
```bash
# Increase timeout
export ANALYSIS_TIMEOUT=1800
npx claude-flow analyze

# Or analyze in chunks
npx claude-flow analyze --chunk-size 100
```

#### Memory Issues
```bash
# Increase memory limit
export NODE_OPTIONS="--max-old-space-size=4096"
npx claude-flow analyze

# Or use streaming mode
npx claude-flow analyze --stream
```

#### False Positives
```javascript
// Configure exceptions
const exceptions = {
  security: {
    ignore: ['test/**', 'mock/**'],
    allowlist: ['specific-file.js']
  },
  
  quality: {
    complexity: {
      'complex-algorithm.js': 15  // Allow higher complexity
    }
  }
};
```

## Future Enhancements

### Planned Features
- AI-powered code suggestions
- Automatic refactoring
- Predictive quality metrics
- Cross-repository analysis
- Real-time collaboration

### Research Areas
- Machine learning for pattern detection
- Natural language code reviews
- Automated fix generation
- Performance prediction
- Security threat modeling

---

For detailed agent specifications and integration examples, refer to individual agent documentation files in this directory.