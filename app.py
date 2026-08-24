from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FIXED = [{"id": 1, "name": "fixed"}]


@app.get("/get")
async def get_item():
    return {"id": 2, "role": "assistance", "text": "hi how can i help you"}


@app.post("/post")
async def post_item():
    time.sleep(0.5)
    return {"id": 1, "role": "assistance", "text": "hi how can i help you"}
