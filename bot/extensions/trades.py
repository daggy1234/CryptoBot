import abc
from os import wait

from matplotlib.colors import NoNorm
from numpy import cos
from bot.extensions.portfolio import Portfolio
import discord
import asyncpg
from bot.utils.context import CryptoContext
from bot.bot import CryptoBot
from typing import Any, List, Union, Optional, Dict
import orjson
import uuid
from bot.fetchers.fetch_token_list import Token
from bot.utils.dateutils import maybe_dt_format
from dateutil.parser import parse
from bot.extensions.coins import Coin
from bot.fetchers.fetch_token import PriceType
from bot.fetchers.crypto_price import get_crypto_price
from discord.ext import commands, flags
from bot.utils.flags import PosixLikeFlags
from bot.utils.paginator import DaggyPaginatorClassic
from bot.utils.asyncpg_to_dict import asyncpg_to_dict
from bot.utils.group_data_numbered import GroupDataNumbered



class CryptoBalanceEmbed(GroupDataNumbered["asyncpg.Record"]):

	def __init__(self, data: List[asyncpg.Record], cap: int, total: int) -> None:
	    super().__init__(data, 10)
	    self.capt = cap

	def format_into_embed(self, items: List[asyncpg.Record], count: int) -> discord.Embed:
		embed = discord.Embed(title=f"Portfolio Overview:")
		embed.set_author(name=f"Balance in Account: {self.capt}")
		embed.description = "\n".join([f"**{self.per_page * count + c + 1}**. {record['symbol']}: `{record['quantity']}`" for c, record in enumerate(items)])
		return embed

class TrendingBuyFlags(PosixLikeFlags):
	quantity: Optional[float]

class SellFlags(PosixLikeFlags):
	symbol: Optional[str]
	quantity: Optional[float]

