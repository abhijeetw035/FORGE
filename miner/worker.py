import time
import redis
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Miner worker starting...")
    
    r = redis.Redis(host='redis', port=6379, decode_responses=True)
    
    while True:
        try:
            task = r.blpop('task_queue', timeout=5)
            if task:
                logger.info(f"Processing task: {task[1]}")
            else:
                logger.debug("No tasks in queue")
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
