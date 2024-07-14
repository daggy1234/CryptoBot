from bot.fetchers.fetch_top_prices import PriceType
from datetime import datetime
import aiohttp
from dateutil.parser import parse
from bot.types import LOCALE_TYPE, CURRENCY_TYPE
from typing import Any, Dict, List, Optional, TypedDict

URL = "https://api.coingecko.com/api/v3/coins/"


class TokenAllTime(TypedDict):
	date: datetime
	value: float

class TokenPricing(TypedDict):
	current_price: float
	market_cap: float
	all_time_high: TokenAllTime
	all_time_low: TokenAllTime
	high_24: float
	low_24: float
	circulating_supply: float
	percent_24: float
	date: datetime



class TokenInfo(TypedDict):
	id: str
	symbol: str
	name: str
	hashing_algorithm: str
	image: str
	description: str
	creation_date: datetime
	sentiment_positive: float
	sentiment_negative: float
	homepage: str
	github: List[str]
	market_cap_rank: int
	public_interest_score: float
	liquidity_score: float
	developer_score: float
	community_score: float
	pricing: TokenPricing


def token_to_price_type(tok: TokenInfo) -> PriceType:
	return  {
	"symbol": tok["symbol"].lower(),
	"circulating_supply": int(tok["pricing"]["circulating_supply"]),
	"total_supply": -1,
	"last_updated": tok["pricing"]["date"],
	"price": tok["pricing"]["current_price"],
	"percent_change_24h": tok["pricing"]["percent_24"],
	"market_cap": tok["pricing"]["market_cap"]
	}


def parse_json_payload(json: Any, locale: Optional[LOCALE_TYPE] = "en", currency: Optional[CURRENCY_TYPE] = "usd"):
	if json.get("genesis_date"):
		date = parse(json["genesis_date"])
	else:
		date = datetime.utcnow()

	is_24_data = True

	if json["market_data"]["price_change_percentage_24h"] is None:
		is_24_data = False

	token_price: TokenPricing = {
		"current_price": float(json["market_data"]["current_price"][currency]),
		"market_cap": float(json["market_data"]["market_cap"][currency]),
		"all_time_high": {
			"date": parse(json["market_data"]["ath_date"][currency]),
			"value": float(json["market_data"]["ath"][currency])
		},
		"all_time_low": {
			"date": parse(json["market_data"]["atl_date"][currency]),
			"value": float(json["market_data"]["atl"][currency])
		},
		"high_24": float(json["market_data"]["high_24h"][currency]) if is_24_data else -999999999999999999,
		"low_24": float(json["market_data"]["low_24h"][currency])  if is_24_data else -999999999999999999,
		"circulating_supply": float(json["market_data"]["circulating_supply"]),
		"percent_24": float(json["market_data"]["price_change_percentage_24h"])  if is_24_data else -999999999999999999,
		"date": parse(json["market_data"]["last_updated"])
	}

	data: TokenInfo = {
		"id": json["id"],
		"symbol": json["symbol"],
		"name": json["name"],
		"hashing_algorithm": json["hashing_algorithm"],
		"image": json["image"]["large"],
		"description": json["description"][locale],
		"creation_date": date,
		"sentiment_positive": float(json["sentiment_votes_up_percentage"] or -999999999999999999),
		"sentiment_negative": float(json["sentiment_votes_down_percentage"] or -999999999999999999),
		"homepage": json["links"]["homepage"][0],
		"github": json["links"]["repos_url"]["github"],
		"market_cap_rank": int(json["market_cap_rank"] or -999999999999999999),
		"public_interest_score": float(json["public_interest_score"]),
		"developer_score": float(json["developer_score"]),
		"liquidity_score": float(json["liquidity_score"]),
		"community_score": float(json["community_score"]),
		"pricing": token_price

	}
	return data

async def fetch_token(session: aiohttp.ClientSession, token_id: str, locale: Optional[LOCALE_TYPE] = "en", currency: Optional[CURRENCY_TYPE] = "usd") -> TokenInfo:
	out = await session.get(URL + token_id)
	json = await out.json()
	return parse_json_payload(json, locale=locale, currency=currency)