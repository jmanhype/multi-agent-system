# mobile-app-automation

Orchestrate mobile app automation workflows using Mobile Next MCP tools and specialized agents.

## Usage
```bash
npx claude-flow mobile-app-automation [options]
```

## Options
- `--app <name>` - Target mobile app (classdojo, general)
- `--workflow <type>` - Automation workflow (explore, test, parent-login, parent-signup)
- `--platform <type>` - Target platform (android, ios, both)
- `--device <name>` - Specific device name or use default
- `--agents <number>` - Number of agents for complex workflows (default: 3)
- `--output <format>` - Output format (json, markdown, report)

## Examples

### ClassDojo Parent Workflow Exploration
```bash
# Complete parent account exploration
npx claude-flow mobile-app-automation \
    --app classdojo \
    --workflow explore \
    --platform android \
    --output markdown

# Specific parent login flow
npx claude-flow mobile-app-automation \
    --app classdojo \
    --workflow parent-login \
    --platform android \
    --agents 2
```

### Generic Mobile App Testing
```bash
# Explore any mobile app
npx claude-flow mobile-app-automation \
    --app com.example.app \
    --workflow explore \
    --platform android

# Multi-platform testing
npx claude-flow mobile-app-automation \
    --app com.example.app \
    --workflow test \
    --platform both \
    --agents 4
```

### Advanced Orchestration
```bash
# Custom workflow with specific agents
npx claude-flow mobile-app-automation \
    --app classdojo \
    --workflow parent-signup \
    --platform ios \
    --agents 3 \
    --output json \
    --device "iPhone 15 Simulator"
```

## Workflow Types

### `explore`
- Launch app and discover UI elements
- Navigate through main screens
- Document user flows and interaction patterns
- Generate comprehensive app structure report

### `test` 
- Execute predefined test scenarios
- Validate UI element accessibility
- Test form inputs and navigation
- Generate test results and coverage report

### `parent-login` (ClassDojo-specific)
- Navigate to parent login screen
- Test login form elements
- Document authentication options
- Validate login workflow completeness

### `parent-signup` (ClassDojo-specific)
- Access parent registration screen
- Test signup form and options
- Document registration requirements
- Validate OAuth integration options

## Agent Coordination

The command automatically coordinates multiple specialized agents:

### Primary Agents
1. **classdojo-mobile-automation** - Main mobile interaction agent
2. **mobile-controller** - Device management and connectivity
3. **workflow-documenter** - Pattern recording and documentation

### Agent Roles
- **Device Controller**: Manages mobile device connections and app lifecycle
- **UI Explorer**: Discovers and interacts with mobile UI elements
- **Pattern Documenter**: Records workflows and generates reports
- **Quality Validator**: Ensures automation reliability and error handling

## Output Formats

### JSON Output
```json
{
  "session_id": "mobile-automation-20250905",
  "app": "classdojo",
  "workflow": "parent-login", 
  "platform": "android",
  "results": {
    "screens_discovered": ["parent_signup", "parent_login"],
    "ui_elements": {
      "parent_login": [
        {
          "type": "username_field",
          "identifier": "com.classdojo.android:id/fragment_login_et_username",
          "coordinates": {"x": 42, "y": 584, "width": 996, "height": 164}
        }
      ]
    },
    "workflows_documented": ["signup_to_login_navigation", "form_interaction"],
    "success_rate": 0.95,
    "execution_time": "4.2s"
  }
}
```

### Markdown Report
```markdown
# Mobile Automation Report: ClassDojo Parent Login

## Session Overview
- **App**: ClassDojo (com.classdojo.android)
- **Platform**: Android Emulator
- **Workflow**: Parent Login Exploration
- **Duration**: 4.2 seconds
- **Success Rate**: 95%

## Discovered Screens
1. **Parent Signup Screen**
   - Email input field identified
   - Google OAuth option available
   - Login navigation link present

2. **Parent Login Screen**  
   - Username/email field accessible
   - Password field functional
   - Authentication options documented

## Recommendations
- Implement robust error handling for network timeouts
- Add accessibility labels for better automation reliability
```

## Integration Examples

### With Zen Tools
```bash
# Combine with analysis
npx claude-flow mobile-app-automation --app classdojo --workflow explore | \
npx claude-flow zen analyze --query "Mobile UI patterns and usability"

# Generate comprehensive documentation
npx claude-flow mobile-app-automation --app classdojo --workflow explore | \
npx claude-flow zen docgen --format markdown --title "ClassDojo Mobile Automation Guide"
```

### With Task Master
```bash
# Create automation tasks from PRD
npx claude-flow task-master parse-prd --input mobile-app-requirements.md | \
npx claude-flow mobile-app-automation --workflow test --app classdojo
```

### With Swarm Coordination
```bash
# Initialize mobile automation swarm
npx claude-flow swarm init --topology mesh --max-agents 5
npx claude-flow mobile-app-automation --app classdojo --workflow explore --agents 3
```

## Configuration

### Device Selection Priority
1. Explicit `--device` parameter
2. Environment variable `MOBILE_DEFAULT_DEVICE`
3. Auto-detection of available devices
4. Mobile Next MCP default device

### Platform Detection
- **Android**: Detects emulators and connected devices
- **iOS**: Detects simulators and connected devices  
- **Both**: Runs automation on both platforms sequentially

### Error Recovery
- Automatic device reconnection on failure
- App restart on crash or hang
- Element detection retries with exponential backoff
- Session state persistence for resume capability

## Troubleshooting

### Common Issues

#### Device Not Found
```bash
# List available devices
npx claude-flow mobile-app-automation --list-devices

# Force specific device  
npx claude-flow mobile-app-automation --device "emulator-5554" --app classdojo
```

#### App Launch Failure
```bash
# Verify app installation
npx claude-flow mobile-app-automation --check-app classdojo

# Force app reinstall
npx claude-flow mobile-app-automation --install-app classdojo.apk
```

#### Element Detection Issues
```bash
# Enable debug mode for detailed element logging
npx claude-flow mobile-app-automation --debug --app classdojo --workflow explore

# Generate element hierarchy report
npx claude-flow mobile-app-automation --dump-ui --app classdojo
```

### Performance Optimization
- Use `--cache-elements` for faster repeated interactions
- Enable `--batch-operations` for multiple UI actions
- Set `--timeout` values appropriate for app loading times
- Use `--parallel-agents` for independent workflow testing

Remember: Mobile automation success depends on stable device connectivity, proper app installation, and robust error handling strategies.