# Test script for backend AI interactions
Write-Host "Testing backend AI interactions..."

# Wait for backend to start
Start-Sleep -Seconds 3

# Test debug status
Write-Host "1. Testing debug status..."
try {
    $debugResponse = Invoke-WebRequest -Uri "http://localhost:8002/debug-status" -Method GET
    $debugData = $debugResponse.Content | ConvertFrom-Json
    Write-Host "Debug Status:"
    Write-Host "  File Operations: $($debugData.file_operations_count)"
    Write-Host "  AI Interactions: $($debugData.ai_interactions_count)"
    Write-Host "  Gemini Configured: $($debugData.gemini_configured)"
    Write-Host "  Pattern Detection Running: $($debugData.pattern_detection_running)"
    Write-Host "  Agents Initialized: $($debugData.agents_initialized | ConvertTo-Json -Compress)"
} catch {
    Write-Host "Error getting debug status: $($_.Exception.Message)"
}

# Test AI interaction
Write-Host "`n2. Testing AI interaction..."
try {
    $aiResponse = Invoke-WebRequest -Uri "http://localhost:8002/test-ai-interaction" -Method POST
    $aiData = $aiResponse.Content | ConvertFrom-Json
    Write-Host "AI Interaction Test: $($aiData.message)"
    Write-Host "Total Interactions: $($aiData.total_interactions)"
} catch {
    Write-Host "Error testing AI interaction: $($_.Exception.Message)"
}

# Test pattern detection
Write-Host "`n3. Testing pattern detection..."
try {
    $patternResponse = Invoke-WebRequest -Uri "http://localhost:8002/test-pattern-detection" -Method POST
    $patternData = $patternResponse.Content | ConvertFrom-Json
    Write-Host "Pattern Detection Test: $($patternData.message)"
    Write-Host "Original Ops: $($patternData.original_ops)"
    Write-Host "Filtered Ops: $($patternData.filtered_ops)"
    Write-Host "AI Interactions After Test: $($patternData.ai_interactions)"
} catch {
    Write-Host "Error testing pattern detection: $($_.Exception.Message)"
}

# Get AI interactions
Write-Host "`n4. Getting AI interactions..."
try {
    $interactionsResponse = Invoke-WebRequest -Uri "http://localhost:8002/ai-interactions" -Method GET
    $interactionsData = $interactionsResponse.Content | ConvertFrom-Json
    Write-Host "Total AI Interactions: $($interactionsData.interactions.Count)"
    if ($interactionsData.interactions.Count -gt 0) {
        Write-Host "Latest Interaction:"
        $latest = $interactionsData.interactions[0]
        Write-Host "  Agent: $($latest.agent)"
        Write-Host "  Prompt: $($latest.prompt.Substring(0, [Math]::Min(50, $latest.prompt.Length)))..."
        Write-Host "  Response: $($latest.response.Substring(0, [Math]::Min(50, $latest.response.Length)))..."
        Write-Host "  Timestamp: $($latest.timestamp)"
    }
} catch {
    Write-Host "Error getting AI interactions: $($_.Exception.Message)"
}

Write-Host "`nTest completed!"

