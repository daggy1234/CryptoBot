import asyncio
import traceback
from typing import Any, List, Dict
import aiohttp
import asyncpg
import discord
from contextlib import asynccontextmanager
import collections
from bot.utils.config import Config
from discord.ext import commands
import logging
from bot.utils.context import CryptoContext
from aioredis import Redis
from concurrent.futures import ProcessPoolExecutor
from bot.utils.logger import create_logger


extensions = [
	"trending",
	"coins",
	"frequency_cache",
	"portfolio",
	"trades",
	"tutorial"
]


class CryptoBot(commands.AutoShardedBot):

	def __init__(self,config:  Config ,session: aiohttp.ClientSession,redis: Redis, pool: asyncpg.Pool ,**options):
		super().__init__(command_prefix=self.get_prefix, description=config.get("bot/description"),strip_after_prefix=True, **options)
		self.logger: logging.Logger = create_logger("CryptoCord", logging.DEBUG)
		self.discord_logger: logging.Logger = create_logger('discord', logging.INFO)
		self.redis: Redis = redis
		self.pool: asyncpg.Pool = pool
		self.data: Dict[str, str] = {}
		self.session = session
		self.config = config
		self.counter = collections.Counter[str]()
		self.commands_used = collections.Counter[str]()
		self.commands_called: int = 0
		self.process_pool = ProcessPoolExecutor(max_workers=8)

	async def on_socket_response(self, msg: Any):
		if msg["op"] == 0 and (event := msg["t"]) is not None:
			self.counter[event] += 1

	async def get_context(self, message, *, cls=CryptoContext):
	    return await super().get_context(message, cls=cls)


	def load_extensions(self):
		for extension in extensions:
			try:
				self.load_extension(f"bot.extensions.{extension}")
				self.logger.info(f"{extension} was loaded")
			except Exception as e:
				self.logger.critical(f"{extension} could not be loaded: {e}")
		self.load_extension("jishaku")

	async def on_command_completion(self, ctx: CryptoContext):
		self.commands_called += 1
		if ctx.command:
			self.commands_used[ctx.command.qualified_name] += 1

	async def get_prefix(self, message: discord.Message) -> List[str]:
		prefixes = ["crypto", self.config.get("bot/prefix")] + commands.when_mentioned(self, message)
		return prefixes

	@asynccontextmanager
	async def acquire(self):
		async with self.pool.acquire() as connection:
			async with connection.transaction():
				connection: asyncpg.Connection
				yield connection


async def start_stuff(session: aiohttp.ClientSession, config: Config,redis: Redis, pool: asyncpg.Pool) -> None:
	bot = CryptoBot(config=config,  session=session, redis=redis, pool=pool)
	bot.load_extensions()
	try:
		ready_task = asyncio.create_task(bot.wait_until_ready())
		bot_task = asyncio.create_task(bot.start(config.get("bot/token")))
		done, _ = await asyncio.wait((bot_task ,ready_task), return_when=asyncio.FIRST_COMPLETED)
		if bot_task in done:
			error = bot_task.exception()
			bot.logger.critical("Shutdown before starup")
			if error:
				traceback.print_exception(type(error), error, error.__traceback__)
			return
		bot.logger.info(f"Logged in as {bot.user}")
		await bot_task
	except Exception as e:
		bot.logger.critical(f"{type(e).__name__}: {e}")
	finally:
		if not bot.user:
			return
		await session.close()
		bot.logger.info("Bot shut down succesfuly")
