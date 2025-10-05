# Smart Automation System

## Overview

The Smart Automation System is a restructured AI-powered automation platform that intelligently detects user patterns and creates automated workflows. The system is divided into three main components:

1. **Action Registry** - Central storage for all user actions
2. **Short-Term Pattern Detection** - Detects patterns in actions from the last 10-20 seconds
3. **Long-Term Pattern Detection** - (Coming Soon) Analyzes patterns over days/weeks

## Architecture

### Backend Components

#### 1. Action Registry (`backend/src/action_registry.py`)

The Action Registry is the central hub that stores all user actions across the system.

**Features:**
- Stores up to 1000 actions with automatic cleanup
- Supports filtering by timestamp, action type, and source
- Persists data to `data/action_registry.json`
- Provides statistics and analytics on stored actions

**Key Methods:**
- `register_action(action_type, details, source, metadata)` - Register a new action
- `get_recent_actions(seconds)` - Get actions from last N seconds
- `get_action_stats()` - Get statistics about stored actions

#### 2. Short-Term Pattern Agent (`backend/src/agents/short_term_pattern_agent.py`)

Detects patterns in user actions within a 10-20 second window.

**Features:**
- Analyzes recent user actions for repetitive patterns
- Uses AI to identify automation opportunities
- Implements cooldown mechanism to avoid spam (30 seconds between detections)
- Filters out system-generated actions

**Detection Criteria:**
- Repetitive actions (e.g., renaming multiple files)
- Similar operations (e.g., creating files with similar names)
- Sequential workflows (e.g., create, move, rename sequence)

#### 3. Long-Term Pattern Agent (`backend/src/agents/long_term_pattern_agent.py`)

**Status:** Coming Soon

**Planned Features:**
- Daily/weekly routine detection
- Recurring workflow identification
- Proactive automation suggestions
- Historical pattern learning
- Time-based automation triggers

#### 4. Automation Executor (`backend/src/automation_executor.py`)

Handles the complete automation execution lifecycle.

**Features:**
- Generates Python scripts from user descriptions
- Automatically installs required libraries using pip
- Executes scripts with retry logic (up to 3 attempts)
- Cleans up temporary script files after successful execution
- Comprehensive error handling and logging

**Execution Flow:**
1. Extract required libraries from script
2. Install libraries if needed
3. Execute script (with 60-second timeout)
4. Retry up to 3 times on failure
5. Delete temporary script file on success

### Backend API Endpoints

#### Action Registry Endpoints
- `GET /automation/action-registry/stats` - Get action statistics
- `GET /automation/action-registry/recent?seconds=60` - Get recent actions

#### Automation Workflow Endpoints
- `GET /automation/pending-suggestions` - Get pending automation suggestions
- `POST /automation/suggestion/{id}/accept` - Accept a suggestion
- `POST /automation/suggestion/{id}/reject` - Reject a suggestion
- `POST /automation/suggestion/{id}/explain` - Provide explanation and generate script
- `POST /automation/suggestion/{id}/confirm-and-execute` - Execute the automation
- `GET /automation/suggestions/all` - Get all suggestions (history)

#### Long-Term Pattern Endpoint
- `GET /automation/long-term/status` - Check long-term detection status

### Frontend Components

#### 1. AutomationSuggestionPopup (`frontend/src/components/AutomationSuggestionPopup.js`)

A global popup that appears when a pattern is detected.

**User Flow:**
1. **Pattern Detected** - Popup appears with description
2. **User Decision** - User clicks "Yes, automate!" or "No, thanks"
3. **Explanation** - User explains what they want to automate
4. **Script Generation** - AI generates Python script based on explanation
5. **Review & Execute** - User reviews script and confirms execution

**Features:**
- Non-intrusive bottom-right popup
- Beautiful gradient design with animations
- Multi-step modal workflow
- Real-time polling for new suggestions (every 5 seconds)

#### 2. SmartAutomation (`frontend/src/components/SmartAutomation.js`)

Dashboard view for the three-part automation system.

**Sections:**

**Action Registry Card:**
- Total actions count
- Action type breakdown
- Source breakdown

**Short-Term Patterns Card:**
- Total suggestions count
- Completed vs pending statistics
- Active monitoring indicator

**Long-Term Patterns Card:**
- Coming soon status
- Planned features list

