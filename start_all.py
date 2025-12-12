"""
Start All Monitors and API
===========================

This script starts all 4 monitors and the Flask API in separate threads.
Designed for Docker/Railway deployment.
"""

import threading
import time
import sys
from event_calendar_monitor import EventCalendarMonitor
from announcements_monitor import AnnouncementsMonitor
from crd_monitor import CRDMonitor
from credit_rating_monitor import CreditRatingMonitor
from api import app
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_event_calendar_monitor():
    """Run event calendar monitor"""
    try:
        logger.info("Starting Event Calendar Monitor...")
        monitor = EventCalendarMonitor(headless=True)
        monitor.start_monitoring(interval_minutes=5)
    except Exception as e:
        logger.error(f"Event Calendar Monitor error: {e}")


def run_announcements_monitor():
    """Run announcements monitor (Equity)"""
    try:
        logger.info("Starting Announcements Monitor (Equity)...")
        monitor = AnnouncementsMonitor(headless=True, market_type='Equity')
        monitor.start_monitoring(interval_minutes=5)
    except Exception as e:
        logger.error(f"Announcements Monitor error: {e}")


def run_crd_monitor():
    """Run CRD monitor"""
    try:
        logger.info("Starting CRD Monitor...")
        monitor = CRDMonitor(headless=True)
        monitor.start_monitoring(interval_minutes=5)
    except Exception as e:
        logger.error(f"CRD Monitor error: {e}")


def run_credit_rating_monitor():
    """Run credit rating monitor (Equity)"""
    try:
        logger.info("Starting Credit Rating Monitor (Equity)...")
        monitor = CreditRatingMonitor(headless=True, market_type='Equity')
        monitor.start_monitoring(interval_minutes=5)
    except Exception as e:
        logger.error(f"Credit Rating Monitor error: {e}")


def run_api():
    """Run Flask API"""
    try:
        import os
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Flask API on port {port}...")
        # Wait a bit for monitors to create initial data
        time.sleep(5)
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"API error: {e}")


def main():
    """Start all services"""
    logger.info("=" * 80)
    logger.info("NSE DATA SCRAPER - STARTING ALL SERVICES")
    logger.info("=" * 80)
    
    # Create threads for each monitor
    threads = [
        threading.Thread(target=run_event_calendar_monitor, daemon=True, name="EventCalendar"),
        threading.Thread(target=run_announcements_monitor, daemon=True, name="Announcements"),
        threading.Thread(target=run_crd_monitor, daemon=True, name="CRD"),
        threading.Thread(target=run_credit_rating_monitor, daemon=True, name="CreditRating"),
        threading.Thread(target=run_api, daemon=False, name="API")  # Not daemon so it keeps running
    ]
    
    # Start all threads
    for thread in threads:
        logger.info(f"Starting thread: {thread.name}")
        thread.start()
        time.sleep(2)  # Stagger starts
    
    logger.info("=" * 80)
    logger.info("ALL SERVICES STARTED")
    logger.info("API available at: http://0.0.0.0:5000")
    logger.info("=" * 80)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(60)
            # Check if threads are alive
            for thread in threads:
                if not thread.is_alive() and thread.name != "API":
                    logger.warning(f"Thread {thread.name} has stopped!")
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()

