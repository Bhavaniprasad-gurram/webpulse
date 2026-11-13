import time
import signal
import sys
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from config import config
from database.connection import get_db, test_connection
from database.models import Website
from repositories.website_repository import WebsiteRepository
from services.monitoring_service import MonitoringService

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] (Worker) %(name)s: %(message)s",
)
logger = logging.getLogger("webpulse.worker")


class MonitorWorker:
    """
    Dedicated background worker executing continuous scheduled HTTP checks
    for all active registered websites using APScheduler.
    Runs independently from the Streamlit UI process.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.running_jobs = set()  # Track scheduled website_ids
        self._is_running = True

    def run_check_for_website(self, website_id: int):
        """Worker task executed by APScheduler for a specific website."""
        try:
            result = MonitoringService.record_and_evaluate(website_id)
            if result:
                status_str = "UP" if result.is_available else "DOWN"
                code_str = f"HTTP {result.http_status_code}" if result.http_status_code else (result.error_type or "ERR")
                latency_str = f"{result.response_time_ms}ms" if result.response_time_ms is not None else "--"
                logger.info(f"Checked Website #{website_id} -> {status_str} [{code_str}] ({latency_str})")
        except Exception as exc:
            logger.error(f"Worker encountered unhandled error during check of website #{website_id}: {exc}", exc_info=True)

    def sync_scheduled_jobs(self):
        """
        Synchronize APScheduler jobs with active website records in the database.
        Adds newly created websites, removes deleted/inactive websites, and
        adjusts interval triggers if modified.
        """
        try:
            with get_db() as session:
                active_websites = WebsiteRepository.get_all(session, include_inactive=False)
                active_ids = {w.id for w in active_websites}
                website_map = {w.id: w for w in active_websites}

            # Remove jobs for websites no longer active or deleted
            for job_id in list(self.running_jobs):
                if job_id not in active_ids:
                    str_job_id = f"site_{job_id}"
                    if self.scheduler.get_job(str_job_id):
                        self.scheduler.remove_job(str_job_id)
                    self.running_jobs.remove(job_id)
                    logger.info(f"Removed monitoring schedule for inactive/deleted website #{job_id}")

            # Add or update jobs for active websites
            for site_id, site in website_map.items():
                str_job_id = f"site_{site_id}"
                interval_secs = max(10, site.monitoring_interval_seconds or 60)
                existing_job = self.scheduler.get_job(str_job_id)

                if not existing_job:
                    self.scheduler.add_job(
                        self.run_check_for_website,
                        trigger=IntervalTrigger(seconds=interval_secs),
                        id=str_job_id,
                        args=[site_id],
                        max_instances=1,  # Prevent overlapping checks for the same website
                        coalesce=True,
                        name=f"Check '{site.name}' ({site.url})",
                    )
                    self.running_jobs.add(site_id)
                    logger.info(f"Scheduled website #{site_id} ('{site.name}') every {interval_secs}s")

        except Exception as e:
            logger.error(f"Error synchronizing scheduled jobs from database: {e}")

    def start(self):
        """Start the monitoring worker loop."""
        logger.info("=" * 60)
        logger.info("Starting WebPulse Background Monitoring Worker...")
        logger.info("=" * 60)

        # Test DB Connectivity
        ok, msg = test_connection()
        if not ok:
            logger.error(f"Cannot start worker: Database unreachable! ({msg})")
            logger.info("Make sure MySQL is running and credentials in .env are correct.")
            sys.exit(1)

        self.scheduler.start()
        logger.info("APScheduler background scheduler started.")

        # Initial job sync
        self.sync_scheduled_jobs()

        # Handle process termination signals
        def handle_shutdown(signum, frame):
            logger.info("Received termination signal. Shutting down worker gracefully...")
            self._is_running = False
            self.scheduler.shutdown(wait=False)
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        logger.info("Worker is active and monitoring websites. Press Ctrl+C to stop.")

        # Periodic sync loop: check DB for website config changes every 20 seconds
        while self._is_running:
            try:
                time.sleep(20)
                self.sync_scheduled_jobs()
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as loop_err:
                logger.error(f"Unexpected error in worker loop: {loop_err}")
                time.sleep(5)


if __name__ == "__main__":
    worker = MonitorWorker()
    worker.start()
