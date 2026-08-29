from __future__ import annotations

from fastapi import APIRouter

from app.api.endpoints import analysis, campus, demand, dispatch, export, process, scheme, siting, student_mobility


api_router = APIRouter()
api_router.include_router(campus.router, tags=["campus"])
api_router.include_router(demand.router, tags=["demand"])
api_router.include_router(siting.router, tags=["siting"])
api_router.include_router(dispatch.router, tags=["dispatch"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(process.router, tags=["process"])
api_router.include_router(scheme.router, tags=["scheme"])
api_router.include_router(export.router, tags=["export"])
api_router.include_router(student_mobility.router, tags=["simulation"])