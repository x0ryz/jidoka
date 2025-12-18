from faststream import FastStream
from faststream.redis import RedisBroker
from src.config import settings

broker = RedisBroker(settings.REDIS_URL)
app = FastStream(broker)
