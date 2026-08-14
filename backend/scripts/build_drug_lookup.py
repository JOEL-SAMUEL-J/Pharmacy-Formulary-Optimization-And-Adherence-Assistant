from pathlib import Path
from datetime import datetime
import logging
import os
import time

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL, text


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)

# Load your actual environment file
load_dotenv(BASE_DIR / ".env")


DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")


DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)


RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST/rxcui"


# ---------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------

LOG_FILE = LOG_DIR / "drug_lookup.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            LOG_FILE,
            encoding="utf-8",
        )
    ],
)

logger = logging.getLogger(__name__)


def get_pending_rxcuis():
    """
    Return RxCUIs present in formulary_drugs that do not yet
    exist in drug_lookup.
    """
    query = text(
        """
        SELECT DISTINCT fd.rxcui
        FROM formulary_drugs fd
        LEFT JOIN drug_lookup dl
            ON fd.rxcui = dl.rxcui
        WHERE dl.rxcui IS NULL
        ORDER BY fd.rxcui
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(query).fetchall()

    return [row[0] for row in rows]


def fetch_rxnorm_properties(rxcui):
    """
    Fetch basic RxNorm concept properties for one RxCUI.
    """
    url = f"{RXNORM_BASE_URL}/{rxcui}/properties.json"

    response = requests.get(
        url,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    properties = data.get("properties")

    if not properties:
        return None

    return {
        "rxcui": rxcui,
        "drug_display_name": properties.get("name"),
        "term_type": properties.get("tty"),
    }


def insert_lookup_record(
    rxcui,
    drug_display_name,
    term_type,
    lookup_status,
):
    query = text(
        """
        INSERT INTO drug_lookup (
            rxcui,
            drug_display_name,
            term_type,
            lookup_status,
            fetched_at
        )
        VALUES (
            :rxcui,
            :drug_display_name,
            :term_type,
            :lookup_status,
            :fetched_at
        )
        """
    )

    values = {
        "rxcui": rxcui,
        "drug_display_name": drug_display_name,
        "term_type": term_type,
        "lookup_status": lookup_status,
        "fetched_at": datetime.now(),
    }

    with engine.begin() as connection:
        connection.execute(
            query,
            values,
        )


def build_drug_lookup():
    rxcuis = get_pending_rxcuis()

    total = len(rxcuis)

    success_count = 0
    not_found_count = 0
    api_error_count = 0
    other_error_count = 0

    start_time = datetime.now()

    print(f"RxCUIs remaining to process: {total}")

    logger.info("=" * 60)
    logger.info("Drug lookup started")
    logger.info("RxCUIs remaining to process: %s", total)

    for index, rxcui in enumerate(
        rxcuis,
        start=1,
    ):
        try:
            properties = fetch_rxnorm_properties(
                rxcui
            )

            if properties is None:
                insert_lookup_record(
                    rxcui=rxcui,
                    drug_display_name=None,
                    term_type=None,
                    lookup_status="not_found",
                )

                not_found_count += 1

                message = (
                    f"[{index}/{total}] "
                    f"{rxcui} -> not found"
                )

                print(message)
                logger.warning(message)

            else:
                insert_lookup_record(
                    rxcui=rxcui,
                    drug_display_name=(
                        properties["drug_display_name"]
                    ),
                    term_type=(
                        properties["term_type"]
                    ),
                    lookup_status="success",
                )

                success_count += 1

                message = (
                    f"[{index}/{total}] "
                    f"{rxcui} -> "
                    f"{properties['drug_display_name']}"
                )

                print(message)
                logger.info(message)

        except requests.RequestException as error:
            api_error_count += 1

            message = (
                f"[{index}/{total}] "
                f"{rxcui} -> API error: {error}"
            )

            print(message)
            logger.error(message)

        except Exception as error:
            other_error_count += 1

            message = (
                f"[{index}/{total}] "
                f"{rxcui} -> error: {error}"
            )

            print(message)
            logger.exception(message)

        # Small pause so we do not hammer the API
        time.sleep(0.1)

    end_time = datetime.now()
    duration = end_time - start_time

    print("\n=== DRUG LOOKUP SUMMARY ===")
    print("Total attempted:", total)
    print("Successful:", success_count)
    print("Not found:", not_found_count)
    print("API errors:", api_error_count)
    print("Other errors:", other_error_count)
    print("Duration:", duration)
    print("Log file:", LOG_FILE)

    logger.info("=" * 60)
    logger.info("Drug lookup completed")
    logger.info("Total attempted: %s", total)
    logger.info("Successful: %s", success_count)
    logger.info("Not found: %s", not_found_count)
    logger.info("API errors: %s", api_error_count)
    logger.info("Other errors: %s", other_error_count)
    logger.info("Duration: %s", duration)
    logger.info("=" * 60)


if __name__ == "__main__":
    build_drug_lookup()