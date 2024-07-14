from datetime import datetime
from typing import TypedDict, List
import aiohttp
from dateutil.parser import parse

URL = "https://api.nomics.com/v1/exchange-rates?key="

class ExchangeRate(TypedDict):
	currency: str
	rate: float
	timestamp: datetime

async def fetch_exchange_rates(session: aiohttp.ClientSession, token: str) -> List[ExchangeRate]:
	out = await session.get(URL + token)
	json = await out.json()
	exc_rates: List[ExchangeRate] = []
	for item in json:
		exc_rates.append({
			"currency": item["currency"],
			"rate": float(item["rate"]),
			"timestamp": parse(item["timestamp"])
		})
	return exc_rates