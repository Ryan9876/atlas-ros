# Atlas ROS v4.1.0 — W01 Universal Capture Runbook

Purpose: repeatable validation, recovery, and retargeting procedure for the production W01 Universal Capture workflow. Current runtime state and acceptance evidence are maintained in the Automation Register and Review Records.

## Target production Inbox
- Database: https://app.notion.com/p/ecc51b926f32483a86cf5d77b4eab069
- Data source: collection://7bc7d289-299f-4160-95c9-921ee15ce505

## Required properties now present
- Capture — Title
- Raw Capture — Rich text
- Source — Select with Raycast
- Status — Select with New
- Correlation ID — Rich text
- Capture ID — Rich text
- Processing Note — Rich text

## Procedure on Ryan's Mac
1. Open the existing ROS Capture Raycast Script Command.
2. Retain the approved ros-capture-v1.1.5.sh code and Keychain token handling.
3. Replace the legacy Universal Inbox database-container ID or URL with the v4 database shown above.
4. Confirm the Notion connection has access only to the v4 Universal Inbox.
5. Run three harmless captures from different applications.
6. Verify each record appears once with Source=Raycast, Status=New, Capture ID, Correlation ID, and Processing Note populated.
7. Disconnect the network, submit one harmless capture, reconnect, retry, and confirm exactly one record exists for the original Correlation ID.
8. Process one test item through W02 and verify its Destination Record URL.
9. Record acceptance evidence in v4 Review Records.

## Acceptance rule
Production activation or reactivation requires all device tests to pass, acceptance evidence to be recorded in Review Records, and the Automation Register to be updated and verified by readback.
