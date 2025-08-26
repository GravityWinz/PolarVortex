from fastapi import FastAPI, UploadFile, WebSocket
import serial

app = FastAPI()

# Adjust port for Arduino connection
try:
    arduino = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
except Exception as e:
    arduino = None
    print("Arduino not connected:", e)

@app.get("/status")
async def get_status():
    if arduino:
        arduino.write(b'STATUS\n')
        return {"status": arduino.readline().decode().strip()}
    return {"status": "Arduino not connected"}

@app.post("/upload")
async def upload_image(file: UploadFile):
    contents = await file.read()
    return {"filename": file.filename, "size": len(contents)}

@app.post("/command/{cmd}")
async def send_command(cmd: str):
    if arduino:
        arduino.write(f"{cmd}\n".encode())
        return {"sent": cmd}
    return {"error": "Arduino not connected"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
