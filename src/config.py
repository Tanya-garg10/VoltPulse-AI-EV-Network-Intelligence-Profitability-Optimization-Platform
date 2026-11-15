"""VoltPulse AI - central configuration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
WAREHOUSE_DIR = ROOT / "data" / "warehouse"
REPORTS_DIR = ROOT / "reports"

SWAP_EVENTS_CSV = RAW_DIR / "swap_events.csv"
STATIONS_CSV = RAW_DIR / "stations.csv"
RIDERS_CSV = RAW_DIR / "riders.csv"
FLEET_CSV = RAW_DIR / "fleet_partners.csv"
TICKETS_CSV = RAW_DIR / "support_tickets.csv"
CONTEXT_CSV = RAW_DIR / "city_daily_context.csv"

PARQUET_DIR = PROCESSED_DIR / "parquet"
DB_PATH = WAREHOUSE_DIR / "voltpulse.duckdb"

CITIES = ["Bengaluru", "Delhi NCR", "Hyderabad", "Pune", "Mumbai", "Jaipur"]

CHUNK_SIZE = 200_000
DATA_END_DATE = None  # inferred from data
