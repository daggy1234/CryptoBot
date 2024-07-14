import aiohttp
from typing import Dict, List, TypedDict

URL = "https://api.coingecko.com/api/v3/search/trending"

class SearchToken(TypedDict):
	id: str
	coin_id: int
	name: str
	symbol: str
	market_cap_rank: int
	image: str
	price_btc: float

async def trending_token(session: aiohttp.ClientSession) -> List[SearchToken]:
	out = await session.get(URL)
	json = await out.json()
	print(json)
	data: List[SearchToken] = []
	for parent in json["coins"]:
		item = parent["item"]
		data.append({
			"id": item["id"],
			"coin_id": int(item["coin_id"]),
			"name": item["name"],
			"symbol": item["symbol"],
			"image": item["large"],
			"market_cap_rank": int(item["market_cap_rank"]),
			"price_btc": float(item["price_btc"])
		})
	return data