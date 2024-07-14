import aiohttp
from typing import Dict, List, TypedDict

URL = "https://api.coingecko.com/api/v3/coins/list?include_platform=true"

class Token(TypedDict):
	id: str
	symbol: str
	name: str
	platform: Dict[str, str]

async def fetch_token_list(session: aiohttp.ClientSession) -> List[Token]:
	out = await session.get(URL)
	return await out.json()