**Automation History:**
- Complete list of all automation suggestions
- Status badges (pending, accepted, completed, failed, etc.)
- Execution details and results

## User Workflow

### Complete Automation Flow

1. **User performs actions** (e.g., renaming 2-3 files)
   - Actions are detected by file watcher
   - Registered in Action Registry

2. **Pattern detection** (runs every 10 seconds)
   - Short-term agent analyzes last 20 seconds of actions
   - If pattern detected, creates suggestion

3. **Popup appears**
   - Shows pattern description
   - User clicks "Yes, automate!"

4. **Explanation modal**
   - User types what they want: "Rename all images to image_001.jpg, image_002.jpg, etc."
   - Clicks "Generate Script"

5. **Script generation**
   - AI combines pattern + user explanation
   - Generates Python automation script
   - Shows script in review modal

6. **Script execution**
   - User reviews and clicks "Execute Script"
   - System installs required libraries
   - Executes with retry logic (up to 3 attempts)
   - Cleans up temporary files

7. **Result**
   - Success: Shows success message
   - Failure: Shows error details after 3 attempts

## Configuration

The system uses the existing `backend/config.yaml`:

```yaml
watch:
  dirs:
    - C:\Users\user\Desktop
    - C:\Users\user\Downloads
  pattern_interval_seconds: 60  # Pattern detection frequency
```

## Data Persistence

The system persists data in the following locations:

- `data/action_registry.json` - All registered actions
- `data/ai_interactions.json` - AI interaction logs
- Temporary script files are created in system temp directory and deleted after execution

## Background Threads

The backend runs several background threads:

1. **File Watcher Thread** - Monitors configured directories
2. **Pattern Detection Thread** - Original pattern detection (runs every 60s)
3. **Short-Term Detection Thread** - New short-term pattern detection (runs every 10s)
4. **Periodic Save Thread** - Saves data every 30 seconds

## Security

**Script Execution Safety:**
- Scripts run with limited module access
- 60-second timeout per execution
- Sandboxed execution environment
- Library installation via pip (standard packages only)

## Development Notes

### Testing the System

1. **Test Short-Term Detection:**
   - Rename 2-3 files quickly in a watched directory
   - Wait 10-20 seconds
   - Popup should appear

2. **Test Full Workflow:**
   - Accept suggestion
   - Provide explanation
   - Review generated script
   - Execute and verify results

### Adding New Action Sources

To register actions from new sources:

```python
from backend.src.action_registry import ActionRegistry

# Register an action
action_registry.register_action(
    action_type="email_action",
    details={
        "action": "sent_email",
        "recipient": "user@example.com"
    },
    source="email_client",
    metadata={"category": "communication"}
)
```

## Future Enhancements

### Long-Term Pattern Detection (Planned)
- Analyze patterns over days/weeks
- Detect recurring routines
- Suggest proactive automations
- Machine learning for pattern recognition

### Additional Features (Ideas)
- Pattern templates library
- Shared automation scripts
- Voice-activated automation
- Integration with more applications
- Cloud sync for patterns

## Troubleshooting

**Issue: Popup not appearing**
- Check backend logs for pattern detection
- Verify file watcher is running
- Ensure Gemini API key is configured

**Issue: Script execution fails**
- Check execution logs in automation history
- Verify required libraries can be installed
- Review error messages in UI

**Issue: Actions not being registered**
- Check file watcher configuration
- Verify watched directories exist
- Check action registry stats

## API Integration Guide

### Frontend Usage

```javascript
// Get pending suggestions
const suggestions = await window.electronAPI.getPendingSuggestions();

// Accept a suggestion
await window.electronAPI.acceptSuggestion(suggestionId);

// Provide explanation
await window.electronAPI.provideExplanation(suggestionId, "Rename all PDFs");

// Execute automation
await window.electronAPI.confirmAndExecute(suggestionId);
```

## Summary

The Smart Automation System provides an intelligent, user-friendly way to automate repetitive tasks. By combining real-time pattern detection, natural language processing, and automatic script generation, it reduces manual work and increases productivity.

The three-part architecture ensures:
- **Comprehensive tracking** via Action Registry
- **Immediate automation** via Short-Term Detection
- **Future intelligence** via Long-Term Detection (coming soon)

All while maintaining a clean, intuitive user interface and robust error handling.

