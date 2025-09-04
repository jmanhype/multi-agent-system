# Claude Hooks System

## Overview

This directory contains the automated hook system that provides lifecycle management, quality gates, and continuous validation for all Claude Code operations. Hooks enable automated testing, validation, and analysis at critical points in the development workflow.

## Hook Collection

### Core Hooks

#### 1. **Pre-Run Hook** (`pre_run.sh`)
- **Purpose**: Pre-execution validation and environment preparation
- **Triggers**: Before any code execution or deployment
- **Key Features**:
  - **Language Detection**: Automatically detects Python, Node.js, Rust, Elixir projects
  - **Dependency Management**: Ensures dependencies are installed
  - **Linting**: Runs appropriate linters (ruff, flake8, eslint, clippy)
  - **Type Checking**: Executes type checkers (mypy, TypeScript)
  - **Unit Testing**: Runs test suites (pytest, jest, cargo test)
  - **Security Scanning**: Basic credential and secret detection
  - **Large File Detection**: Warns about files over 50MB

#### 2. **Post-Run Hook** (`post_run.sh`)
- **Purpose**: Post-execution analysis and reporting
- **Triggers**: After code execution completes
- **Key Features**:
  - Execution result analysis
  - Performance metrics collection
  - Resource usage reporting
  - Log aggregation
  - Success/failure notifications

#### 3. **Verification Gate** (`verify_gate.sh`)
- **Purpose**: Truth score verification and quality gates
- **Triggers**: Before critical operations (deployment, merge)
- **Key Features**:
  - Truth score calculation
  - Quality threshold enforcement
  - Security validation
  - Compliance checking
  - Rollback triggers

### Hook Logs

#### **Log Files** (`logs/`)
The logs directory contains comprehensive JSON logs for all hook activities:

- **`chat.json`**: Conversational interaction logs
- **`pre_tool_use.json`**: Pre-execution tool usage logs
- **`post_tool_use.json`**: Post-execution tool results
- **`stop.json`**: Session termination logs
- **`sub_agent_stop.json`**: Sub-agent lifecycle logs

## Hook Architecture

```
┌─────────────────────────────────────────────────┐
│                 Trigger Event                    │
│          (PR, Push, Deploy, Execute)             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Pre-Run Validation                  │
│  • Environment Check                             │
│  • Dependency Validation                         │
│  • Linting & Type Checking                       │
│  • Unit Test Execution                           │
│  • Security Scanning                             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│             Main Execution Phase                 │
│         (User Code / Agent Tasks)                │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│            Post-Run Analysis                     │
│  • Result Validation                             │
│  • Performance Analysis                          │
│  • Log Aggregation                               │
│  • Report Generation                             │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│           Verification Gate                      │
│  • Truth Score Assessment                        │
│  • Quality Gates                                 │
│  • Deployment Decision                           │
└─────────────────────────────────────────────────┘
```

## Language-Specific Features

### Python Projects
```bash
# Detected by: pyproject.toml, requirements.txt, setup.py
- Virtual environment validation
- Ruff/Flake8 linting
- Mypy type checking
- Pytest unit testing
- Coverage reporting
```

### Node.js Projects
```bash
# Detected by: package.json
- Node modules installation
- ESLint code quality
- TypeScript compilation
- Jest/Vitest testing
- NPM script execution
```

### Rust Projects
```bash
# Detected by: Cargo.toml
- Cargo check compilation
- Clippy linting
- Cargo test execution
- Benchmark running
- Documentation generation
```

### Elixir Projects
```bash
# Detected by: mix.exs
- Mix dependency resolution
- Code formatting check
- Credo code analysis
- ExUnit testing
- Dialyzer type checking
```

## Hook Configuration

### Environment Variables
```bash
# Hook behavior control
CLAUDE_HOOKS_ENABLED=true           # Enable/disable all hooks
CLAUDE_PRE_RUN_ENABLED=true        # Enable pre-run checks
CLAUDE_POST_RUN_ENABLED=true       # Enable post-run analysis
CLAUDE_VERIFY_GATE_ENABLED=true    # Enable verification gates

# Validation thresholds
CLAUDE_MIN_COVERAGE=80             # Minimum test coverage
CLAUDE_MAX_COMPLEXITY=10            # Maximum cyclomatic complexity
CLAUDE_TRUTH_SCORE_THRESHOLD=0.85  # Minimum truth score

# Performance limits
CLAUDE_MAX_EXECUTION_TIME=300      # Maximum execution time (seconds)
CLAUDE_MAX_MEMORY_USAGE=1024       # Maximum memory usage (MB)
```

### Custom Hook Configuration
```json
{
  "hooks": {
    "pre_run": {
      "enabled": true,
      "timeout": 120,
      "validators": ["lint", "type", "test", "security"],
      "fail_fast": false
    },
    "post_run": {
      "enabled": true,
      "collectors": ["metrics", "logs", "artifacts"],
      "report_format": "json"
    },
    "verify_gate": {
      "enabled": true,
      "thresholds": {
        "truth_score": 0.85,
        "coverage": 0.80,
        "security": "pass"
      }
    }
  }
}
```

## Usage Examples

### Manual Hook Execution
```bash
# Run pre-execution checks
./hooks/pre_run.sh

# Run with verbose output
./hooks/pre_run.sh --verbose

# Dry run mode (no changes)
./hooks/pre_run.sh --dry-run

# Run specific validators
./hooks/pre_run.sh --validators lint,test

# Skip specific checks
./hooks/pre_run.sh --skip security
```

