import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import asyncio
import os
import logging

# Configure logging
# logging.basicConfig(level=logging.INFO, filename='/Users/bootnext-mac-124/Downloads/flutter/logs', filemode='a',
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI()

class ScriptRequest(BaseModel):
    app_name: str
    flutter_version: str
    source_code_path: str

    class Config:
        json_schema_extra = {
            "example": {
                "app_name": "MiniApp",
                "flutter_version": "3.16.9",
                "source_code_path": "/path/to/my/app/source_code",
            }
        }

class ScriptResponse(BaseModel):
    message: str
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Script Output",
            }
        }

# Store WebSocket connections
websocket_connections = set()

@app.websocket("/ws/logs/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.add(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)

async def send_logs_to_websockets(log_message):
    encoded_message = jsonable_encoder({"message": log_message})
    for connection in websocket_connections:
        await connection.send_json(encoded_message)

async def run_script(command: list, log_file_path: str):
    try:
        logging.info(f"Running command: {' '.join(command)}")

        # clear logs.txt
        with open(log_file_path, 'w') as log_file:
            log_file.truncate()

        # Open logs.txt in append mode for writing logs
        with open(log_file_path, 'a') as log_file:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            while True:
                stdout_line = await process.stdout.readline()
                stderr_line = await process.stderr.readline()
                if not stdout_line and not stderr_line:
                    break
                stdout_line = stdout_line.decode().strip()
                stderr_line = stderr_line.decode().strip()
                if stdout_line:
                    await send_logs_to_websockets(f"{stdout_line}")
                    log_file.write(stdout_line + '\n')

                if stderr_line:
                    await send_logs_to_websockets(f"{stderr_line}")
                    log_file.write(stderr_line + '\n')

            await process.wait()

        logging.info("Script executed successfully")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Script failed: {e.stderr}")
    except Exception as err:
        logging.error(f"Script failed: {err}")

@app.post("/run-build-script/", response_class=JSONResponse, response_model=ScriptResponse)
async def run_build_script(request: ScriptRequest, background_tasks: BackgroundTasks, run_pub_outdated: bool = False, run_pub_upgrade: bool = False):
    script_path = "/Users/bootnext-mac-124/Downloads/flutter/logs.sh"
    log_file_path = "/Users/bootnext-mac-124/Downloads/flutter/logs.txt"

    if not os.path.isfile(script_path):
        logging.error(f"Script not found: {script_path}")
        raise HTTPException(status_code=404, detail="Script not found")

    command = [script_path]

    if run_pub_upgrade:
        command.append('-u')
    if run_pub_outdated:
        command.append('-o')

    command.extend([request.flutter_version, request.source_code_path, request.app_name])

    # Add the task to the background
    background_tasks.add_task(run_script, command, log_file_path)

    return {"message": "Script is running in the background"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('ws:app', host="0.0.0.0", port=8000, reload=True)
