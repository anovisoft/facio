from __future__ import annotations

import asyncio

from facio_api.mcp.server import run_stdio


def main() -> None:
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
