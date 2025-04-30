
#!/bin/bash

###############################################################################
# GitHub Monitoring Script v4.0
# 
# This script monitors GitHub for new activity and outputs it to stdout.
# It supports monitoring:
#   1. New comments on a specific issue (by anyone or specific users)
#   2. New issues in a repository (by anyone or specific users)
#   3. Filtering by labels
#
# Use cases:
#   - Monitor issues for comments from maintainers
#   - Watch for new issues matching criteria
#   - Integrate with other scripts/agents to take actions based on GitHub activity
#
# Usage:
#   ./monitor_issue.sh --mode <MODE> --repo <OWNER/REPO> [options]
#
# Examples:
#   Monitor issue comments:
#     ./monitor_issue.sh --mode issue-comments --repo irthomasthomas/llm-consortium --issue 9 --user irthomasthomas
#
#   Monitor new issues:
#     ./monitor_issue.sh --mode new-issues --repo irthomasthomas/llm-consortium --user irthomasthomas --label "bug"
#
#   Run in background (detached):
#     ./monitor_issue.sh --mode new-issues --repo irthomasthomas/llm-consortium --background
#
#   Spawn a sub-agent to monitor a different repo:
#     ./monitor_issue.sh --spawn-agent "Monitor new issues in different repo" \
#       --mode new-issues --repo octocat/hello-world --user octocat
###############################################################################

# Configuration Defaults
POLL_INTERVAL=15        # seconds between checks
FETCH_COUNT=100         # max items to fetch per poll
DEBUG=false             # debug output toggle
BACKGROUND=false        # run in background
SPAWN_ARGS=""           # arguments for spawning agents

# Variables to be set by arguments
MODE=""
REPO=""
ISSUE_NUM=""
TARGET_USER=""
LABEL=""
AGENT_INSTRUCTIONS=""
MONITOR_OUTPUT_FILE=""

# Function to display help/usage information
show_help() {
    cat << EOF
GitHub Monitoring Script v4.0

USAGE:
    ./monitor_issue.sh --mode <MODE> --repo <OWNER/REPO> [options]

MODES:
    issue-comments    Monitor comments on a specific issue
    new-issues        Monitor new issues in a repository

REQUIRED ARGUMENTS:
    --mode MODE       Monitoring mode (issue-comments or new-issues)
    --repo OWNER/REPO GitHub repository in the format owner/repo

MODE-SPECIFIC REQUIRED ARGUMENTS:
    For --mode issue-comments:
        --issue NUM   Issue number to monitor

OPTIONAL ARGUMENTS:
    --user USERNAME   Only show items from this GitHub username
    --label LABEL     Only show issues with this label (only for new-issues mode)
    --interval SEC    Polling interval in seconds (default: 15)
    --count NUM       Maximum number of items to fetch per poll (default: 100)
    --debug           Enable verbose debug output
    --background      Run in background (detached process)
    --output FILE     Write output to file instead of stdout (useful with --background)

ADVANCED USAGE:
    --spawn-agent "INSTRUCTIONS"  Spawn a new agent with the given instructions
                                  (all subsequent args will be passed to the agent)

EXAMPLES:
    ./monitor_issue.sh --mode issue-comments --repo irthomasthomas/llm-consortium --issue 9 --user irthomasthomas
    ./monitor_issue.sh --mode new-issues --repo irthomasthomas/llm-consortium --user irthomasthomas --label "bug"
    ./monitor_issue.sh --mode new-issues --repo irthomasthomas/llm-consortium --background --output /tmp/gh-monitor.log
EOF
    exit 0
}

debug_log() {
    if [ "$DEBUG" = true ]; then
        echo "[DEBUG] $*" >&2
    fi
}

error_log() {
    echo "[ERROR] $*" >&2
}

info_log() {
    echo "[INFO] $*" >&2
}

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    error_log "GitHub CLI (gh) is not installed or not in PATH. Please install it: https://cli.github.com/manual/installation"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    error_log "jq is not installed or not in PATH. Please install it: https://stedolan.github.io/jq/download/"
    exit 1
