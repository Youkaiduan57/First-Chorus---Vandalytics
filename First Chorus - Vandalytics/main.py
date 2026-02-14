from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import subprocess

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("app.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
def signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/logout")
def logout():
    return HTMLResponse(
        '<html><head><meta http-equiv="refresh" content="1; url=/" /></head>'
        '<body style="background:#0e0e14;color:white;display:flex;justify-content:center;align-items:center;height:100vh;">'
        '<h2>Logged out. Redirecting to Home...</h2></body></html>'
    )

@app.post("/run/aim")
def run_aim():
    subprocess.Popen(["python", "aim_train.py"])
    return {"status": "Aim Trainer Started"}

@app.post("/run/optimize")
def run_optimize():
    subprocess.Popen(["python", "optimization.py"])
    return {"status": "Settings Optimizer Started"}

@app.post("/run/coach")
def run_coach():
    subprocess.Popen(["python", "coach.py"])
    return {"status": "AI Coach Started"}