"""Tests for restart recovery retry behaviour."""
import asyncio
import time
from unittest import mock

from module.bot import DownloadBot


class FailingClient:
    def __init__(self):
        self.notifications = []

    async def get_messages(self, *_):
        raise ConnectionError("temporary network failure")

    async def send_message(self, *args):
        self.notifications.append(args)


def test_failed_recovery_is_persisted_for_delayed_retry_and_notified_once():
    downloader = DownloadBot()
    client = FailingClient()
    downloader.bot = client
    downloader.client = client
    downloader.recoverable_downloads = {
        "task": {
            "user_id": 1,
            "messages": [{"chat_id": 2, "message_id": 3}],
            "use_user_client": False,
        }
    }

    async def stop_after_first_sleep(_):
        downloader.is_running = False

    with mock.patch.object(downloader, "update_config") as update_config, mock.patch(
        "module.bot.asyncio.sleep", side_effect=stop_after_first_sleep
    ):
        asyncio.run(downloader.recover_downloads())

    record = downloader.recoverable_downloads["task"]
    assert record["recovery_attempts"] == 1
    assert record["next_recovery_at"] > time.time()
    assert record["recovery_notice_sent"]
    assert len(client.notifications) == 1
    update_config.assert_called_once()
