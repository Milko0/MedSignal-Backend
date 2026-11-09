from fastapi import APIRouter, Request

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness and database reachability")
async def health(request: Request):
    out = {"api": "ok", "mongo": "unknown", "redis": "unknown"}
    try:
        await request.app.state.mongo.admin.command("ping")
        out["mongo"] = "ok"
    except Exception as e:  # noqa: BLE001
        out["mongo"] = f"down ({type(e).__name__})"
    try:
        await request.app.state.redis.ping()
        out["redis"] = "ok"
    except Exception as e:  # noqa: BLE001
        out["redis"] = f"down ({type(e).__name__})"
    return out
