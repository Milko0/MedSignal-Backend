from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status

from app.application.dtos.admin import FaersLoadRequest, IngestionRunDto, IngestionStarted
from app.presentation.api.dependencies import ingestion_runs
from app.presentation.api.responses import CONFLICT

router = APIRouter(prefix="/ingestion", tags=["Admin: ingestion"])

BUSY = "An ingestion job of this kind is already running; follow it in GET /api/admin/ingestion/runs"


def jobs(request: Request):
    return request.app.state.ingestion_jobs


@router.post("/faers", status_code=status.HTTP_202_ACCEPTED, response_model=IngestionStarted,
             responses={**CONFLICT, 422: {"description": "A file is not in the FAERS folder"}},
             summary="Full FAERS load (FR-19)",
             description="Starts in the background and answers at once. Loads the given FAERS bulk files from "
                         "`FAERS_DIR` (download them with `scripts/download_faers.py`), resolves new drug names "
                         "through RxNav, drops the quarters outside the rolling window and recomputes the signals of "
                         "every quarter. New files with many unseen names can take a long time; progress and the "
                         "result appear in `GET /admin/ingestion/runs`.")
async def full_load(body: FaersLoadRequest, background: BackgroundTasks, j=Depends(jobs)):
    paths = j.faers_paths(body.files)            # 422 before anything starts
    if not j.start("faers"):
        raise HTTPException(status.HTTP_409_CONFLICT, BUSY)
    background.add_task(j.faers, paths, body.window_quarters)
    return IngestionStarted(job="faers", detail=f"Loading {len(paths)} file(s); see /api/admin/ingestion/runs")


@router.post("/incremental", status_code=status.HTTP_202_ACCEPTED, response_model=IngestionStarted,
             responses=CONFLICT, summary="Incremental update of shortages, labels and recalls (FR-20)",
             description="Starts in the background and answers at once. Polls the openFDA shortage list (changes are "
                         "stored as events and alert the followers), then downloads the labels and recalls changed "
                         "in the last `since_days` days. The worker already runs both every day (03:00 and 04:00); "
                         "this runs them now.")
async def incremental(background: BackgroundTasks,
                      label_limit: int | None = Query(None, ge=1, le=20000,
                                                      description="At most this many labels (default: all new)"),
                      since_days: int | None = Query(None, ge=1, le=365,
                                                     description="Labels and recalls changed in the last N days "
                                                                 "(default 30)"),
                      j=Depends(jobs)):
    if not j.start("incremental"):
        raise HTTPException(status.HTTP_409_CONFLICT, BUSY)
    background.add_task(j.incremental, label_limit, since_days)
    return IngestionStarted(job="incremental", detail="Polling openFDA; see /api/admin/ingestion/runs")


@router.get("/runs", response_model=list[IngestionRunDto], summary="Ingestion logs (FR-21)",
            description="Newest first: loads, shortage polls, label/recall updates, rolling-window drops and "
                        "failed jobs.")
async def runs(skip: int = 0, limit: int = 50, uc=Depends(ingestion_runs)):
    return await uc.execute(skip, limit)
