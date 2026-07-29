# Atlas ROS v7.5.2 Clarification Evaluation Operator Guide

## Default state

The feature is disabled. Disabled mode must preserve accepted v7.5.1 behavior exactly.

## Shadow evaluation

Shadow mode may evaluate retained, minimized cases against the authoritative predecessor decision. It must not alter classification, routing, destination, execution intent, or provider state.

## Required checks

1. Confirm live authority still identifies v7.5.1 as Active and v7.5.0 as immediate rollback.
2. Confirm evaluation mode is `disabled` or `shadow`.
3. Confirm snapshot digest and predecessor decision digest are present.
4. Confirm provider-write and Todoist-write counts are zero.
5. Retain the deterministic report digest with validation evidence.
6. Do not create production persistence or schema without separate exact authorization.

## Stop conditions

Stop when authority changes, predecessor digests disagree, workspace correlation is ambiguous, evidence is not minimized, any write count is nonzero, or evaluation output reaches a routing/execution adapter.
