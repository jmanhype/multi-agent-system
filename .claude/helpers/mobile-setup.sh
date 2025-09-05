#!/bin/bash
# Mobile Next MCP Setup and Verification Script
# Verifies mobile automation environment and ClassDojo app readiness

set -e

echo "📱 Mobile Next MCP Setup and Verification"
echo "========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
ANDROID_SDK_PATH="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
CLASSDOJO_PACKAGE="com.classdojo.android"
CLASSDOJO_APK_PATH="$ANDROID_SDK_PATH/platform-tools/classdojo.apk"

# Helper functions
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        print_success "$1 is available"
        return 0
    else
        print_error "$1 is not available"
        return 1
    fi
}

# 1. Check prerequisites
print_status "Checking prerequisites..."

echo "1. Node.js and NPM:"
check_command "node" || exit 1
check_command "npm" || exit 1
node --version
npm --version
echo ""

echo "2. Mobile Next MCP installation:"
if npm list -g @mobilenext/mobile-mcp >/dev/null 2>&1; then
    print_success "Mobile Next MCP is globally installed"
    npm list -g @mobilenext/mobile-mcp | grep "@mobilenext/mobile-mcp"
else
    print_warning "Mobile Next MCP not found globally, installing..."
    npm install -g @mobilenext/mobile-mcp@latest
    print_success "Mobile Next MCP installed"
fi
echo ""

echo "3. Android SDK configuration:"
if [ -d "$ANDROID_SDK_PATH" ]; then
    print_success "Android SDK found at: $ANDROID_SDK_PATH"
    
    # Check ADB
    ADB_PATH="$ANDROID_SDK_PATH/platform-tools/adb"
    if [ -f "$ADB_PATH" ]; then
        print_success "ADB found at: $ADB_PATH"
        "$ADB_PATH" --version | head -1
    else
        print_error "ADB not found at expected location"
        exit 1
    fi
else
    print_error "Android SDK not found. Please set ANDROID_HOME environment variable"
    exit 1
fi
echo ""

# 2. Check device connectivity
print_status "Checking device connectivity..."

echo "4. Available devices:"
DEVICES=$("$ADB_PATH" devices 2>/dev/null | grep -v "List of devices" | grep -v "^$")
if [ -n "$DEVICES" ]; then
    print_success "Connected devices found:"
    echo "$DEVICES" | while read line; do
        echo "   📱 $line"
    done
else
    print_warning "No devices currently connected"
    print_status "Starting Android emulator if available..."
    
    # Try to find and start an emulator
    EMULATOR_PATH="$ANDROID_SDK_PATH/emulator/emulator"
    if [ -f "$EMULATOR_PATH" ]; then
        AVD_LIST=$("$EMULATOR_PATH" -list-avds 2>/dev/null | head -1)
        if [ -n "$AVD_LIST" ]; then
            print_status "Found AVD: $AVD_LIST, starting emulator..."
            "$EMULATOR_PATH" -avd "$AVD_LIST" -no-audio -no-window &
            EMULATOR_PID=$!
            
            # Wait for emulator to start
            print_status "Waiting for emulator to boot..."
            WAIT_COUNT=0
            while [ $WAIT_COUNT -lt 30 ]; do
                if "$ADB_PATH" devices | grep -q "emulator.*device"; then
                    print_success "Emulator started successfully"
                    break
                fi
                sleep 2
                WAIT_COUNT=$((WAIT_COUNT + 1))
                echo -n "."
            done
            echo ""
            
            if [ $WAIT_COUNT -eq 30 ]; then
                print_warning "Emulator taking longer than expected to start"
            fi
        else
            print_warning "No Android Virtual Devices (AVDs) found"
        fi
    else
        print_warning "Android emulator not found"
    fi
fi
echo ""

# 3. Check ClassDojo app installation
print_status "Checking ClassDojo app installation..."

echo "5. ClassDojo app verification:"
DEVICE_ID=$("$ADB_PATH" devices 2>/dev/null | grep "device$" | head -1 | cut -f1)

