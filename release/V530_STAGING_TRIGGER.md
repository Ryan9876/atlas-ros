# Atlas ROS v5.3.0rc1 Staging Trigger

This marker records the deterministic staging transaction for candidate head `6380c79974bcd499a5694982210f86431e85dec4`, candidate workflow run `30115235749`, artifact ID `8605295031`, and expected package SHA-256 `3fe3dafe2723b5be881830fbd7ef4c74ebe0dad5ae7e1c1ed5a6a60ccabdcb53`.

The transaction creates or updates draft release tag `v5.3.0-rc.1`, uploads the checksum-bound candidate publication set, downloads and verifies the authoritative combined package and its internal publication checksum set, and proves restoration without Google Drive. It does not authorize or perform production promotion.

Attempt 2 corrects published-asset readback to use the authoritative combined package rather than the separately uploaded convenience copies.
