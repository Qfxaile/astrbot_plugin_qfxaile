import asyncio

import pytest

from qfxaile.scheduler import TaskRegistry


@pytest.mark.asyncio
async def test_task_registry_stops_and_clears_running_tasks():
    registry = TaskRegistry()
    started = asyncio.Event()

    async def worker():
        started.set()
        await asyncio.Event().wait()

    registry.start("daily", lambda: worker())
    await started.wait()
    await registry.stop()

    assert registry.tasks == {}
