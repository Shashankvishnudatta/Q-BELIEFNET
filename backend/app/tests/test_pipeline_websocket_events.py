import asyncio

from app.api.websockets import publish_message


def test_pipeline_websocket_event_can_be_published():
    asyncio.run(publish_message({"type": "provider_health_update", "payload": {"health": "ok"}}))

    # publish_message assigns IDs and stores messages without requiring connected clients.
    from app.api.websockets import message_history

    assert message_history[-1]["type"] == "provider_health_update"
    assert "meta" in message_history[-1]
