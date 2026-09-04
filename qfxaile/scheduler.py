from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any


class TaskRegistry:
    """Manage named background tasks and wait for their cancellation."""

    def __init__(self) -> None:
        self.tasks: dict[str, asyncio.Task[Any]] = {}

    def start(
        self,
        name: str,
        coroutine_factory: Callable[[], Coroutine[Any, Any, Any]],
    ) -> None:
        old_task = self.tasks.pop(name, None)
        if old_task and not old_task.done():
            old_task.cancel()
        self.tasks[name] = asyncio.create_task(coroutine_factory(), name=name)

    async def stop(self) -> None:
        tasks = list(self.tasks.values())
        self.tasks.clear()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
