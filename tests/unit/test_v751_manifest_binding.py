from __future__ import annotations

from pathlib import Path

import pytest

from atlas_ros.kernel import bootstrap

_INVENTORY_DATA_SOURCE = "collection://46af021f-eb9a-4eba-b10c-4523e70df0c3"


def test_v751_candidate_manifest_binds_authoritative_integration_inventory() -> None:
    manifest = Path("release/RELEASE_MANIFEST_V751_DRAFT.md").read_text()

    assert bootstrap._integration_inventory_reference(manifest) == _INVENTORY_DATA_SOURCE
    assert (
        "Integration Inventory authority: "
        "https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b"
    ) in manifest


def test_manifest_without_inventory_binding_fails_closed() -> None:
    with pytest.raises(
        bootstrap.InitializationError,
        match="active manifest does not provide the Integration Inventory reference",
    ):
        bootstrap._integration_inventory_reference("# Atlas ROS v7.5.1\n")


def test_inventory_data_source_takes_precedence_over_page_fallback() -> None:
    manifest = "\n".join(
        (
            "# Atlas ROS v7.5.1",
            "Integration Inventory authority: https://app.notion.com/p/fallback",
            f"Integration Inventory data source: {_INVENTORY_DATA_SOURCE}",
        )
    )

    assert bootstrap._integration_inventory_reference(manifest) == _INVENTORY_DATA_SOURCE
