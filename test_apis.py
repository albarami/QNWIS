"""Quick validation of external labour market API clients."""

import asyncio
from pprint import pprint

from src.data.apis.gcc_stat import GCCStatClient
from src.data.apis.lmis_mol_api import LMISAPIClient
from src.data.apis.world_bank import UDCGlobalDataIntegrator


async def _run_in_thread(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


async def test_mol():
    print("Testing LMIS / MoL API...")
    client = LMISAPIClient()
    try:
        df = await _run_in_thread(client.get_qatar_main_indicators)
        if df is None or df.empty:
            print("  ⚠️ No data returned")
        else:
            print(f"  ✅ Rows: {len(df)} | Columns: {list(df.columns)[:5]}")
            pprint(df.head(3).to_dict(orient="records"))
    except Exception as exc:  # pragma: no cover
        print(f"  ❌ Error: {exc}")


async def test_gcc_stat():
    print("\nTesting GCC-STAT API...")
    client = GCCStatClient()
    try:
        df = await _run_in_thread(client.get_unemployment_comparison)
        if df is None or df.empty:
            print("  ⚠️ No data returned")
        else:
            print(f"  ✅ Rows: {len(df)}")
            pprint(df.head(3).to_dict(orient="records"))
    except Exception as exc:  # pragma: no cover
        print(f"  ❌ Error: {exc}")


async def test_world_bank():
    print("\nTesting World Bank API...")
    client = UDCGlobalDataIntegrator()
    try:
        df = await _run_in_thread(
            client.get_indicator,
            indicator="NY.GDP.MKTP.CD",
            countries=["QAT"],
            start_year=2018,
        )
        if df is None or df.empty:
            print("  ⚠️ No data returned")
        else:
            print(f"  ✅ Rows: {len(df)}")
            pprint(df.head(3).to_dict(orient="records"))
    except Exception as exc:  # pragma: no cover
        print(f"  ❌ Error: {exc}")


async def main():
    await test_mol()
    await test_gcc_stat()
    await test_world_bank()


if __name__ == "__main__":
    asyncio.run(main())
