from typing import Union

from fastapi import FastAPI
from sqladmin import Admin

from src.database import engine
from src.admin import LeadAdmin

from faststream.redis import RedisBroker

app = FastAPI()
admin = Admin(app, engine, title="My Admin")

admin.add_view(LeadAdmin)


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.post("/send_message/{phone}")
async def send_message(phone: str):
    broker = RedisBroker("redis://redis:6379")
    await broker.connect()

    await broker.publish(
        {"phone": phone},
        channel="whatsapp_messages"
    )

    print("Завдання відправлено в чергу!")
    await broker.close()
