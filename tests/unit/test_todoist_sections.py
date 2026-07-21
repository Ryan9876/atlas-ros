from atlas_ros.config.loader import load_config


def test_work_section_order_and_waiting_rule() -> None:
    config = load_config("todoist")
    assert config["work_sections"]["ordered"] == [
        "Leadership & Team",
        "Active Projects",
        "Operations",
        "Waiting on Others",
        "Development & Learning",
    ]
    assert "temporary state" in config["work_sections"]["rules"]["Waiting on Others"]