fi

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            ;;
        --mode)
            MODE="$2"
            shift
            ;;
        --repo)
            REPO="$2"
            shift
            ;;
        --issue)
            ISSUE_NUM="$2"
            shift
            ;;
        --user)
            TARGET_USER="$2"
            shift
            ;;
        --label)
            LABEL="$2"
            shift
            ;;
        --interval)
            POLL_INTERVAL="$2"
            shift
            ;;
        --count)
            FETCH_COUNT="$2"
            shift
            ;;
        --debug)
            DEBUG=true
            ;;
        --background)
            BACKGROUND=true
            ;;
        --output)
            MONITOR_OUTPUT_FILE="$2"
            shift
            ;;
        --spawn-agent)
            AGENT_INSTRUCTIONS="$2"
            shift
            
            # All remaining arguments will be passed to the spawned agent
            SPAWN_ARGS="$*"
            break
            ;;
        *)
            error_log "Unknown parameter passed: $1"
            echo "Use --help for usage information." >&2
            exit 1
            ;;
    esac
    shift
done

# Handle agent spawning if requested
if [[ -n "$AGENT_INSTRUCTIONS" ]]; then
    # This is where we would integrate with an agent spawning system
    # For now, we'll use a basic approach to start a new monitoring script
    
    info_log "Spawning a new monitoring agent with instructions: $AGENT_INSTRUCTIONS"
    info_log "Agent arguments: $SPAWN_ARGS"
    
    # If there's a known agent spawning command available:
    # eval "$AGENT_CMD \"$AGENT_INSTRUCTIONS\" $SPAWN_ARGS"
    
    # Alternative: Start a new monitoring script instance
    if command -v nohup &> /dev/null; then
        info_log "Starting agent using nohup in background..."
        nohup ./monitor_issue.sh $SPAWN_ARGS &> /tmp/monitor_agent_$$.log &
        echo "Agent started with PID $!"
    else
        info_log "Starting agent in background..."
        ./monitor_issue.sh $SPAWN_ARGS &
    fi
    
    exit 0
fi

# Run in background if requested
if [ "$BACKGROUND" = true ]; then
    if [ -z "$MONITOR_OUTPUT_FILE" ]; then
        MONITOR_OUTPUT_FILE="/tmp/gh_monitor_${REPO//\//_}_$$.log"
    fi
    
    info_log "Running in background. Output will be written to: $MONITOR_OUTPUT_FILE"
    info_log "To stop the monitoring, find the process ID and kill it: ps aux | grep monitor_issue"
    
    # Restart with nohup in the background
    nohup "$0" --mode "$MODE" --repo "$REPO" \
         ${ISSUE_NUM:+--issue "$ISSUE_NUM"} \
         ${TARGET_USER:+--user "$TARGET_USER"} \
         ${LABEL:+--label "$LABEL"} \
         --interval "$POLL_INTERVAL" \
         --count "$FETCH_COUNT" \
         ${DEBUG:+--debug} \
         --output "$MONITOR_OUTPUT_FILE" > /dev/null 2>&1 &
    
    echo "Background monitoring started with PID $!"
    exit 0
fi

# Handle output redirection if specified
if [ -n "$MONITOR_OUTPUT_FILE" ]; then
    exec > "$MONITOR_OUTPUT_FILE"
    info_log "Output redirected to $MONITOR_OUTPUT_FILE"
fi

# Validate required arguments
if [[ -z "$MODE" ]]; then
    error_log "Error: --mode <issue-comments|new-issues> is required."
    exit 1
fi

if [[ -z "$REPO" ]]; then
    error_log "Error: --repo <owner/name> is required."
    exit 1
fi

# Validate mode-specific requirements
if [[ "$MODE" == "issue-comments" ]]; then
    if [[ -z "$ISSUE_NUM" ]]; then
        error_log "Error: --issue <NUM> is required for mode issue-comments."
        exit 1
    fi
