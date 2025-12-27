# -*- coding: utf-8 -*-
"""
Простой интеграционный тест: bot → process_manager → event → handler
"""

import asyncio
from core.event_bus import subscribe_async, emit_event, clear_all_handlers
from core.utils.validator import validate_coordinates
from core.process_manager import generate_task_id


async def test_basic_integration():
    """Тестирует базовую цепочку: событие → обработчик."""
    results = []

    async def handler(event):
        results.append(event)

    subscribe_async("integration_test", handler)

    await emit_event("integration_test", {"status": "success", "step": 1})

    await asyncio.sleep(0.1)

    assert len(results) == 1
    assert results[0]["status"] == "success"
    assert results[0]["step"] == 1

    clear_all_handlers()
    print("✅ test_basic_integration passed")


def test_utils_integration():
    """Тестирует валидаторы."""
    assert validate_coordinates(55.75, 37.62) == True
    assert generate_task_id("script.py", ["1", "2"]) == generate_task_id("script.py", ["1", "2"])
    print("✅ test_utils_integration passed")


if __name__ == "__main__":
    asyncio.run(test_basic_integration())
    test_utils_integration()