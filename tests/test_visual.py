from spatialscan.tiers.visual import collect_images, collect_video_frames, estimate_visual_capture, estimate_visual_plan


def test_visual_photo_fixture_runs():
    result = estimate_visual_plan(collect_images("fixtures/photo"), "photos")
    assert result["tier"] == "photos"
    assert result["device"]["images_used"] > 0


def test_visual_video_fixture_runs():
    frames = collect_video_frames("fixtures/video")
    result = estimate_visual_plan(frames, "video")
    assert result["tier"] == "video"
    assert result["device"]["images_used"] > 0


def test_visual_scale_calibration_changes_footprint():
    result = estimate_visual_plan(collect_images("fixtures/photo"), "photos", 0.01)
    assert result["diagnostics"]["calibration_status"] == "DECLARED_SCALE_PER_PIXEL"
    assert result["rooms"][0]["floor_area_m2"]["value"] > 1


def test_visual_capture_groups_photo_room_folders(tmp_path):
    import shutil

    source = collect_images("fixtures/photo")[0]
    for room_id in ("room_01", "room_02"):
        target = tmp_path / room_id
        target.mkdir()
        shutil.copyfile(source, target / "view_01.png")
    result = estimate_visual_capture(collect_images(tmp_path), "photos")
    assert result["device"]["rooms_detected"] == 2
    assert {room["id"] for room in result["rooms"]} == {"room_01", "room_02"}