elif [[ "$MODE" == "new-issues" ]]; then
    true # Valid mode, no additional validation needed
else
    error_log "Error: Invalid mode '$MODE'. Must be issue-comments or new-issues."
    exit 1
fi

# Validate numeric values
if ! [[ "$POLL_INTERVAL" =~ ^[0-9]+$ ]]; then
    error_log "Error: --interval must be a positive integer."
    exit 1
fi

if ! [[ "$FETCH_COUNT" =~ ^[0-9]+$ ]]; then
    error_log "Error: --count must be a positive integer."
    exit 1
fi

# Ensure fetch count is reasonable
if [[ "$FETCH_COUNT" -lt 1 || "$FETCH_COUNT" -gt 500 ]]; then
    info_log "Adjusting fetch count to reasonable limits (1-500)."
    if [[ "$FETCH_COUNT" -lt 1 ]]; then
        FETCH_COUNT=1
    elif [[ "$FETCH_COUNT" -gt 500 ]]; then
        FETCH_COUNT=500
    fi
fi

info_log "Starting GitHub monitoring with following parameters:"
info_log "  Mode: $MODE"
info_log "  Repository: $REPO"
[[ -n "$ISSUE_NUM" ]] && info_log "  Issue: $ISSUE_NUM"
[[ -n "$TARGET_USER" ]] && info_log "  User filter: $TARGET_USER"
[[ -n "$LABEL" ]] && info_log "  Label filter: $LABEL"
info_log "  Poll interval: $POLL_INTERVAL seconds"
info_log "  Fetch count: $FETCH_COUNT items maximum"

# --- Initial State Determination ---
# Get marker for the latest processed item
last_processed_marker=""

if [[ "$MODE" == "issue-comments" ]]; then
    debug_log "Mode: issue-comments. Repo: $REPO Issue: $ISSUE_NUM. User: $TARGET_USER. Label: $LABEL"
    
    # Get the ID of the absolute latest comment initially
    debug_log "Fetching initial LATEST comment ID..."
    last_processed_marker=$(gh issue view "$ISSUE_NUM" --repo "$REPO" --json comments --jq '.comments[-1].id? // "0"' 2>/dev/null || echo "0")

    if [[ "$last_processed_marker" == "0" ]]; then
        info_log "No comments found on issue $REPO#$ISSUE_NUM or error fetching. Will monitor for first comment"
        [[ -n "$TARGET_USER" ]] && info_log "from '$TARGET_USER'."
    else
        debug_log "Initial latest comment ID (any user): $last_processed_marker"
    fi

elif [[ "$MODE" == "new-issues" ]]; then
    debug_log "Mode: new-issues. Repo: $REPO. User: $TARGET_USER. Label: $LABEL"
    
    # Get the creation timestamp of the absolute latest issue initially
    label_filter_arg=""
    if [[ -n "$LABEL" ]]; then
        label_filter_arg="--label $LABEL"
    fi
    
    debug_log "Fetching initial LATEST issue created_at timestamp..."
    last_processed_marker=$(gh issue list --repo "$REPO" $label_filter_arg --state open --json number,createdAt --limit 1 --jq '.[0].createdAt? // "1970-01-01T00:00:00Z"' 2>/dev/null || echo "1970-01-01T00:00:00Z")

    if [[ "$last_processed_marker" == "1970-01-01T00:00:00Z" ]]; then
        info_log "No recent open issues matching criteria found for $REPO. Will monitor for the first."
    else
        debug_log "Initial latest issue created_at (any user): $last_processed_marker"
    fi
fi

info_log "Monitoring will begin for new items"
[[ -n "$TARGET_USER" ]] && info_log "from '$TARGET_USER'"
info_log "newer than marker: $last_processed_marker"
info_log "Press Ctrl+C to stop monitoring."

