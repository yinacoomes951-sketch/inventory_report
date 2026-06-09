from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


def main() -> None:
    load_env()
    database_url = os.getenv("AI_INVENTORY_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not configured")

    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.connect() as conn:
        candidates = conn.execute(
            text(
                """
                select table_schema, table_name
                from information_schema.tables
                where table_name ilike :inventory_pattern
                   or table_name ilike :kd_pattern
                order by table_schema, table_name
                limit 20
                """
            ),
            {"inventory_pattern": "%inventory%sku%calc%", "kd_pattern": "%ads_lx_kd%"},
        ).mappings().all()

        output = {"candidates": [dict(row) for row in candidates]}

        try:
            latest = conn.execute(
                text(
                    """
                    with latest as (
                        select max(insert_time) as ts
                        from lx_ads.ads_lx_kd_inventory_sku_calc
                    )
                    select (select ts::text from latest) as latest_ts,
                           count(*) as total_rows
                    from lx_ads.ads_lx_kd_inventory_sku_calc t, latest
                    where t.insert_time = latest.ts
                    """
                )
            ).mappings().first()
            output["latest"] = dict(latest) if latest else None
            warnings = conn.execute(
                text(
                    """
                    with latest as (
                        select max(insert_time) as ts
                        from lx_ads.ads_lx_kd_inventory_sku_calc
                    )
                    select coalesce("备货预警", '') as warning,
                           count(*) as count
                    from lx_ads.ads_lx_kd_inventory_sku_calc t, latest
                    where t.insert_time = latest.ts
                    group by 1
                    order by count desc
                    limit 20
                    """
                )
            ).mappings().all()
            output["restock_warnings"] = [dict(row) for row in warnings]
        except Exception as exc:  # noqa: BLE001 - probe should report DB privilege details.
            output["latest_error"] = str(exc).splitlines()[0]

    print(json.dumps(output, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
