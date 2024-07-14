from datetime import datetime
import aiohttp
from dateutil.parser import parse
from typing import Dict, List, Optional, TypedDict

URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?limit=200&CMC_PRO_API_KEY="

class PriceType(TypedDict):
	symbol: str
	circulating_supply: int
	total_supply: int
	last_updated: datetime
	price: float
	percent_change_24h: float
	market_cap: float


async def fetch_top_prices(session: aiohttp.ClientSession, coinmarketcap_token: str) -> List[PriceType]:
	out = await session.get(URL + coinmarketcap_token)
	json = await out.json()
	coin_data: List[PriceType] = []
	for sub_json in json["data"]:
		price_type: PriceType = {
			"symbol": sub_json["symbol"].lower(),
			"circulating_supply": int(sub_json["circulating_supply"]),
			"total_supply": int(sub_json["total_supply"]),
			"last_updated": parse(sub_json["last_updated"]),
			"price": float(sub_json["quote"]["USD"]["price"]),
			"market_cap": float(sub_json["quote"]["USD"]["market_cap"]),
			"percent_change_24h": float(sub_json["quote"]["USD"]["percent_change_24h"])
		}
		coin_data.append(price_type)
	return coin_data