from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes.projectFilesRoutes import router as projectFilesRoutes
from src.routes.userRoutes import router as userRoutes
from src.routes.projectRoutes import router as projectRoutes
from src.routes.chatRoutes import router as chatRoutes
from src.middleware.logging_middleware import LoggingMiddleware
from src.config.logging import configure_logging

configure_logging(log_filename="application.log")

app = FastAPI(
    title="MultiModal RAG",
    description="API for Enterprise-level MultiModal RAG System",
)

app.add_middleware(LoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-Request-ID"],
)
app.include_router(userRoutes, prefix="/api/user")
app.include_router(projectRoutes, prefix="/api/project")
app.include_router(projectFilesRoutes, prefix="/api/project")
app.include_router(chatRoutes, prefix="/api/chat")

