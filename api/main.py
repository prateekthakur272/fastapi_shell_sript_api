import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio
import os

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
    stdout: str
    stderr: str

    class Config:
        json_schema_extra = {
            "example": {
                "stdout": "Script Output",
                "stderr": "Errors"
            }
        }

class Message(BaseModel):
    message:str

@app.post("/run-build-script/", response_class=JSONResponse, response_model=Message)
async def run_build_script(request: ScriptRequest, run_pub_outdated: bool = False, run_pub_upgrade: bool = False):
    script_path = "../logs.sh"
    
    if not os.path.isfile(script_path):
        raise HTTPException(status_code=404, detail="Script not found")
    
    try:
        command = [script_path]

        if run_pub_upgrade:
            command.append('-u')
        if run_pub_outdated:
            command.append('-o')

        command.extend([request.flutter_version, request.source_code_path, request.app_name])

        print(" ".join(command))

        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        
        # stdout, stderr = await process.communicate()
        # return ScriptResponse(stdout=stdout.decode(), stderr=stderr.decode())
        return Message(message='Script started in background')
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Script failed: {e.stderr}")
    
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Script failed: {err}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('main:app', host="0.0.0.0", port=8000, reload=True)
