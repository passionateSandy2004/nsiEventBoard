"""
Start API Only (Without Monitors)
==================================

Lightweight version for Railway deployment.
Serves data from JSON files (populate them separately).
"""

import os
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from api import app

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("=" * 80)
    logger.info("NSE DATA API - LIGHTWEIGHT MODE")
    logger.info("=" * 80)
    logger.info(f"Starting API on port {port}")
    logger.info("Monitors NOT running - serve existing data only")
    logger.info("=" * 80)
    
    app.run(host='0.0.0.0', port=port, debug=False)
