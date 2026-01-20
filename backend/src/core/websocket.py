import asyncio
import json

from fastapi import WebSocket
from loguru import logger

from src.core.broker import broker


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket client connected. Total: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client disconnected")

    async def broadcast(self, message: dict):
        data = json.dumps(message, default=str)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.error(f"Error sending to WS: {e}")
                self.disconnect(connection)


manager = ConnectionManager()


async def nats_listener():
    """Listen to NATS ws_updates subject and broadcast to WebSocket clients"""
    logger.info("Starting NATS Listener for WebSocket updates...")

    while True:
        try:
            if not broker._connection:
                logger.warning("NATS broker not connected, waiting...")
                await asyncio.sleep(2)
                continue

            js = broker._connection.jetstream()

            try:
                await js.add_stream(
                    name="ws_updates",
                    subjects=["ws_updates"],
                    retention="limits",
                    max_msgs=10000,
                    max_age=300,
                    discard="old",
                )
            except Exception:
                pass

            psub = await js.pull_subscribe("ws_updates", "ws-broadcaster")
            logger.info("NATS Pub/Sub connected for WebSocket updates")

            while True:
                try:
                    messages = await psub.fetch(batch=1, timeout=1.0)
                    for msg in messages:
                        try:
                            payload = json.loads(msg.data.decode())
                            event_name = (
                                payload.get("event") or payload.get("type") or "unknown"
                            )
                            logger.info(f"WS sending: {event_name}")
                            await manager.broadcast(payload)
                            await msg.ack()
                        except json.JSONDecodeError:
                            logger.error(f"Failed to decode NATS message: {msg.data}")
                            await msg.ack()
                        except Exception as e:
                            logger.error(f"Error broadcasting message: {e}")
                            await msg.ack()
                except TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error fetching messages: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("NATS listener cancelled.")
            break
        except Exception as e:
            logger.error(f"NATS connection lost: {e}. Reconnecting...")
            await asyncio.sleep(5)
