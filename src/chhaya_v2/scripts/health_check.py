import sys
from chhaya_v2.core.engine.config import settings
from chhaya_v2.core.engine.logger import logger

def main():
    logger.info("running_health_check", environment=settings.environment)

    # 1. Config validation happens automatically on Settings instantiation
    logger.info("config_loaded_successfully")

    # 2. Check for required dependencies / paths (simulated for Phase 0)
    import os
    os.makedirs(settings.chroma_db_dir, exist_ok=True)
    logger.info("storage_paths_verified", chroma_dir=settings.chroma_db_dir)

    # 3. Simple Event Bus sanity check
    from chhaya_v2.core.engine.event_bus import event_bus
    logger.info("event_bus_ready")

    logger.info("health_check_passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
