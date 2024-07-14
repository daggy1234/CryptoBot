from bot.fetchers.fetch_top_prices import PriceType
from datetime import timedelta
from dateutil.parser import parse
from typing import List, Optional, Union
from bot.utils.context import CryptoContext
from bot.bot import CryptoBot
from bot.fetchers.candlestick_fetch import candlestick_graph
from bot.fetchers.time_series_graph import price_graph
from discord.ext import commands
from bot.fetchers.fetch_token import TokenInfo, fetch_token, token_to_price_type
from bot.fetchers.fetch_token_list import Token
import discord
import difflib
import orjson
from bot.utils.dateutils import maybe_dt_format
from bot.utils.flags import PosixLikeFlags
from markdownify import markdownify as md

class TrendingBuyFlags(PosixLikeFlags):
	time: str = "1d"

class CryptoBuyFlags(PosixLikeFlags):
	days: int = 1

class Coin(commands.Cog):

	def __init__(self, bot: CryptoBot) -> None:
		self.bot = bot


	def get_id_from_symbol(self, query: str, tokens: List[Token]) -> Optional[Token]:
		for token in tokens:
			parts = token["name"], token["id"], token["symbol"]
			if any(part.lower() == query for part in parts):
				return token

	def get_id_from_name(self, query: str, tokens: List[Token]) -> Union[Token, str]:
		match_list = []
		found_match = None
		for token in tokens:
			parts = token["name"], token["id"], token["symbol"]
			if any(part.lower() == query for part in parts):
				found_match = token
				break
			match_list.extend(parts)
		if found_match is None:
			close_matches = difflib.get_close_matches(query, match_list, n=1)
			if len(close_matches) > 0:
				return f"No exact results found. Closest match was `{close_matches[0]}`"
			else:
				return f"No matches found. Please check your seach query and try again."
		return found_match

	def embed_list_from_token(self, tok: TokenInfo) -> List[discord.Embed]:
		embed_list = []
		embed_a = discord.Embed(title=f'**{tok["name"]}**[{tok["symbol"]}]', description=md(tok["description"]))
		embed_a.add_field(name="Hashing Algo", value=tok["hashing_algorithm"])
		embed_a.add_field(name="Creation Date", value=maybe_dt_format(tok["creation_date"]))
		embed_a.add_field(name="Homepage", value=tok["homepage"] if tok["homepage"] else "Nan", inline=False)
		embed_a.set_thumbnail(url=tok["image"])
		embed_list.append(embed_a)
		embed_b = discord.Embed(title=f'**{tok["name"]}**[{tok["symbol"]}]')
		embed_b.add_field(name="Market Cap Rank", value=tok["market_cap_rank"])
		embed_b.add_field(name="Public Intrest Score",value=tok["public_interest_score"])
		embed_b.add_field(name="Liquidity Score", value=tok["liquidity_score"], inline=False)
		embed_b.add_field(name="Developer Score", value=tok["developer_score"])
		embed_b.add_field(name="Community Score", value=tok["community_score"])
		embed_list.append(embed_b)
		embed_c = discord.Embed(title=f'**{tok["name"]}**[{tok["symbol"]}]')
		embed_c.add_field(name="Price (USD)", value=f'`${tok["pricing"]["current_price"]}`')
		embed_c.add_field(name="Circulating Supply", value=tok["pricing"]["circulating_supply"])
		if p := tok['pricing']['percent_24'] == -999999999999999999:
			p = "no data"
		else:
			p = f"`{round(p, 2)}%`"
		embed_c.add_field(name="24 Hour % change in Price (USD)", value=p, inline=False)
		embed_c.add_field(name="All Time High", value=f"`${tok['pricing']['all_time_high']['value']}` on {maybe_dt_format(tok['pricing']['all_time_high']['date'])}", inline=False)
		embed_c.add_field(name="All Time Low", value=f"`${tok['pricing']['all_time_low']['value']}` on {maybe_dt_format(tok['pricing']['all_time_low']['date'])}", inline=False)
		embed_list.append(embed_c)
		return embed_list



	async def getch(self, query: str) -> TokenInfo:
		cache_resolve: Optional[str] = await self.bot.redis.get(query)
		if cache_resolve:
			data: TokenInfo = orjson.loads(cache_resolve)
		else:
			data: TokenInfo = await fetch_token(self.bot.session, query, "en", "usd")
			await self.bot.redis.set(query, orjson.dumps(data, option=orjson.OPT_NAIVE_UTC), ex=300)
		return data

	@commands.command(name="info",aliases=["i","search", "query"] ,help="Get info about a cryto using it's symbol, name or id")
	@commands.cooldown(1, 30.0, commands.BucketType.user)
	async def crypto_search(self, ctx: CryptoContext, *, query: str):
		await ctx.trigger_typing()
		tokens: List[Token] = orjson.loads(await self.bot.redis.get("token_list"))
		found_match = self.get_id_from_name(query.lower(), tokens)
		if isinstance(found_match, str):
			return await ctx.send(found_match)
		data = await self.getch(found_match['id'])
		embeds = self.embed_list_from_token(data)
		return await ctx.send(embeds=embeds) #type: ignore

	@commands.command(name="candle",aliases=["can","ohlc"] ,help="Get info about a cryto using it's symbol, name or id")
	@commands.cooldown(1, 60.0, commands.BucketType.user)
	async def crypto_graph_candle(self, ctx: CryptoContext, query: str, *, flags: TrendingBuyFlags):
		query = query.lower()
		acceptable_times = ["10m","1h","1d", "1m", "3m","6m", "1y"]
		relevant_delta = [timedelta(minutes=10), timedelta(minutes=60), timedelta(hours=24), timedelta(days=30), timedelta(days=120), timedelta(days=160), timedelta(weeks=52)]
		interval_durations = ["1m", "1m", "30m", "12h", "3d", "3d", "1w"]
		time = flags.time
		if time not in acceptable_times:
			return await ctx.send(f"Time must be one of `{','.join(acceptable_times)}`")
		i = acceptable_times.index(time)
		await ctx.trigger_typing()
		tokens: List[Token] = orjson.loads(await self.bot.redis.get("token_list"))
		found_match = self.get_id_from_name(query, tokens)
		if isinstance(found_match, str):
			return await ctx.send(found_match)
		try:
			out = await candlestick_graph(self.bot.loop, self.bot.session, self.bot.process_pool, found_match["symbol"], interval_durations[i], relevant_delta[i], acceptable_times[i])
		except Exception as e:
			return await ctx.send(f"For symbol `{found_match['symbol']}`, graph data isn't available.")
		return await ctx.send(file=discord.File(fp=out, filename=f"ohlc-{found_match['symbol']}.png"))

	@commands.command(name="price_graph",aliases=["graphprice","pricegraph"] ,help="Get info about a cryto using it's symbol, name or id")
	@commands.cooldown(1, 60.0, commands.BucketType.user)
	async def crypto_graph_price(self, ctx: CryptoContext, query: str,  *, flags: CryptoBuyFlags):
		await ctx.trigger_typing()
		tokens: List[Token] = orjson.loads(await self.bot.redis.get("token_list"))
		found_match = self.get_id_from_name(query, tokens)
		if isinstance(found_match, str):
			return await ctx.send(found_match)
		try:
			out = await price_graph(self.bot.loop, self.bot.session, self.bot.process_pool,self.bot.config.get("proxies/time_series_graph") ,found_match["id"], "USD", flags.days)
		except Exception as e:
			print(e)
			return await ctx.send(f"For symbol `{found_match['symbol']}`, graph data isn't available.")
		return await ctx.send(file=discord.File(fp=out, filename=f"ohlc-{found_match['symbol']}.png"))
	
	# @flags.add_flag("--days", type=int, default=1)
	# @flags.command(name="candle",aliases=["can","ohlc"] ,help="Get info about a cryto using it's symbol, name or id")
	# async def crypto_graph_price(self, ctx: CryptoContext, *, query: str, **flags):
	# 	await ctx.trigger_typing()
	# 	tokens: List[Token] = orjson.loads(await self.bot.redis.get("token_list"))
	# 	found_match = self.get_id_from_name(query.lower(), tokens)
	# 	if isinstance(found_match, str):
	# 		return await ctx.send(found_match)
	# 	try:
	# 		out = await candlestick_graph(self.bot.loop, self.bot.session, self.bot.process_pool, found_match["symbol"], "30m", timedelta(hours=24))
	# 	except Exception as e:
	# 		print(e)
	# 		return await ctx.send(f"For symbol `{found_match['symbol']}`, graph data isn't available.")
	# 	return await ctx.send(file=discord.File(fp=out, filename=f"ohlc-{found_match['symbol']}.png"))


	@commands.command(name="price", aliases=["p"], help="Get realtime info about a crypto's price")
	@commands.cooldown(1, 30.0, commands.BucketType.user)
	async def crypto_price(self, ctx: CryptoContext, *, query: str):
		await ctx.trigger_typing()
		tokens: List[Token] = orjson.loads(await self.bot.redis.get("token_list"))
		try_match = self.get_id_from_name(query.lower(), tokens)
		if isinstance(try_match, str):
			return await ctx.send(try_match)
		symbol = try_match["symbol"]
		cache_price = await self.bot.redis.get(f"{symbol}_price")
		cache_price_parsed: Optional[PriceType] = None
		if not cache_price:
			print("no Cp")
			try:
				tok_data = await self.getch(try_match["id"])
				cache_price_parsed =  token_to_price_type(tok_data)
			except:
				pass
		else:
			cache_price_parsed = orjson.loads(str(cache_price))
		if not cache_price_parsed:
			return await ctx.send("Pricing not available atm for this token :(")
		embed = discord.Embed(title=f'**{try_match["name"]}**[{try_match["symbol"]}]', description=f"Pricing data from {maybe_dt_format(parse(str(cache_price_parsed['last_updated'])))}.\nFor more info on the crypto use `crypto info {query}`")
		if p := cache_price_parsed["total_supply"] == -999999999999999999:
			p = "no data"
		else:
			p = f"`{round(cache_price_parsed['percent_change_24h'], 2)}%`"
		embed.add_field(name="Price (USD)", value=f'`${cache_price_parsed["price"]}`')
		embed.add_field(name="Total Supply", value=cache_price_parsed["total_supply"])
		embed.add_field(name="24 Hour % change in Price (USD)",value=p , inline=False)
		return await ctx.send(embed=embed)



	

	def cog_unload(self):
		return super().cog_unload()

	


def setup(bot: CryptoBot):
	bot.add_cog(Coin(bot))
		