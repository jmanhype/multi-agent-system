#!/bin/bash
# Verification gate hook for Claude Code
# Blocks execution if truth score < 0.95

set -e

echo "🔒 Running verification gate..."

# Check for registry and truth scores
if [ -f "registry/index.ndjson" ]; then
    echo "📋 Registry found, checking truth scores..."
    
    # Extract latest truth.score from NDJSON
    if command -v jq &> /dev/null; then
        latest_score=$(tail -n 1 registry/index.ndjson 2>/dev/null | jq -r '.truth.score // 0' 2>/dev/null || echo "0")
    else
        # Fallback without jq - basic parsing
        latest_score=$(tail -n 1 registry/index.ndjson 2>/dev/null | grep -o '"score":[0-9.]*' | head -1 | cut -d: -f2 || echo "0")
    fi
    
    echo "📊 Latest truth score: $latest_score"
    
    # Verify score format
    if [[ ! "$latest_score" =~ ^[0-9]*\.?[0-9]+$ ]]; then
        echo "⚠️  Invalid score format, defaulting to 0"
        latest_score="0"
    fi
    
    # Check threshold (0.95)
    threshold="0.95"
    
    # Compare using awk (more portable than bc)
    if awk -v score="$latest_score" -v thresh="$threshold" 'BEGIN { exit (score < thresh) }'; then
        echo "✅ Truth score ($latest_score) meets threshold ($threshold)"
    else
        echo "❌ Truth score ($latest_score) below threshold ($threshold)"
        echo "🚫 Blocking execution - verification failed"
        echo ""
        echo "Recommendations:"
        echo "1. Review recent changes for accuracy"
        echo "2. Run additional validation tests"
        echo "3. Update documentation if needed"
        echo "4. Consider peer review"
        exit 1
    fi
    
elif [ -f "platform/policy/verify.json" ]; then
    echo "📋 Policy verification file found, checking..."
    
    if command -v jq &> /dev/null; then
        policy_score=$(jq -r '.verification.score // 0' platform/policy/verify.json 2>/dev/null || echo "0")
        echo "📊 Policy verification score: $policy_score"
        
        if awk -v score="$policy_score" 'BEGIN { exit (score < 0.95) }'; then
            echo "✅ Policy verification passed"
        else
            echo "❌ Policy verification failed"
            exit 1
        fi
    else
        echo "⚠️  jq not available for JSON parsing, skipping policy verification"
    fi
    
else
    echo "⚠️  No registry or policy verification found"
    echo "💡 Consider running experiments to establish truth scores"
    echo "✅ Proceeding without verification (development mode)"
fi

echo "✅ Verification gate completed"