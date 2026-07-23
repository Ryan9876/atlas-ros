#!/bin/bash
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Atlas Capture
# @raycast.mode compact
# @raycast.argument1 { "type": "text", "placeholder": "What would you like Atlas to capture?" }
# @raycast.argument2 { "type": "text", "placeholder": "Due date (optional)", "optional": true }
# @raycast.argument3 { "type": "text", "placeholder": "Delegate to (optional)", "optional": true }
# @raycast.argument4 { "type": "text", "placeholder": "Additional context (optional)", "optional": true }
exec atlas capture "$1" \
  --source raycast \
  --due-date "${2:-}" \
  --delegate-to "${3:-}" \
  --context "${4:-}"
