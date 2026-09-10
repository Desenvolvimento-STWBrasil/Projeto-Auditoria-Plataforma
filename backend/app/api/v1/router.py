from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.client import router as client_router
from app.api.v1.admin import router as admin_router
from app.api.v1.sub_users import router as sub_users_router
from app.api.v1.admin_onboarding import router as admin_onboarding_router
from app.api.v1.dashboard_cards import router as dashboard_cards_router
from app.api.v1.dashboard_board import router as dashboard_board_router
from app.api.v1.dashboard_categories import router as dashboard_categories_router
from app.api.v1.dashboard_labels import router as dashboard_labels_router
from app.api.v1.dashboard_templates import router as dashboard_templates_router
from app.api.v1.company_messages import router as company_messages_router
from app.api.v1.companies import router as companies_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(users_router)
router.include_router(client_router)
router.include_router(admin_router)
router.include_router(sub_users_router)
router.include_router(admin_onboarding_router)
router.include_router(dashboard_cards_router)
router.include_router(dashboard_board_router)
router.include_router(dashboard_categories_router)
router.include_router(dashboard_labels_router)
router.include_router(dashboard_templates_router)
router.include_router(company_messages_router)
router.include_router(companies_router)
