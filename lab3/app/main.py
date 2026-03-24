import uvicorn
import logging
import uuid

from fastapi import FastAPI, Request

from log_config import log_config

logger = logging.getLogger("myapp")
access_logger = logging.getLogger("access")
error_logger = logging.getLogger("error")

app = FastAPI()

def add_id(log: logging.Logger, request_id: str):
    return logging.LoggerAdapter(log, {"request_id": request_id})

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    add_id(access_logger, request_id).info(
        f"{request.method} {request.url.path} - {response.status_code}"
    )
    return response

@app.get("/")
async def root(request: Request):
    response = {"Data from web server"}
    log = add_id(logger, request.state.request_id)
    log.info("Request for root endpoint.")
    log.debug("Request for root endpoint.")
    log.info("Returning response: %s", response)
    return response

@app.get("/error")
async def error(request: Request):
    error_response = {"Error Response"}
    log = add_id(error_logger, request.state.request_id)
    try:
        text = "some text"
        text[1] = 1
    except Exception:
        log.exception("Custom error.")

    return error_response

if __name__ == "__main__":
    uvicorn.run(app,
        host="0.0.0.0",
        port=5500,
        log_config=log_config,
        access_log=False
    )