from typing import Tuple, TypedDict
import aiohttp
from .fetch_token import TokenInfo, parse_json_payload, PriceType, token_to_price_type

async def get_crypto_price(session: aiohttp.ClientSession, url: str  ,coin: str) -> Tuple[str, TokenInfo ,PriceType]:
	out = await session.post(url, json={
			"coin": coin
	})
	json = await out.json()
	payloaded = parse_json_payload(json)
	return payloaded["symbol"],payloaded ,token_to_price_type(payloaded)