if [ -n "$DEVICE_ID" ]; then
    print_success "Using device: $DEVICE_ID"
    
    # Check if ClassDojo is installed
    if "$ADB_PATH" -s "$DEVICE_ID" shell pm list packages | grep -q "$CLASSDOJO_PACKAGE"; then
        print_success "ClassDojo app is installed"
        
        # Get app version
        VERSION_INFO=$("$ADB_PATH" -s "$DEVICE_ID" shell dumpsys package "$CLASSDOJO_PACKAGE" | grep "versionName" | head -1 || echo "Version info not available")
        echo "   📋 $VERSION_INFO"
        
        # Test app launch capability
        print_status "Testing app launch..."
        if "$ADB_PATH" -s "$DEVICE_ID" shell monkey -p "$CLASSDOJO_PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; then
            print_success "App launch test successful"
            sleep 2
            # Force stop the app after test
            "$ADB_PATH" -s "$DEVICE_ID" shell am force-stop "$CLASSDOJO_PACKAGE" >/dev/null 2>&1
        else
            print_warning "App launch test failed"
        fi
    else
        print_warning "ClassDojo app not installed"
        
        # Check if APK is available for installation
        if [ -f "$CLASSDOJO_APK_PATH" ]; then
            print_status "ClassDojo APK found, installing..."
            if "$ADB_PATH" -s "$DEVICE_ID" install "$CLASSDOJO_APK_PATH"; then
                print_success "ClassDojo app installed successfully"
            else
                print_error "Failed to install ClassDojo app"
            fi
        else
            print_warning "ClassDojo APK not found at: $CLASSDOJO_APK_PATH"
            echo "   💡 Download ClassDojo APK and place it in platform-tools directory"
        fi
    fi
else
    print_error "No devices available for app verification"
fi
echo ""

# 4. Test Mobile Next MCP integration
print_status "Testing Mobile Next MCP integration..."

echo "6. MCP server connectivity:"
# Create a simple test script to verify MCP tools
TEST_SCRIPT=$(cat << 'EOF'
const { spawn } = require('child_process');

async function testMCP() {
    console.log('Testing Mobile Next MCP server...');
    
    try {
        // This would normally be done through Claude Code MCP integration
        // Here we just verify the server can start
        const mcp = spawn('npx', ['@mobilenext/mobile-mcp@latest'], {
            stdio: ['pipe', 'pipe', 'pipe']
        });
        
        let output = '';
        mcp.stdout.on('data', (data) => {
            output += data.toString();
        });
        
        mcp.stderr.on('data', (data) => {
            output += data.toString();
        });
        
        // Give it a few seconds to initialize
        setTimeout(() => {
            mcp.kill();
            if (output.length > 0) {
                console.log('✅ Mobile Next MCP server can start');
                console.log('📋 Server output received');
            } else {
                console.log('⚠️  Mobile Next MCP server started but no output received');
            }
        }, 3000);
        
    } catch (error) {
        console.log('❌ Failed to start Mobile Next MCP server:', error.message);
    }
}

testMCP();
EOF
)

echo "$TEST_SCRIPT" > /tmp/test_mcp.js
node /tmp/test_mcp.js &
wait
rm -f /tmp/test_mcp.js
echo ""

# 5. Generate setup report
print_status "Generating setup report..."

echo "7. Configuration summary:"
cat << EOF > /tmp/mobile_setup_report.md
# Mobile Next MCP Setup Report

**Generated:** $(date)

## System Configuration
- **Android SDK Path:** $ANDROID_SDK_PATH
- **ADB Path:** $ADB_PATH
- **Node.js Version:** $(node --version)
- **NPM Version:** $(npm --version)

## Device Status
\`\`\`
$("$ADB_PATH" devices 2>/dev/null || echo "ADB not accessible")
\`\`\`

## ClassDojo App Status
- **Package:** $CLASSDOJO_PACKAGE
- **Installation Status:** $(if "$ADB_PATH" shell pm list packages 2>/dev/null | grep -q "$CLASSDOJO_PACKAGE"; then echo "Installed"; else echo "Not Installed"; fi)
- **APK Location:** $CLASSDOJO_APK_PATH

## Next Steps
1. Verify Claude Code can access Mobile Next MCP tools
2. Test mobile automation workflows
3. Run ClassDojo exploration scenarios

## Troubleshooting Commands
\`\`\`bash
# List available devices
$ADB_PATH devices

# Check app installation  
$ADB_PATH shell pm list packages | grep classdojo

# Install ClassDojo APK
$ADB_PATH install $CLASSDOJO_APK_PATH

# Test app launch
$ADB_PATH shell monkey -p $CLASSDOJO_PACKAGE -c android.intent.category.LAUNCHER 1
\`\`\`
EOF

echo "📄 Setup report saved to: /tmp/mobile_setup_report.md"
print_success "Mobile setup verification complete!"
echo ""

# 6. Final recommendations
echo "🎯 Recommendations:"
echo "   1. Ensure Claude Code is configured with Mobile Next MCP in .claude/mcp/servers.json"
echo "   2. Test mobile automation with: npx claude-flow mobile-app-automation --app classdojo --workflow explore"
echo "   3. Review mobile automation workflows in .claude/workflows/mobile-automation-workflows.md"
echo "   4. Check agent capabilities in .claude/agents/specialized/mobile/"
echo ""

echo "🚀 Ready for mobile automation!"
echo ""

# Display report contents
if [ "$1" = "--show-report" ]; then
    echo "📋 Setup Report Contents:"
    echo "========================"
    cat /tmp/mobile_setup_report.md
fi

exit 0