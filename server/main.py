from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import API_PREFIX
from .routers import dashboard, defects, grid, inspections, photos, repairs, route_plans, turbines, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="风电场叶片无人机巡检闭环系统",
    description="巡检 · 缺陷标注 · 维修决策 · 并网确认 · 追溯审计",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(turbines.router, prefix=API_PREFIX)
app.include_router(route_plans.router, prefix=API_PREFIX)
app.include_router(inspections.router, prefix=API_PREFIX)
app.include_router(defects.router, prefix=API_PREFIX)
app.include_router(photos.router, prefix=API_PREFIX)
app.include_router(repairs.router, prefix=API_PREFIX)
app.include_router(grid.router, prefix=API_PREFIX)


@app.get("/")
async def root():
    return {"name": "风电场叶片无人机巡检闭环系统 API", "version": "1.0.0", "docs": "/docs"}
