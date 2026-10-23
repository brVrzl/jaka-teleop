from __future__ import annotations

from pathlib import Path

from embodiment_core.config import load_yaml


def test_all_yaml_configs_load() -> None:
    config_root = Path("configs")
    for yaml_path in config_root.rglob("*.yaml"):
        data = load_yaml(yaml_path)
        assert isinstance(data, dict), yaml_path


def test_required_robot_config_fields() -> None:
    jaka = load_yaml("configs/sim/quest_hts_jaka_mini2_live_demo.yaml")
    collection = load_yaml("configs/data_collection/physical_collection.yaml")
    rh56 = load_yaml("configs/hand/rh56_pc_direct_teleop.yaml")
    camera = load_yaml("tests/fixtures/default_rgbd.yaml")
    assert jaka["schema_version"] == "quest_hts_jaka_mini2_live_demo.v1"
    assert (
        collection["runtime"]["enforce_clutch_target_displacement_limit"]
        is False
    )
    assert len(jaka["simulation"]["initial_arm_joints_rad"]) == 6
    assert rh56["serial"]["baudrate"] == 115200
    assert "port" not in rh56["serial"]
    assert rh56["scheduler"]["command_rate_hz"] == 40
    assert rh56["scheduler"]["current_feedback_rate_hz"] == 10
    assert camera["device_type"] == "rgbd"
    assert "topics" in camera


def test_machine_runtime_reports_missing_and_invalid_values() -> None:
    from copy import deepcopy
    from embodiment_core.config import validate_runtime_config

    example = load_yaml("configs/data_collection/thor.example.yaml")
    errors = validate_runtime_config(example)
    assert any("robot_ip" in error for error in errors)
    assert any("workspace.serial" in error for error in errors)
    configured = deepcopy(example)
    configured["runtime"].update(robot_ip="192.0.2.50", edg_state_ip="192.0.2.19")
    configured["cameras"]["workspace"]["serial"] = "camera-a"
    configured["cameras"]["wrist"]["serial"] = "camera-b"
    assert validate_runtime_config(configured) == []
    configured["runtime"]["port"] = True
    configured["runtime"]["allowed_sender"] = "not-an-ip"
    configured["cameras"]["wrist"]["serial"] = "camera-a"
    errors = validate_runtime_config(configured)
    assert any("port" in error for error in errors)
    assert any("allowed_sender" in error for error in errors)
    assert any("different" in error for error in errors)


def test_dh_profile_cannot_enter_rh56_recorder(tmp_path) -> None:
    import pytest
    import yaml
    from episode_dataset.runtime import EpisodeDataRuntime

    config = load_yaml("configs/data_collection/thor.example.yaml")
    config["cameras"]["workspace"]["serial"] = "camera-a"
    config["cameras"]["wrist"]["serial"] = "camera-b"
    path = tmp_path / "dh.yaml"
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="DH 7-D"):
        EpisodeDataRuntime.start(path, episode_root=None, task_name="bringup",
            operator="test", control_config_path="unused", maximum_start_delta_rad=0.01,
            metadata={})


def test_machine_ip_fields_reject_numeric_yaml_and_unspecified_peer() -> None:
    from embodiment_core.config import validate_runtime_config

    document = load_yaml("configs/data_collection/thor.example.yaml")
    document["runtime"].update(robot_ip=1, edg_state_ip=True, allowed_sender=123)
    errors = validate_runtime_config(document)
    for name in ("robot_ip", "edg_state_ip", "allowed_sender"):
        assert any(name in error for error in errors)
    document["runtime"].update(robot_ip="0.0.0.0", edg_state_ip="192.0.2.1", allowed_sender=None)
    assert any("robot_ip" in error for error in validate_runtime_config(document))


def test_yaml_empty_sequence_is_not_a_mapping(tmp_path) -> None:
    import pytest
    path = tmp_path / "invalid.yaml"
    path.write_text("[]")
    with pytest.raises(ValueError, match="mapping"):
        load_yaml(path)


def test_dh_tool_cannot_bypass_recorder_guard_with_legacy_or_missing_profile(tmp_path) -> None:
    import pytest
    import yaml
    from episode_dataset.runtime import EpisodeDataRuntime

    document = load_yaml("configs/data_collection/thor.example.yaml")
    document["cameras"]["workspace"]["serial"] = "camera-a"
    document["cameras"]["wrist"]["serial"] = "camera-b"
    for profile in (None, "jaka_rh56_12d_v1"):
        document["dataset"].pop("profile", None)
        if profile is not None:
            document["dataset"]["profile"] = profile
        path = tmp_path / "dh.yaml"
        path.write_text(yaml.safe_dump(document))
        with pytest.raises(ValueError, match="DH 7-D"):
            EpisodeDataRuntime.start(path, episode_root=None, task_name="bringup",
                operator="test", control_config_path="unused", maximum_start_delta_rad=0.01,
                metadata={})
