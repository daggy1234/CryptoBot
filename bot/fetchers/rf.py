import asyncio
import aiohttp
from fetch_token import fetch_token


async def main():
	session = aiohttp.ClientSession()
	print(await fetch_token(session, "coinye"))

asyncio.run(main())