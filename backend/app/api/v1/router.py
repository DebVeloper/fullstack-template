from fastapi import APIRouter

from app.api.v1.endpoints import admin_users, auth, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(users.router, prefix="/users")
api_router.include_router(admin_users.router, prefix="/admin/users")
