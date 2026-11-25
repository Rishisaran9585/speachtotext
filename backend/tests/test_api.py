import os
os.environ["DATABASE_URL"]="sqlite:///./test_speech.db"
from fastapi.testclient import TestClient
from app.main import app, Base, engine
Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
client=TestClient(app)
def test_health(): assert client.get("/api/health").json()["status"]=="ok"
def test_transcription_crud():
    r=client.post("/api/transcriptions",json={"title":"Test","text":"hello नमस्ते"}); assert r.status_code==201
    item=r.json(); tid=item["id"]
    assert client.get(f"/api/transcriptions/{tid}").json()["text"]=="hello नमस्ते"
    assert client.patch(f"/api/transcriptions/{tid}",json={"title":"Edited"}).json()["title"]=="Edited"
    assert client.delete(f"/api/transcriptions/{tid}").status_code==204
    assert client.get(f"/api/transcriptions/{tid}").status_code==404
def test_empty_text_rejected(): assert client.post("/api/transcriptions",json={"text":" "}).status_code==422
