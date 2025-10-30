import signal
import sys
from fastapi import FastAPI

def signal_handler(sig, frame):
    print('Signal received, but ignoring')
    return

signal.signal(signal.SIGINT, signal_handler)

app = FastAPI()

@app.get('/')
def hello():
    try:
        print('Endpoint called')
        return {"message": "hello"}
    except Exception as e:
        print(f'Exception in endpoint: {e}')
        raise

