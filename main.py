from multiprocessing import Manager, Process
import os
import time
from fastapi import FastAPI, Form, HTTPException
import Utils
import wb
import asyncio
from fastapi import FastAPI, Request, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

class UrlTask(BaseModel):
    url: str
    task_id: str

class LoginData(BaseModel):
    username: str
    password: str

class CodeData(BaseModel):
    username: str
    captcha: str

# 设置静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("static/index.html", "r") as file:
        content = file.read()
    return HTMLResponse(content=content)

@app.post("/create-captcha-file")
async def create_captcha_file(data: UrlTask):
    directory = './captchas'
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_name = os.path.join(directory, f"captchasurl_{data.task_id}.txt")
    try:
        with open(file_name, "w") as file:
            file.write(data.url)
        return {"status": "success", "file_name": file_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/captcha-url")
async def get_captcha_url(task_id: str):
    if os.path.exists(f"./captchas/captchasurl_{task_id}.txt"):
        with open(f"./captchas/captchasurl_{task_id}.txt", "r") as f:
            code = f.read()
        return {"status": "验证码地址获取成功", "url": code}
    else:
        return {"url": "暂未获取到"}

@app.post("/submit-code")
async def submit_code(data: CodeData):
    directory = './captchas'
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_name = os.path.join(directory, f"captchas_{data.username}.txt")
    
    try:
        with open(file_name, "w") as file:
            file.write(data.captcha)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/status")
async def get_status(task_id: str = Query(...)):
    # Check if the specific task_id status is available
    if os.path.exists(f"./captchas/captchas_{task_id}.txt"):
        with open(f"./captchas/captchas_{task_id}.txt", "r") as f:
            code = f.read().strip()
        return {"status": "验证码已提交", "code": code}
    else:
        return {"status": "等待验证码提交"}

def write_to_task_file(task_id, content):
    directory = './log'
    file_path = os.path.join(directory, f"{task_id}.txt")
    
    # 如果目录不存在，创建目录
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # 写入内容到文件
    with open(file_path, 'a') as file:
        file.write(content + '\n')
    
    print(f"内容已写入到 {file_path}")

def read_from_task_file(task_id):
    directory = './log'
    file_path = os.path.join(directory, f"{task_id}.txt")
    
    # 检查文件是否存在
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"{file_path} 文件不存在")

    # 读取文件内容
    with open(file_path, 'r') as file:
        content = file.read()
    
    return content

def process_task(username: str, password: str, task_id: str, tasks):
    file_path = f'./log/{task_id}.txt'  # 文件路径
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"文件 {file_path} 已删除")
    else:
        print(f"文件 {file_path} 不存在")
    write_to_task_file(task_id, "等待执行")
    tasks[task_id] = "Started"

    try:
        config = Utils.set_accounts(username, password)
        Utils.save_Login_State(config)
        asyncio.run(wb.main())
    except KeyboardInterrupt:print(f'\n任务被手动终止')
    os.system("pause")
    
    write_to_task_file(task_id, "执行完毕")
    tasks[task_id] = "Completed"

@app.post("/submit-login")
async def submit_login(data: LoginData):
    task_id = f"{data.username}"
    
    # if task_id in tasks:
    #     raise HTTPException(status_code=400, detail="Task already in progress")
    
    p = Process(target=process_task, args=(data.username, data.password, task_id, tasks))
    p.start()
    tasks[task_id] = "Processing"
    return {"task_id": task_id, "status": tasks[task_id]}

@app.get("/status/{username}")
async def get_status(username: str):
    task_id = f"{username}"
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status = tasks[task_id]
    log = read_from_task_file(task_id)
    
    return {"task_id": task_id, "status": status,"logs": log}

@app.get("/file", response_model=List[str])
async def get_file_names():
    log_dir = './log'
    file_names = [f[:7] for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
    return file_names

if __name__ == "__main__":
    manager = Manager()
    tasks = manager.dict()  # Used to store task status
    log_queues = manager.dict()  # Used to store log queues

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
