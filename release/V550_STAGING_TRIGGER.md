# Atlas ROS v5.5.0 Promotion Trigger

This file records the governed transition from the exact validated v5.5.0rc1 candidate to final publication and production promotion.

- Exact candidate: `8b248d371536c7274f6688fe7a331489d3f6a234`.
- Candidate artifact: `8611955387`.
- Candidate package SHA-256: `8ce4439feb06f0968ef9255255ae116b56d09e180cda1fe48358dd380a8fd474`.
- Full Validation: `V4V-31` — Passed with no blocking findings.
- Promotion decision: `V4D-27`.
- Production promotion authorized by Ryan Smith on 2026-07-24.
- Previous Active authority and required immediate immutable rollback: Atlas ROS v5.4.0.
- Authority records may switch only after final GitHub publication, asset readback, checksum verification, and Drive-independent restoration pass.

## Publication retry

- Initial final publication created `v5.5.0` and verified all checksums, but restoration run `30136025576` failed before benchmark execution because the verified source archive had not been extracted.
- Controller fix: `f8ceb17550513d289ebe443c47f93ef414564381`.
- Retry remains idempotent and must complete final asset readback, source extraction, installation, benchmark validation, and release metadata verification before authority records switch.

- Second retry run `30136083745` completed asset verification, source extraction, installation, and the 52-case benchmark, but its final report readback referenced the pre-extraction directory. Controller readback-path fix: `d38a26c47b0ecc753cece28d3ef08e775d4a0173`.
