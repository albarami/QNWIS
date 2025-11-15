"""Inspect PostgreSQL contents for QNWIS datasets."""

import os
from textwrap import dedent

import psycopg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/qnwis")

print("=" * 80)
print("CHECKING POSTGRESQL DATABASE")
print("=" * 80)

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(
            dedent(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
        )
        tables = cur.fetchall()

        print(f"\nFound {len(tables)} tables:")
        for (table_name,) in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]

            cur.execute(f"SELECT * FROM {table_name} LIMIT 1")
            sample = cur.fetchone()

            print(f"\n  📊 {table_name}: {count:,} rows")
            if sample:
                print(f"     Sample columns: {len(sample)} fields")

        print("\n" + "=" * 80)
        print("CHECKING QATAR OPEN DATA")
        print("=" * 80)
        cur.execute(
            dedent(
                """
                SELECT DISTINCT dataset_id, COUNT(*) as count
                FROM qatar_open_data
                GROUP BY dataset_id
                ORDER BY count DESC
                LIMIT 10
                """
            )
        )
        qatar_data = cur.fetchall()
        if qatar_data:
            print("\nTop 10 Qatar datasets:")
            for dataset_id, count in qatar_data:
                print(f"  • {dataset_id}: {count} records")
        else:
            print("No Qatar Open Data records found")

        print("\n" + "=" * 80)
        print("CHECKING GCC-STAT DATA")
        print("=" * 80)
        cur.execute(
            dedent(
                """
                SELECT country, unemployment_rate, labor_force_participation
                FROM gcc_labor_statistics
                WHERE year = 2024
                ORDER BY country
                """
            )
        )
        gcc_data = cur.fetchall()
        if gcc_data:
            print("\nGCC Data (2024):")
            for country, unemp, lfp in gcc_data:
                print(f"  • {country}: {unemp}% unemployment, {lfp}% participation")
        else:
            print("No GCC labor statistics found for 2024")
