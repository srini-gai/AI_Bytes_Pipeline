from production_queue.cli import main
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
sys.exit(main())