### Programmatic Hook Integration
```javascript
// Node.js integration
const { execSync } = require('child_process');

function runPreChecks(projectPath) {
  try {
    const result = execSync('./hooks/pre_run.sh', {
      cwd: projectPath,
      encoding: 'utf8'
    });
    console.log('Pre-checks passed:', result);
    return true;
  } catch (error) {
    console.error('Pre-checks failed:', error.stdout);
    return false;
  }
}

// Python integration
import subprocess

def run_pre_checks(project_path):
    try:
        result = subprocess.run(
            ['./hooks/pre_run.sh'],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Pre-checks passed: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Pre-checks failed: {e.stdout}")
        return False
```

### CI/CD Integration
```yaml
# GitHub Actions
name: Claude Hooks Validation
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Pre-Checks
        run: ./hooks/pre_run.sh
      - name: Execute Main Task
        run: npm run build
      - name: Run Post-Analysis
        run: ./hooks/post_run.sh
      - name: Verify Quality Gates
        run: ./hooks/verify_gate.sh

# GitLab CI
validate:
  script:
    - ./hooks/pre_run.sh
    - npm run build
    - ./hooks/post_run.sh
    - ./hooks/verify_gate.sh
  only:
    - merge_requests
    - main
```

## Log Analysis

### Log Structure
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "hook": "pre_run",
  "event": "validation",
  "project": {
    "type": "python",
    "path": "/Users/speed/project",
    "dependencies": ["pytest", "mypy", "ruff"]
  },
  "results": {
    "linting": {
      "status": "passed",
      "issues": 0,
      "duration": 2.3
    },
    "testing": {
      "status": "passed",
      "coverage": 0.92,
      "duration": 15.7
    },
    "security": {
      "status": "warning",
      "findings": ["potential API key in config.py"],
      "duration": 0.8
    }
  },
  "overall_status": "passed_with_warnings"
}
```

### Log Aggregation
```bash
# Parse and analyze hook logs
jq '.results | select(.overall_status == "failed")' hooks/logs/pre_tool_use.json

# Get execution statistics
jq -s 'map(.results.testing.coverage) | add/length' hooks/logs/*.json

# Find security issues
jq '.results.security | select(.findings | length > 0)' hooks/logs/*.json
```

## Security Features

### Credential Scanning
- API key detection patterns
- Password/secret detection
- Environment variable validation
- Certificate expiration checking
- SSH key detection

### Compliance Validation
- License compatibility checking
- Dependency vulnerability scanning
- OWASP compliance validation
- PCI/HIPAA compliance checks (configurable)

### Access Control
- Hook execution permissions
- Log file access restrictions
- Sensitive data masking
- Audit trail generation

## Performance Optimization

### Caching Strategies
```bash
# Cache directory for hook results
~/.claude/hooks/cache/
  ├── lint_results/
  ├── test_results/
  ├── dependency_cache/
  └── build_artifacts/
```

### Parallel Execution
- Concurrent validator execution
- Parallel test suite running
- Distributed linting across files
- Async log processing

### Resource Management
- Memory usage monitoring
- CPU utilization tracking
- Disk space validation
- Network bandwidth management

## Troubleshooting

### Common Issues

#### 1. Hook Timeout
```bash
# Increase timeout
export CLAUDE_HOOK_TIMEOUT=300
./hooks/pre_run.sh

# Or disable timeout
./hooks/pre_run.sh --no-timeout
```

#### 2. Permission Errors
```bash
# Fix hook permissions
chmod +x hooks/*.sh

# Run with elevated permissions if needed
sudo ./hooks/pre_run.sh
```

#### 3. Missing Dependencies
```bash
# Install hook dependencies
pip install -r hooks/requirements.txt
npm install -g @claude/hooks
```

### Debug Mode
```bash
# Enable debug output
export CLAUDE_HOOKS_DEBUG=true
./hooks/pre_run.sh

# Verbose logging
./hooks/pre_run.sh -v

# Trace execution
set -x
./hooks/pre_run.sh
```

## Best Practices

### Hook Development
1. **Idempotency**: Hooks should be safe to run multiple times
2. **Error Handling**: Graceful failure with informative messages
3. **Performance**: Keep hooks fast (< 30 seconds typical)
4. **Logging**: Comprehensive logging for debugging
5. **Documentation**: Clear inline documentation

### Hook Deployment
1. **Version Control**: Track hook changes in git
2. **Testing**: Test hooks in isolation before deployment
3. **Rollback**: Maintain previous hook versions
4. **Monitoring**: Track hook execution metrics
5. **Alerts**: Set up notifications for hook failures

### Security Considerations
1. **Input Validation**: Sanitize all inputs
2. **Secret Management**: Never log sensitive data
3. **Access Control**: Restrict hook execution permissions
4. **Audit Trail**: Log all hook executions
5. **Update Regularly**: Keep hook dependencies updated

## Future Enhancements

### Planned Features
- **AI-Powered Analysis**: ML-based code quality assessment
- **Custom Hook Plugins**: User-defined validation plugins
- **Distributed Execution**: Run hooks across multiple machines
- **Real-time Monitoring**: Live hook execution dashboard
- **Smart Caching**: Intelligent result caching

### Integration Roadmap
- Kubernetes admission webhooks
- Terraform validation hooks
- Docker build hooks
- Cloud provider integrations
- IDE plugin support

---

For detailed implementation and customization, refer to the individual hook scripts and the CLAUDE.md documentation in this directory.