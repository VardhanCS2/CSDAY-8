from fastapi import APIRouter, Depends

from app.core.redis import get_redis


router = APIRouter(
    prefix="/redis",
    tags=["Redis"],
)


@router.get("/test")
async def test_redis(
    redis = Depends(get_redis)
):

    await redis.set(
        "message",
        "Redis is working"
    )

    value = await redis.get(
        "message"
    )

    return {
        "message": value
    }