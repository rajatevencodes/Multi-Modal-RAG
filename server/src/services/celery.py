from celery import Celery
from celery.signals import setup_logging
from src.config.index import appConfig
from src.rag.ingestion.index import process_document
from src.config.logging import get_logger, configure_logging


@setup_logging.connect
def config_loggers(*args, **kwargs):
    configure_logging(log_filename="worker.log")


logger = get_logger(__name__)

celery_app = Celery(
    "multi-modal-rag",  # Name of the Celery App
    broker=appConfig["redis_url"],  # broker - Redis Queue - Tasks are queued
)


@celery_app.task
def perform_rag_ingestion_task(document_id: str):
    try:
        logger.info("celery_task_started", document_id=document_id)
        process_document_result = process_document(document_id)
        logger.info("celery_task_completed", document_id=document_id)
        return (
            f"Document {process_document_result['document_id']} processed successfully"
        )
    except Exception as e:
        logger.error(
            "celery_task_failed", document_id=document_id, error=str(e), exc_info=True
        )
        return f"Failed to process document {document_id}: {str(e)}"
