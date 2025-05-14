from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .handlers import router as api_router
from ..config import DEBUG, API_HOST, API_PORT

app = FastAPI(
    title="RFID Indoor Positioning API",
    version="0.1.0",
    debug=DEBUG
)

# 跨域配置（根据前端域名自行调整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(api_router, prefix="/api", tags=["rfid"])

# 入口提示
@app.get("/", tags=["root"])
def read_root():
    return {"message": "Welcome to RFID Indoor Positioning API"}
