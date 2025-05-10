#!/usr/bin/env python3

import asyncio
import json
import os
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import argparse
import logging
import subprocess
from functools import wraps
import aiohttp
import yaml
from dotenv import load_dotenv
from prometheus_client import Counter, Gauge, start_http_server
from ratelimit import limits, sleep_and_retry

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('te_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
QUERY_COUNTER = Counter('te_queries_total', 'Total number of queries made')
ERROR_COUNTER = Counter('te_errors_total', 'Total number of errors')
DATA_USAGE_GAUGE = Gauge('te_data_usage_percent', 'Current data usage percentage')
DATA_REMAINING_GAUGE = Gauge('te_data_remaining_gb', 'Remaining data in GB')

@dataclass
class Config:
    """Configuration for the TE Monitor."""
    login_url: str
    query_url: str
    headers: Dict[str, str]
    rate_limit: int = 1  # requests per second
    metrics_port: int = 8000
    health_check_interval: int = 300  # 5 minutes
    retry_attempts: int = 3
    retry_delay: int = 5

    @classmethod
    def from_yaml(cls, path: str) -> 'Config':
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)

def rate_limit_decorator(calls: int, period: int):
    """Decorator for rate limiting API calls."""
    def decorator(func):
        @wraps(func)
        @sleep_and_retry
        @limits(calls=calls, period=period)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class TEMonitor:
    """Main TE Monitor class."""
    
    def __init__(self, config: Config, account_id: str, password: str):
        self.config = config
        self.account_id = account_id
        self.password = password
        self.session: Optional[aiohttp.ClientSession] = None
        self.csrf_token: Optional[str] = None
        self.subscriber_id: Optional[str] = None
        self.last_health_check: datetime = datetime.now()
        self.is_healthy: bool = True

    async def initialize(self):
        """Initialize the monitor."""
        self.session = aiohttp.ClientSession()
        await self.authenticate()

    async def cleanup(self):
        """Cleanup resources."""
        if self.session:
            await self.session.close()

    @rate_limit_decorator(calls=1, period=1)
    async def authenticate(self) -> None:
        """Authenticate with the TE service."""
        try:
            login_data = {
                "acctId": f"FBB{self.account_id}",
                "password": self.password,
                "appLocale": "en-US",
                "isSelfcare": "Y",
                "isMobile": "N",
                "recaptchaToken": ""
            }

            async with self.session.post(
                self.config.login_url,
                headers=self.config.headers,
                json=login_data
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                self.csrf_token = data['body']['token']
                self.subscriber_id = data['body']['subscriber']['subscriberId']
                logger.info("Successfully authenticated")
                
        except Exception as e:
            ERROR_COUNTER.inc()
            logger.error(f"Authentication failed: {str(e)}")
            raise

    @rate_limit_decorator(calls=1, period=1)
    async def query_data(self) -> Dict[str, Any]:
        """Query data from TE service."""
        try:
            query_headers = self.config.headers.copy()
            query_headers.update({
                "Csrftoken": self.csrf_token,
                "Languagecode": "en-US",
                "Connection": "close"
            })

            query_data = {"subscriberId": self.subscriber_id}
            
            async with self.session.post(
                self.config.query_url,
                headers=query_headers,
                json=query_data
            ) as response:
                response.raise_for_status()
                data = await response.json()
                QUERY_COUNTER.inc()
                return data
                
        except Exception as e:
            ERROR_COUNTER.inc()
            logger.error(f"Query failed: {str(e)}")
            raise

    async def process_data(self, data: Dict[str, Any]) -> None:
        """Process and update metrics from query data."""
        try:
            for item in data['body']:
                total = item.get('total', 1)
                remain = item.get('remain', 0)
                used_percentage = round(((total - remain) / total) * 100, 2)
                
                DATA_USAGE_GAUGE.set(used_percentage)
                DATA_REMAINING_GAUGE.set(remain)
                
                message = f"{used_percentage}%, {remain} GB remaining."
                logger.info(message)
                
                if os.getenv('TE_NOTIFY_ID'):
                    await self.send_notification(message)
                    
        except Exception as e:
            ERROR_COUNTER.inc()
            logger.error(f"Data processing failed: {str(e)}")

    async def send_notification(self, message: str) -> None:
        """Send notification using the notify command."""
        try:
            process = await asyncio.create_subprocess_exec(
                'notify', '-silent', '-id', os.getenv('TE_NOTIFY_ID'),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.communicate(input=message.encode())
        except Exception as e:
            ERROR_COUNTER.inc()
            logger.error(f"Notification failed: {str(e)}")

    async def health_check(self) -> None:
        """Perform health check of the service."""
        try:
            await self.query_data()
            self.is_healthy = True
            self.last_health_check = datetime.now()
        except Exception as e:
            self.is_healthy = False
            logger.error(f"Health check failed: {str(e)}")

    async def run(self) -> None:
        """Main run loop."""
        try:
            # Start Prometheus metrics server
            start_http_server(self.config.metrics_port)
            
            while True:
                try:
                    data = await self.query_data()
                    await self.process_data(data)
                    
                    # Perform health check periodically
                    if (datetime.now() - self.last_health_check).seconds >= self.config.health_check_interval:
                        await self.health_check()
                        
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    if not self.is_healthy:
                        await self.authenticate()
                        
                await asyncio.sleep(self.config.rate_limit)
                
        except asyncio.CancelledError:
            logger.info("Shutting down...")
        finally:
            await self.cleanup()

def handle_interrupt(signum: int, frame: Optional[object]) -> None:
    """Handle interrupt signal gracefully."""
    logger.info("\nExiting gracefully...")
    sys.exit(0)

def get_credentials(args: argparse.Namespace) -> Tuple[str, str]:
    """Get credentials from either command line args or environment variables."""
    account_id = args.acctId or os.getenv('TE_ACCOUNT_ID')
    password = args.password or os.getenv('TE_PASSWORD')
    
    if not account_id or not password:
        logger.error("Credentials not provided. Please provide them either via command line or .env file")
        sys.exit(1)
        
    return account_id, password

async def main() -> None:
    """Main entry point of the script."""
    parser = argparse.ArgumentParser(
        description="TE Internet Monitor - A professional monitoring tool for TE Internet usage.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=4000,
        help="Interval in seconds between each query"
    )
    parser.add_argument(
        "--acctId",
        type=str,
        help="TE account ID (can also be set via TE_ACCOUNT_ID environment variable)"
    )
    parser.add_argument(
        "--password",
        type=str,
        help="TE password (can also be set via TE_PASSWORD environment variable)"
    )
    args = parser.parse_args()

    # Get credentials
    account_id, password = get_credentials(args)

    # Load configuration
    config = Config.from_yaml(args.config)
    config.rate_limit = args.interval

    # Set up signal handler
    signal.signal(signal.SIGINT, handle_interrupt)

    # Create and run monitor
    monitor = TEMonitor(config, account_id, password)
    await monitor.initialize()
    await monitor.run()

if __name__ == "__main__":
    asyncio.run(main())