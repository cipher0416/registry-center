# audit_logger.py
import os
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from common.util.c