class Trades(commands.Cog):

	def __init__(self, bot: CryptoBot) -> None:
		self.bot = bot
		cog_a = bot.get_cog("Coin")
		if not cog_a or not isinstance(cog_a, Coin):
			raise Exception("need Coin Cog")
		self.coin_cog: Coin = cog_a
		cog_b = bot.get_cog("Portfolio")
		if not cog_b or not isinstance(cog_b, Portfolio):
			raise Exception("Need Portfolio cog")
		self.portfolio_cog : Portfolio = cog_b  # type: ignore

	async def get_crypto_price(self, symbol: str, cid: str) -> PriceType:
		cache_price = await self.bot.redis.get(f"{symbol}_price")
		if cache_price:
			return orjson.loads(str(cache_price))
		coin, pl, data =  await get_crypto_price(self.bot.session, self.bot.config.get("proxies/crypto_price"), cid)
		await self.bot.redis.set(f"{coin}_price", orjson.dumps(data, option=orjson.OPT_NAIVE_UTC), ex=300)
		await self.bot.redis.set(cid, orjson.dumps(pl, option=orjson.OPT_NAIVE_UTC), ex=300)
		return data


	async def resolve_from_name(self, query: str) -> Union[Token, str]:
		tokens: List[Token] = orjson.loads(await self.bot.redis.get("token_list"))
		return self.coin_cog.get_id_from_name(query, tokens)

	@commands.command(name="buy", help="buy a crypto.")
	async def trending_buy(self, ctx: CryptoContext, crypto: str, *, flags: TrendingBuyFlags):
		await ctx.trigger_typing()
		us  = await self.portfolio_cog.getch_user(ctx.author.id)
		if not us:
			return await ctx.send("You do not have an account! Create one with `crypto create`!")
		symbol = await self.resolve_from_name(crypto.lower())
		if isinstance(symbol, str):
			return await ctx.send(symbol)
		conf = await ctx.confirm(f"Would you like us to fetch pricing info for [Id:{symbol['id']}]`name: {symbol['name']}`,`symbol: {symbol['symbol']}` ")
		if not conf:
			return
		await ctx.trigger_typing()
		cache_price_parsed = await self.get_crypto_price(symbol['symbol'], symbol["id"])
		embed = discord.Embed(title=f'**{symbol["name"]}**[{symbol["symbol"]}]', description=f"Pricing data from {maybe_dt_format(parse(str(cache_price_parsed['last_updated'])))}.\nFor more info on the cryspto use `crypto info {symbol['name']}`")
		if p := cache_price_parsed["total_supply"] == -999999999999999999:
			p = "no data"
		else:
			p = f"`{round(cache_price_parsed['percent_change_24h'], 2)}%`"
		embed.add_field(name="Price (USD)", value=f'`${cache_price_parsed["price"]}`')
		embed.add_field(name="Total Supply", value=cache_price_parsed["total_supply"])
		embed.add_field(name="24 Hour % change in Price (USD)",value=p , inline=False)
		await ctx.send(embed=embed)

		async def check_q_msg(msg: discord.Message) -> bool:
			try:
				float(msg.content)
			except ValueError:
				return False
			else:
				return True

		if flags.quantity is None:
			n, a = await ctx.wait_for_message("Pleace specify the quantity you would like to purchase at the price above", ctx.author._user, "Please enter a valid number as your quantity.", check_q_msg)
			if n is False:
				return await ctx.reply("No explicit quantity was passed. Cannot proceed")
			quantity = float(a)
		else:
			quantity = flags.quantity
		cp = cache_price_parsed["price"]
		if not cp:
			return await ctx.send(f"Error occured. No price data found.")

		cost = quantity * cache_price_parsed['price']
		async with self.bot.acquire() as pool:
			bal = await pool.fetchrow('SELECT * FROM balance  WHERE "user" = $1;', us['uu'])
		if bal is None:
			return await ctx.send("No balance found for account. Error. Aborting......")
		if cost > bal['balance']:
			return await ctx.send(f"Insufficient balance. Cost `{cost}` cannot be satisfied with balance of `{bal['balance']}`")
		conf = await ctx.confirm(f"Would you proceed with purchasing. `{quantity}` units of crypto `{symbol['name']}[{symbol['symbol']}]`. Your estimated total is `{cost}`")
		if conf is False:
			return await ctx.send("Cancelled purchase of crypto")
		async with self.bot.acquire() as pool:
			await pool.execute('UPDATE balance SET "balance" = "balance" - $1 WHERE "user" = $2', cost, us['uu'])
			await pool.execute(
			"""
			INSERT INTO portfolios(uu, symbol, quantity)
			VALUES ($1, $2, $3)
			ON CONFLICT("uu", "symbol")
			DO UPDATE SET "quantity" = portfolios.quantity + EXCLUDED.quantity
			""", us['uu'], symbol['symbol'].lower(), quantity)
			out = await pool.fetchval('INSERT INTO transactions("user", symbol, quantity, price) VALUES ($1, $2, $3, $4)', us['uu'], symbol['symbol'].lower(), quantity, cost)
		
		purchase_embed = discord.Embed(title="Success!")
		purchase_embed.description = f"Reciept\n**Symbol**: {symbol['symbol'].lower()}\n**Quantity**: {quantity}\n**Cost**: -{cost}"
		return await ctx.send(embed=purchase_embed)

	@commands.command(name="sell", help="sell a crypto.")
	async def trending_sell(self, ctx: CryptoContext, flags: TrendingBuyFlags):
		await ctx.trigger_typing()
		us  = await self.portfolio_cog.getch_user(ctx.author.id)
		if not us:
			return await ctx.send("You do not have an account! Create one with `crypto create`!")
		async with self.bot.acquire() as pool:
			qts = await pool.fetch("SELECT * FROM portfolios WHERE uu = $1 ORDER by quantity DESC;", us['uu'])
			bal = await pool.fetchrow('SELECT * FROM balance  WHERE "user" = $1;', us['uu'])
		if len(qts) == 0 or qts is None:
			return await ctx.send("You do not own any crypto atm! Use `crypto buy <asset>` to buy crypto")
		if bal is None:
			return await ctx.send("No balance found for account. Error. Aborting......")
		parsed_data = CryptoBalanceEmbed(qts, bal['balance'], len(qts))
		vv = DaggyPaginatorClassic(ctx, parsed_data.parsed_embeds)
		parsed_dict = [asyncpg_to_dict(rec) for rec in qts]
		symbol_list = [elm['symbol'].lower() for elm in parsed_dict]

		async def check_symbol_or_num(msg: discord.Message) -> bool:
			if msg.content.lower() in symbol_list:
				return True
			try:
				int(msg.content)
			except ValueError:
				return False
			return True

		await ctx.send(embed=vv.embeds[0], view=vv)
		status, wait_red = await ctx.wait_for_message("=", ctx.author._user, "Please provide one of the following.\n1) A symbol in your portfolio\n2) A number reffering to the index of the element", check_symbol_or_num, embed=discord.Embed(description="Please send a message containing ONLY the symbol you would like to sell, or the index of the symbol you would like to sell"))
		if status is False:
			return await ctx.send("There was no valid symbol or index provided. Try again")
		symbol = None
		if wait_red.lower() in symbol_list:
			symbol = wait_red
		else:
			try:
				val = int(wait_red)
			except ValueError:
				return await ctx.send("Validation error. Aborting...")
			else:
				if 0 < val <= len(qts):
					symbol = parsed_dict[val-1]['symbol'].lower()

		if not symbol:
			return await ctx.send("No symbol could be parsed")

		crypto = await self.resolve_from_name(symbol.lower())
		if isinstance(crypto, str):
			return await ctx.send(symbol.lower())
		await ctx.trigger_typing()
		cache_price_parsed = await self.get_crypto_price(crypto['symbol'].lower(), crypto["id"])
		embed = discord.Embed(title=f'**{crypto["name"]}**[{crypto["symbol"]}]', description=f"Pricing data from {maybe_dt_format(parse(str(cache_price_parsed['last_updated'])))}.\nFor more info on the cryspto use `crypto info {crypto['name']}`")
		if p := cache_price_parsed["total_supply"] == -999999999999999999:
			p = "no data"
		else:
			p = f"`{round(cache_price_parsed['percent_change_24h'], 2)}%`"
		embed.add_field(name="Price (USD)", value=f'`${cache_price_parsed["price"]}`')
		embed.add_field(name="Total Supply", value=cache_price_parsed["total_supply"])
		embed.add_field(name="24 Hour % change in Price (USD)",value=p , inline=False)
		await ctx.send(embed=embed)
		async def check_q_msg(msg: discord.Message) -> bool:
			try:
				float(msg.content)
			except ValueError:
				return False
			else:
				return True

		if flags.quantity is None:
			n, a = await ctx.wait_for_message("=", ctx.author._user, "Please enter a valid number as your quantity.", check_q_msg, embed=discord.Embed(description=f"Please enter below the quantity you would like to sell"))
			if n is False:
				return await ctx.reply("No explicit quantity was passed. Cannot proceed")
			quantity = float(a)
		else:
			quantity = flags.quantity
		cp = cache_price_parsed["price"]
		if not cp:
			return await ctx.send(f"Error occured. No price data found.")
		try:
			symbol_quantity = symbol_list.index(symbol.lower())
			quantity_pos = parsed_dict[symbol_quantity]['quantity']
		except ValueError:
			return await ctx.send(f"Unable to get quantitiy of `{symbol}` possesed")

		if quantity > quantity_pos:
			return await ctx.send("You cannot sell more than you have. Please Retry sale.")

		cost = quantity * cache_price_parsed['price']

		conf = await ctx.confirm(f"WOuld you like to sell `{quantity}` of  `{crypto['name']}[{crypto['symbol'].lower()}]`. \nThis Sale would result in a credit of `{cost}`.\n Your new total holdings of `{crypto['name']}[{crypto['symbol'].lower()}]` would consist of {quantity_pos - quantity} would be worth `{(quantity_pos - quantity) * cp}`")
		if conf is False:
			return await ctx.send("Aborting Sale......")
		async with self.bot.acquire() as pool:
			await pool.execute('UPDATE balance SET "balance" = "balance" + $1 WHERE "user" = $2', cost, us['uu'])
			await pool.execute(
			"""
			UPDATE portfolios SET "quantity" = "quantity" - $1 WHERE "uu" = $2 AND "symbol" = $3;
			""", quantity,  us['uu'], crypto['symbol'].lower())
			out = await pool.fetchval('INSERT INTO transactions("user", symbol, quantity, price) VALUES ($1, $2, $3, $4)', us['uu'], crypto['symbol'].lower(), -quantity, -cost)
		purchase_embed = discord.Embed(title="Success!")
		purchase_embed.description = f"Reciept\n**Symbol**: {crypto['symbol']}\n**Quantity**: {quantity}\n**Cost**: +{cost}"
		return await ctx.send(embed=purchase_embed)

		


def setup(bot: CryptoBot):
	bot.add_cog(Trades(bot))
