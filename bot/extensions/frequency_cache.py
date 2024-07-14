from asyncio import tasks

import orjson
from bot.bot import CryptoBot
from discord.ext import commands, tasks
from bot.fetchers.fetch_top_prices import fetch_top_prices
from bot.fetchers.fetch_exchange_rates import fetch_exchange_rates
from bot.fetchers.fetch_token_list import Token, fetch_token_list

class FrequencyCache(commands.Cog):

	def __init__(self, bot: CryptoBot) -> None:
		self.bot = bot
		self.price_cacher.start()
		self.cache_forex.start()
		self.cache_global.start()
		self.cmc_requests = 0
		self.cmc_daily_limit = 330

	def get_cmc_token(self) -> str:
		token_num = (self.cmc_requests // self.cmc_daily_limit) + 1
		return self.bot.config.get(f"apis/coin_market_cap_{token_num}")


	@tasks.loop(minutes=5)
	async def cache_forex(self):
		tok = self.bot.config.get("apis/nomics")
		rates = await fetch_exchange_rates(self.bot.session, tok)
		await self.bot.redis.set("exchange_rates", orjson.dumps(rates, option=orjson.OPT_NAIVE_UTC), ex=300)
		self.bot.logger.debug("Cached Exchange Rates")

	@cache_forex.before_loop
	async def before_forex(self):
		await self.bot.wait_until_ready()
		self.bot.logger.info("Starting forex caching")

	@tasks.loop(seconds=299)
	async def price_cacher(self):
		tok = self.get_cmc_token()
		token_data = await fetch_top_prices(self.bot.session, tok)
		for token in token_data:
			await self.bot.redis.set(f"{token['symbol']}_price", orjson.dumps(token, option=orjson.OPT_NAIVE_UTC), ex=300)
		self.bot.logger.debug("Cached Prices")

	@price_cacher.before_loop
	async def before_loop(self):
		await self.bot.wait_until_ready()
		self.bot.logger.info("Waiting for ready before price caching")

	@tasks.loop(hours=24.0)
	async def cache_global(self):
		self.cmc_requests = 0
		list_data = await fetch_token_list(self.bot.session)
		await self.bot.redis.set("token_list", orjson.dumps(list_data, option=orjson.OPT_NAIVE_UTC), ex=86400)
		self.bot.logger.debug("Cached token list")

	@cache_global.before_loop
	async def before_cache_global(self):
		await self.bot.wait_until_ready()
		self.bot.logger.info("Bot is ready to start caching token list!")

	def cog_unload(self):
		self.price_cacher.stop()
		self.cache_forex.stop()
		self.cache_global.stop()
		return super().cog_unload()

def setup(bot: CryptoBot):
	bot.add_cog(FrequencyCache(bot))