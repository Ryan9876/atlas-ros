# Atlas ROS v6.1.1 Explainability Standard

User-facing reasoning must state:

- the identified primary outcome
- the selected planning model
- the current execution path
- delegated and conditional work that remains withheld
- whether clarification is needed
- any low-confidence dimension
- whether that low confidence affects execution eligibility

User-facing text must not expose internal journals, transaction IDs, hashes, or receipt details unless the user is reviewing an audit record. An approved no-review result must never state that clarification is required or that the work belongs in Needs Clarification.

Material contradictions produce an attended-review explanation and make provider execution ineligible.
