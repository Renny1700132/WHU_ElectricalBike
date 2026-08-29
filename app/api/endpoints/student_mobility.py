from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.algorithm.student_mobility import build_student_daily_mobility
from app.schemas.student_mobility import StudentMobilityRequest, StudentMobilityResponse

router = APIRouter()


@router.post(
    "/simulation/students/day",
    response_model=StudentMobilityResponse,
    summary="Simulate Student Daily Mobility / 模拟学生一天轨迹",
    description="Generate daily event-based mobility trajectories for students. / 生成学生一天的事件段轨迹数据。",
)
def simulate_student_daily_mobility(payload: StudentMobilityRequest) -> StudentMobilityResponse:
    try:
        students = build_student_daily_mobility(
            student_count=payload.student_count,
            include_routes=payload.include_routes,
        )
        return StudentMobilityResponse(
            status="success",
            student_count=payload.student_count,
            students=students,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))