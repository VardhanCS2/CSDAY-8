from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.projects import router as projects_router
from app.routers.tasks import router as tasks_router


app = FastAPI(
    title="Task Management API",
    description="API for managing users, projects, and tasks",
    version="1.0.0",
)


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(projects_router)
app.include_router(tasks_router)


@app.get("/")
async def root():
    return {
        "message": "Task Management API is running"
    }