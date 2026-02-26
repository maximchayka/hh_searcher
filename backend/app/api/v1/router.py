from fastapi import APIRouter

from app.api.v1.endpoints import auth, resumes, cover_letters, search, applications, job_tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(resumes.router)
api_router.include_router(cover_letters.router)
api_router.include_router(search.router)
api_router.include_router(applications.router)
api_router.include_router(job_tasks.router)
