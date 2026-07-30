# Atlas ROS v8.0.0 Rollback Evidence Plan

The full candidate workflow resolves the current Active release from live `governance/AUTHORITY.json`, requires it to be Atlas ROS v7.8.0 for this release transaction, downloads the exact immutable Release assets, verifies `CHECKSUMS.sha256`, and records the immutable commit. It also verifies the current immediate rollback chain without modifying it.

Before activation, independent publication readback must repeat v7.8.0 restoration from the published immutable assets. The additive Notion migration requires no destructive rollback; v7.8.0 ignores the added fields. No v8.0.0 authority activation may occur unless restoration evidence passes.
