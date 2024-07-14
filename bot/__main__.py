import aiohttp
from bot.bot import start_stuff
import asyncio
import aioredis
import asyncpg
from aioredis import Redis
from bot.utils.config import Config, load_config

async def main(config: Config):
	redis: Redis = aioredis.from_url(config.get("redis/url"), decode_responses=True)
	async with aiohttp.ClientSession() as e,  asyncpg.create_pool(**config.get_from_parent_raw("postgres")) as pool:
		await start_stuff(e, config, redis, pool)

if __name__ == "__main__":
	config = load_config()
	try:
		asyncio.run(main(config))

	except (KeyboardInterrupt, RuntimeError) as e:
		print(f"Shutdown by user")
