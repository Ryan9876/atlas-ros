# ADR — Atlas ROS v7.6.1 User Communication and Decision Adaptation

## Status

Accepted for candidate implementation; production deployment and profile activation are not authorized.

## Context

Atlas ROS v7.6.0 provides governed, inspectable, correctable, context-isolated intent evidence. Communication adaptation must reuse those controls rather than create a second memory subsystem. Full assessment reports and unconstrained profile prompts would create privacy, injection, staleness, and authorization risks.

## Decision

Implement four distinct layers: minimized source evidence, a deterministic integrated projection, a compact policy compiler, and context-specific playbooks. The projection references v7.6.0 governed evidence and retains confirmation, provenance, sensitivity, contradiction, review, expiry, and override state.

The executable policy is bounded to sixteen directives and twelve avoided patterns. It applies only when the software feature is in adaptation mode, the exact selected profile is valid and globally enabled, the context is enabled, and no current instruction or live authority override exists. Restricted preferences do not cross context boundaries.

The package contains contracts, compiler code, synthetic fixtures, and redacted examples only. The Ryan profile is a separate access-controlled artifact. Profile activation is a separate governed transaction and cannot create provider or execution authority.

## Consequences

- Disabled feature behavior remains equivalent to v7.6.0.
- Consequential clarification behavior remains unchanged.
- Adaptation decisions are deterministic and inspectable without revealing raw profile content.
- No dedicated Notion projection schema is required for this candidate; the model is derived over existing v7.6.0 evidence and externally bound profile state.
- An invalid profile degrades to the safe baseline rather than partially applying.