# --- Monitoring Loop ---
while true; do
    new_item_body="" # Variable to hold the body of the new item found
    latest_item_marker_found_in_loop="" # Marker of the newest item found in this loop iteration

    if [[ "$MODE" == "issue-comments" ]]; then
        debug_log "Loop: Fetching latest $FETCH_COUNT comments on $REPO#$ISSUE_NUM..."
        items_json=$(gh issue view "$ISSUE_NUM" --repo "$REPO" --json comments --jq ".comments | reverse | .[:$FETCH_COUNT]" 2>/dev/null)

        if ! echo "$items_json" | jq -e '. | type == "array"' > /dev/null; then
            error_log "Failed to fetch comments or invalid JSON. Retrying in $POLL_INTERVAL seconds..."
            sleep "$POLL_INTERVAL"
            continue
        fi
        
        comment_count=$(echo "$items_json" | jq 'length')
        debug_log "Comments fetched successfully ($comment_count items). Processing..."

        debug_log "Filtering for new comments"
        [[ -n "$TARGET_USER" ]] && debug_log "from '$TARGET_USER'"
        debug_log "newer than ID '$last_processed_marker'..."
        
        # Process comments using jq: Filter for user, filter for newer ID, select first (newest), output body and ID
        jq_result=$(echo "$items_json" | jq -r --arg last_marker "$last_processed_marker" --arg user "$TARGET_USER" '
            # Filter by user if specified, otherwise match any user
            (if $user == "" then . else map(select(.author.login == $user)) end) |
            # Filter for items with an ID lexicographically greater than the last processed marker
            map(select(.id > $last_marker)) |
            # Get the *newest* item from the filtered list (which is the first due to reverse sort)
            first |
            # Output the body and the ID, separated by a delimiter, if an item was found
            if . then 
              "---ITEM-AUTHOR---\(.author.login)\n---ITEM-CREATED---\(.createdAt)\n---ITEM-URL---\(.url)\n---ITEM-BODY-START---\n\(.body? // "")\n---ITEM-BODY-END---\n---ITEM-MARKER---\(.id)"
            else 
              "" 
            end
        ')

        if [[ -n "$jq_result" ]]; then
            # Extract the author
            item_author=$(echo "$jq_result" | sed -n 's/---ITEM-AUTHOR---\(.*\)/\1/p')
            
            # Extract the creation date
            item_created=$(echo "$jq_result" | sed -n 's/---ITEM-CREATED---\(.*\)/\1/p')
            
            # Extract the URL
            item_url=$(echo "$jq_result" | sed -n 's/---ITEM-URL---\(.*\)/\1/p')
            
            # Extract the body
            new_item_body=$(echo "$jq_result" | sed -n '/---ITEM-BODY-START---/,/---ITEM-BODY-END---/ { /---ITEM-BODY-START---/d; /---ITEM-BODY-END---/d; p }')
            
            # Extract the marker
            latest_item_marker_found_in_loop=$(echo "$jq_result" | sed -n 's/---ITEM-MARKER---\(.*\)/\1/p')
        fi

    elif [[ "$MODE" == "new-issues" ]]; then
        debug_log "Loop: Fetching latest $FETCH_COUNT open issues in $REPO"
        [[ -n "$LABEL" ]] && debug_log "with label '$LABEL'"
        [[ -n "$TARGET_USER" ]] && debug_log "by user '$TARGET_USER'"
        
        label_filter_arg=""
        if [[ -n "$LABEL" ]]; then
            label_filter_arg="--label $LABEL"
        fi
        
        # Fetch issues, sorted newest first
        items_json=$(gh issue list --repo "$REPO" $label_filter_arg --state open --json number,title,body,author,url,createdAt --limit $FETCH_COUNT --jq '.' 2>/dev/null)

        if ! echo "$items_json" | jq -e '. | type == "array"' > /dev/null; then
            error_log "Failed to fetch issues or invalid JSON. Retrying in $POLL_INTERVAL seconds..."
            sleep "$POLL_INTERVAL"
            continue
        fi
        
        issue_count=$(echo "$items_json" | jq 'length')
        debug_log "Issues fetched successfully ($issue_count items). Processing..."

        debug_log "Filtering for new issues"
        [[ -n "$TARGET_USER" ]] && debug_log "from '$TARGET_USER'"
        debug_log "newer than timestamp '$last_processed_marker'..."
        
        # Process issues using jq: Filter for timestamp, filter for user (optional), select first, output body and timestamp
        jq_result=$(echo "$items_json" | jq -r --arg last_marker "$last_processed_marker" --arg user "$TARGET_USER" '
            # Filter for issues with creation timestamp > last processed marker
            map(select(.createdAt > $last_marker)) |
            # Filter by user if specified
            (if $user == "" then . else map(select(.author.login == $user)) end) |
            # Get the *newest* issue from the filtered list (which is the first)
            first |
            # Output the formatted issue data and the marker (created timestamp), separated by delimiters
            if . then 
              "---ITEM-NUMBER---\(.number)\n---ITEM-TITLE---\(.title)\n---ITEM-AUTHOR---\(.author.login)\n---ITEM-CREATED---\(.createdAt)\n---ITEM-URL---\(.url)\n---ITEM-BODY-START---\n\(.body? // "")\n---ITEM-BODY-END---\n---ITEM-MARKER---\(.createdAt)"
            else 
              "" 
            end
        ')

        if [[ -n "$jq_result" ]]; then
            # Extract the issue number
            item_number=$(echo "$jq_result" | sed -n 's/---ITEM-NUMBER---\(.*\)/\1/p')
            
            # Extract the title
            item_title=$(echo "$jq_result" | sed -n 's/---ITEM-TITLE---\(.*\)/\1/p')
            
            # Extract the author
            item_author=$(echo "$jq_result" | sed -n 's/---ITEM-AUTHOR---\(.*\)/\1/p')
            
            # Extract the creation date
            item_created=$(echo "$jq_result" | sed -n 's/---ITEM-CREATED---\(.*\)/\1/p')
            
            # Extract the URL
            item_url=$(echo "$jq_result" | sed -n 's/---ITEM-URL---\(.*\)/\1/p')
            
            # Extract the body
            item_body=$(echo "$jq_result" | sed -n '/---ITEM-BODY-START---/,/---ITEM-BODY-END---/ { /---ITEM-BODY-START---/d; /---ITEM-BODY-END---/d; p }')
            
            # Format the new item body for output
            new_item_body="# Issue #${item_number}: ${item_title}

${item_body}"
            
            # Extract the marker
            latest_item_marker_found_in_loop=$(echo "$jq_result" | sed -n 's/---ITEM-MARKER---\(.*\)/\1/p')
        fi
    fi # End of MODE check

    # Check if a new item body was found AND a valid marker was extracted
    if [[ -n "$new_item_body" && -n "$latest_item_marker_found_in_loop" ]]; then
        info_log "New item found! Outputting and updating marker..."
        
        # Update the last_processed_marker to the marker of the item we just found
        # This prevents re-detecting the same item if the script is restarted
        last_processed_marker="$latest_item_marker_found_in_loop"
        debug_log "Updated last_processed_marker internally to: $last_processed_marker"

        if [[ "$MODE" == "issue-comments" ]]; then
            info_log "New comment by ${item_author} on issue #${ISSUE_NUM} (${item_created}):"
            info_log "URL: ${item_url}"
        elif [[ "$MODE" == "new-issues" ]]; then
            info_log "New issue #${item_number}: '${item_title}' by ${item_author} (${item_created}):"
            info_log "URL: ${item_url}"
        fi
        
        echo "--- NEW ITEM ---" >&2 # Separator on stderr
        echo "$new_item_body" # Output item body to stdout
        exit 0 # Exit successfully after finding and outputting an item
    fi

    # No new relevant item found, wait before polling again
    debug_log "No new relevant items found. Sleeping for $POLL_INTERVAL seconds..."
    sleep "$POLL_INTERVAL"
done
