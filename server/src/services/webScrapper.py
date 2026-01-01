from scrapingbee import ScrapingBeeClient
from src.config.index import appConfig
from src.config.logging import get_logger

logger = get_logger(__name__)

scrapingbee_client = ScrapingBeeClient(api_key=appConfig["scrapingbee_api_key"])
