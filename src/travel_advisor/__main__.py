"""
Allow the package to be run directly:

  python -m travel_advisor [--mode stdio|sse|streamable-http] [--host HOST] [--port PORT]
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main())
