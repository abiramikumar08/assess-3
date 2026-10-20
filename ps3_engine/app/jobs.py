import os
from redis import Redis
from rq import Queue

def get_redis():
    return Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

queue = Queue('broll', connection=get_redis())

def process_job(payload: dict):
    # placeholder job – simply returns payload with completed status
    return {'status': 'completed', 'payload': payload}
