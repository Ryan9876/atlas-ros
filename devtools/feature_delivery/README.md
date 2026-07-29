# Feature Delivery Tooling Boundary

This directory is reserved for repository-level development and release-tooling configuration, schemas, templates, fixtures, workflow registries, and reports. Runtime-importable development code lives under `src/atlas_ros/devtools_cli` solely to support the installed `atlas-dev` command and is prohibited from production runtime imports by `scripts/validate_devtools_boundary.py`.

The v7.4.0 candidate starts additively. Impact analysis is shadow-only and cannot suppress complete candidate gates.
