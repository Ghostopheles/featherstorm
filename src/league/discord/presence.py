import asyncio

from typing import Any
from dataclasses import dataclass, asdict

from pypresence import AioPresence
from pypresence.types import ActivityType, StatusDisplayType

@dataclass
class DiscordActivity:
    activity_type: ActivityType | None = None
    status_display_type: StatusDisplayType | None = None
    state: str | None = None
    details: str | None = None
    name: str | None = None
    start: int | None = None
    end: int | None = None
    large_image: str | None = None
    large_text: str | None = None
    small_image: str | None = None
    small_text: str | None = None
    party_id: str | None = None
    party_size: list | None = None
    join: str | None = None
    spectate: str | None = None
    match: str | None = None
    buttons: list | None = None
    instance: bool | None = None

class DiscordRichPresence:
    client_id: str = ""
    connected: bool = False
    rpc: AioPresence | None = None
    activity: DiscordActivity | None = None

    def __init__(
        self,
        client_id: str | None = None,
        activity: DiscordActivity | None = None
    ):
        if client_id is not None:
            self.client_id = client_id

        if activity is not None:
            self.activity = activity

        self.rpc = AioPresence(client_id)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def connect(self):
        await self.rpc.connect()
        self.connected = True

    async def close(self):
        # pypresence's AioPresence.close() is sync and closes the running event
        # loop, so we close the IPC pipe ourselves instead.
        self.connected = False
        writer = self.rpc.sock_writer
        if writer is None:
            return

        try:
            self.rpc.send_data(2, {"v": 1, "client_id": self.rpc.client_id})
        except Exception:
            pass

        writer.close()
        if hasattr(writer, "wait_closed"):
            await writer.wait_closed()
        else:
            # on Windows the writer is a proactor pipe transport; give the
            # loop a tick to run its connection_lost callback
            await asyncio.sleep(0)

        self.rpc.sock_writer = None
        self.rpc.sock_reader = None

    def set_activity(self, activity: DiscordActivity):
        self.activity = activity

    def get_activity(self) -> DiscordActivity | None:
        return self.activity

    def update_activity(self, **kwargs):
        if self.activity is None:
            self.activity = DiscordActivity()

        for key, value in kwargs.items():
            if hasattr(self.activity, key):
                setattr(self.activity, key, value)

    async def update(
        self,
        activity_type: ActivityType | None = None,
        status_display_type: StatusDisplayType | None = None,
        state: str | None = None,
        details: str | None = None,
        name: str | None = None,
        start: int | None = None,
        end: int | None = None,
        large_image: str | None = None,
        large_text: str | None = None,
        small_image: str | None = None,
        small_text: str | None = None,
        party_id: str | None = None,
        party_size: list | None = None,
        join: str | None = None,
        spectate: str | None = None,
        match: str | None = None,
        buttons: list | None = None,
        instance: bool | None = None
    ):
        if not self.connected:
            raise RuntimeError("DiscordRichPresence is not connected.")

        kwargs = {k: v for k, v in locals().items() if k != "self" and v is not None}
        await self.rpc.update(**{**asdict(self.activity), **kwargs})

    async def clear(self):
        if not self.connected:
            raise RuntimeError("DiscordRichPresence is not connected.")

        await self.rpc.clear()
