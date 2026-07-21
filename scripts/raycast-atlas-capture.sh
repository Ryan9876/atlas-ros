#!/bin/bash
# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Atlas Capture
# @raycast.mode compact
# @raycast.argument1 { "type": "text", "placeholder": "Capture" }
exec atlas capture "$1" --source raycast

