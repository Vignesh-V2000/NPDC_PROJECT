"""
Station Data Processing - Shared Configuration
This module centralizes configuration for all station data processing scripts
"""

import os
import logging
from pathlib import Path
from django.conf import settings

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
# Use Django's database configuration instead of hard-coded credentials
DB_HOST = os.getenv('NPDC_DB_HOST', 'localhost')
DB_PORT = os.getenv('NPDC_DB_PORT', '5432')
DB_NAME = os.getenv('NPDC_DB_NAME', 'npdc_db')
DB_USER = os.getenv('NPDC_DB_USER', 'postgres')
DB_PASSWORD = os.getenv('NPDC_DB_PASSWORD', 'postgres')

# SQLAlchemy connection string
DB_CONNECTION_STRING = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Psycopg2 connection dict
DB_CONN_PARAMS = {
    'host': DB_HOST,
    'port': DB_PORT,
    'database': DB_NAME,
    'user': DB_USER,
    'password': DB_PASSWORD
}

# ============================================================================
# DATA DIRECTORIES CONFIGURATION
# ============================================================================
# Project root - use Django's BASE_DIR or calculate from script location
if hasattr(settings, 'BASE_DIR'):
    PROJECT_ROOT = settings.BASE_DIR
else:
    # Fallback: go up from stations directory
    PROJECT_ROOT = Path(__file__).parent.parent.parent

# Raw data input directories
RAW_DATA_DIR = PROJECT_ROOT / 'raw_data'
MAITRI_RAW_DIR = RAW_DATA_DIR / 'Maitri'
BHARATI_RAW_DIR = RAW_DATA_DIR / 'DCWIS_NEW'
HIMANSH_RAW_DIR = RAW_DATA_DIR / 'Himansh'
HIMANSH_WATER_RAW_DIR = RAW_DATA_DIR / 'Himalaya' / 'WaterLevel'
HIMADRI_RAW_DIR = RAW_DATA_DIR / 'Himadri' / 'Radiometer'

# Processed data output directories
PROCESS_DATA_DIR = PROJECT_ROOT / 'process_data'
MAITRI_PROCESS_DIR = PROCESS_DATA_DIR / 'Maitri'
BHARATI_PROCESS_DIR = PROCESS_DATA_DIR / 'DCWIS'
HIMANSH_PROCESS_DIR = PROCESS_DATA_DIR / 'Himansh'
HIMANSH_WATER_PROCESS_DIR = PROCESS_DATA_DIR / 'Himalaya' / 'WaterLevel'
HIMADRI_PROCESS_DIR = PROCESS_DATA_DIR / 'Himadri' / 'Radiometer'
HIMADRI_TEMP_PROCESS_DIR = PROCESS_DATA_DIR / 'Himadri' / 'Radiometer' / 'TEMP_ALT'

# ============================================================================
# EMAIL CONFIGURATION (for Himansh & Water Level)
# ============================================================================
HIMANSH_EMAIL_USER = os.getenv('HIMANSH_EMAIL_USER', 'himanshncpor@gmail.com')
HIMANSH_EMAIL_PASS = os.getenv('HIMANSH_EMAIL_PASS', 'default_app_password')
HIMANSH_EMAIL_IMAP = 'imap.gmail.com'

WATER_LEVEL_EMAIL_USER = os.getenv('WATER_LEVEL_EMAIL_USER', 'pnsharmancpor@gmail.com')
WATER_LEVEL_EMAIL_PASS = os.getenv('WATER_LEVEL_EMAIL_PASS', 'default_app_password')
WATER_LEVEL_EMAIL_IMAP = 'imap.gmail.com'

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
# Create logs directory
LOGS_DIR = PROJECT_ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

def get_logger(name, log_file=None):
    """
    Get configured logger for station data processing scripts
    
    Args:
        name: Logger name (usually __name__)
        log_file: Optional log file name (default: {name}.log)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler
        if log_file is None:
            log_file = f'{name.split(".")[-1]}.log'
        file_handler = logging.FileHandler(LOGS_DIR / log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    
    return logger

# ============================================================================
# DATABASE TABLES
# ============================================================================
STATION_TABLES = {
    'maitri': {
        'name': 'Maitri',
        'location': 'Antarctica',
        'table': 'maitri_maitri',
        'columns': ['date', 'temp', 'dew_point', 'rh', 'ap', 'ap_1', 'ap_2', 'ws', 'wd']
    },
    'bharati': {
        'name': 'Bharati',
        'location': 'Antarctica',
        'table': 'imd_bharati',
        'columns': ['obstime', 'tempr', 'ap', 'ws', 'wd', 'rh']
    },
    'himansh': {
        'name': 'Himansh',
        'location': 'Himalaya',
        'table': 'himansh_himansh',
        'columns': ['date', 'acc_preciptn', 'tot_acc_preciptn', 'ap', 'wd', 'wd_6m', 
                   'batt_avg', 'air_temp', 'pannel_temp', 'rh', 's_up', 's_dn', 'l_up', 
                   'l_dn', 'albedo', 'ws', 'ws_6m', 'tcdt', 'sur_temp']
    },
    'himadri': {
        'name': 'Himadri',
        'location': 'Arctic',
        'table': 'himadri_radiometer_surface',
        'columns': ['date', 'temperature', 'relative_humidity', 'air_pressure', 'data_quality']
    }
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def ensure_directories_exist():
    """Create all required data directories"""
    directories = [
        MAITRI_RAW_DIR,
        BHARATI_RAW_DIR,
        HIMANSH_RAW_DIR,
        HIMANSH_WATER_RAW_DIR,
        HIMADRI_RAW_DIR,
        MAITRI_PROCESS_DIR,
        BHARATI_PROCESS_DIR,
        HIMANSH_PROCESS_DIR,
        HIMANSH_WATER_PROCESS_DIR,
        HIMADRI_PROCESS_DIR,
        HIMADRI_TEMP_PROCESS_DIR,
        LOGS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

if __name__ == '__main__':
    print("Station Data Processing Configuration")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Database: {DB_NAME}@{DB_HOST}:{DB_PORT}")
    print(f"Raw Data: {RAW_DATA_DIR}")
    print(f"Process Data: {PROCESS_DATA_DIR}")
    ensure_directories_exist()
    print("✓ All directories created successfully")
