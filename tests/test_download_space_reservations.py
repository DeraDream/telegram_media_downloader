"""Tests for per-filesystem download-space reservations."""
from collections import namedtuple
from unittest import mock

from media_downloader import app, space_reservations
from module.app import TaskNode


DiskUsage = namedtuple("DiskUsage", "total used free")


def setup_function():
    space_reservations._items.clear()  # pylint: disable=protected-access
    app.space_reservation_bytes = 0
    app.space_reservation_count = 0
    app.space_reservation_by_device = {}


def test_same_disk_is_reserved_once_and_released_as_written():
    node = TaskNode(1, task_id=1)
    with mock.patch.object(space_reservations, "_device", return_value=10), mock.patch(
        "media_downloader.shutil.disk_usage", return_value=DiskUsage(1000, 0, 1000)
    ):
        admitted, _, _ = space_reservations.reserve(node, 1, 500, "/downloads")
        assert admitted
        assert app.space_reservation_by_device == {10: 500}

        space_reservations.update(node, 1, 200)
        assert app.space_reservation_by_device == {10: 300}


def test_cross_disk_reserves_final_copy_until_task_is_released():
    node = TaskNode(1, task_id=2)
    with mock.patch.object(space_reservations, "_device", side_effect=[10, 20]), mock.patch(
        "media_downloader.shutil.disk_usage", return_value=DiskUsage(1000, 0, 1000)
    ):
        admitted, _, _ = space_reservations.reserve(node, 2, 500, "/downloads")
        assert admitted
        assert app.space_reservation_by_device == {10: 500, 20: 500}

        space_reservations.update(node, 2, 200)
        assert app.space_reservation_by_device == {10: 300, 20: 500}

        space_reservations.release(node, 2)
        assert app.space_reservation_by_device == {}


def test_cross_disk_rejects_when_destination_budget_is_insufficient():
    node = TaskNode(1, task_id=3)
    with mock.patch.object(space_reservations, "_device", side_effect=[10, 20]), mock.patch(
        "media_downloader.shutil.disk_usage",
        side_effect=[DiskUsage(1000, 0, 1000), DiskUsage(100, 0, 100)],
    ):
        admitted, available, _ = space_reservations.reserve(node, 3, 200, "/downloads")

    assert not admitted
    assert available == 95
    assert app.space_reservation_by_device == {}
