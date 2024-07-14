from typing import Dict, List, Optional, Any, Tuple
import asyncpg
import asyncio

import discord
from bot.utils.context import CryptoContext
from bot.extensions.coins import Coin
from bot.bot import CryptoBot
import uuid
import orjson
from tabulate import tabulate
import secrets
import re
from bot.utils.dateutils import maybe_dt_format
from bot.fetchers.fetch_token import PriceType
from bot.fetchers.fetch_token_list import Token
from bot.fetchers.crypto_price import get_crypto_price
from bot.utils.asyncpg_to_dict import asyncpg_to_dict
from bot.utils.paginator import DaggyPaginatorClassic
from bot.utils.group_data_numbered import GroupDataNumbered
from discord.ext import commands

class CryptoPortfolioEmbed(GroupDataNumbered[List[Any]]):

	def __init__(self, data, cap: int,portfolio_value: int , total: int) -> None:
	    super().__init__(data, 10)
	    self.capt = cap
	    self.pv = portfolio_value

	def format_into_embed(self, items: List[Any], count: int) -> discord.Embed:
		embed = discord.Embed(title=f"Portfolio Overview:")
		embed.add_field(name="Balance", value=self.capt)
		embed.add_field(name="Total Value of assets", value=self.pv)
		embed.description = "```\n" + tabulate(items, headers=["", "Qty","Price" ,"Value"], tablefmt="grid", numalign="left") + "\n```"
		return embed


class Portfolio(commands.Cog):

	def __init__(self, bot: CryptoBot) -> None:
		self.bot = bot
		cog_a = bot.get_cog("Coin")
		if not cog_a or not isinstance(cog_a, Coin):
			raise Exception("need Coin Cog")
		self.coin_cog: Coin = cog_a

	async def getch_user(self, user_id: int) -> Optional[Dict[str, Any]]:
		a = await self.bot.redis.get(str(user_id))
		if a:
			return orjson.loads(a)
		async with self.bot.acquire() as pool:
			out: asyncpg.Record = await pool.fetchrow("SELECT * FROM users WHERE discord_id = $1", user_id)
			if out:
				a = {}
				for i in out.items():
					a[i[0]] = i[1]
				a["uu"] = str(a["uu"])
				pl = orjson.dumps(dict(a))
				await self.bot.redis.set(str(user_id), pl, ex=86400)
				return dict(out)
		return

	async def check_referral(self, invite: str, new_uuid: str) -> Tuple[bool, str]:
		try:
			async with self.bot.acquire() as pool:
				out: List[asyncpg.Record] = await pool.fetch("SELECT * FROM users WHERE referral = $1;", invite)
				if len(out) < 1:
					return False, "Invalid Referral Code. Not in database"
				user = str(out[0]["uu"])
				await pool.execute("""UPDATE balance  SET "balance" = "balance" + 100 WHERE "user" = $1;""", user)
				await pool.execute("""INSERT INTO referrals ("user", "referred_by") VALUES ($1, $2);""", new_uuid, invite)
				return True, f"Thank you for using the refferal code of {out[0]['discord_id']}(`{out[0]['uu']}`). They have been credited 100$, as will you!"
		except Exception as e:
			return False, f"Error: `{repr(e)}`"

	@commands.command(name="create",aliases=["init", "new"] , help="register yourself as an investor")
	@commands.cooldown(1, 30.0, commands.BucketType.user)
	async def create_portfolio(self, ctx: CryptoContext):

		async def check_r(msg: discord.Message) -> bool:
			if re.match("^[0-9A-Fa-f]+$", msg.content):
				return len(msg.content) == 32
			return False
		us = await self.getch_user(ctx.author.id)
		balance_to_add = 1000
		if us:
			return await ctx.send("Hey you aldready have a CryptoCord account! Please try the `profile` command!")
		uu = str(uuid.uuid4())
		await ctx.send("Welcome to CryptoCord! Lets get you setup. We will start by creating an account")
		code = await ctx.confirm("Were you referred to by another user? If so would you like to use a refferal code?")
		if code:
			stat, cod = await ctx.wait_for_message("Please enter the referral code you have!", ctx.author._user, "Invalid Refferal Code used. Please try again.", check_r)
			if stat is False:
				return await ctx.send("No valid referral code")
			else:
				await ctx.send(f"Valid referral code: `{cod}`")
				status, msg = await self.check_referral(cod, str(uu))
				if status is False:
					return await ctx.send(f"Unable to create profile due to the following error\n{msg}")
				await ctx.send(msg)
				balance_to_add += 100
		try:
			async with self.bot.acquire() as pool:
				await pool.execute(
					"""
					INSERT INTO users (uu, discord_id, premium, contributor, moderator, referral)
					VALUES ($1, $2, false, false, false, $3)
					""",
					uu,
					ctx.author.id,
					secrets.token_hex(16)
				)
				await pool.execute(
					"""
					INSERT INTO balance ("user", "balance")
					VALUES ($1, $2);
					""",
					uu,
					balance_to_add
					)
			return await ctx.send("Thank you so much for joining CryptoCord! To get started maybe try `cryptotutorial` or view your profile with `cryptoprofile`")
		except Exception as e:
			return await ctx.send(f"Error Creating Profile. Please Try again later. Error:\n{e}")

	@commands.command(name="profile", aliases=["userinfo", "ui"], help="View a user's profile")
	@commands.cooldown(1, 30.0, commands.BucketType.user)
	async def user_profile(self, ctx: CryptoContext, *, user: discord.User = None):
		if not user:
			user = ctx.author._user
		data = await self.getch_user(user.id)
		if not data:
			return await ctx.send("We do not have any data for this user.")
		embed = discord.Embed(title=f"Info for {str(user)}")
		embed.description = f"id: `{data['uu']}`"
		embed.add_field(name="Created", value=maybe_dt_format(data["created_at"]), inline=False)
		embed.add_field(name="Referral", value=data["referral"], inline=False)
		embed.set_thumbnail(url=user.avatar)
		embed.set_footer(text="To view your investments and balance use the `portfolio` command")
		return await ctx.send(embed=embed)

	@commands.command(name="dailyanalysis", aliases=["dailys", "dai"], help="get reminded daily about your portfolio")
	@commands.cooldown(1, 30.0, commands.BucketType.user)
	async def daily_analysis_settings(self, ctx: CryptoContext):
		rec = None
		async with self.bot.acquire() as pool:
			rec = await pool.fetchrow("SELECT remind FROM daily_reminder WHERE discord_id = $1;", ctx.author.id)
			if rec is None:
				opt = await ctx.confirm("Would you like to recieve a daily portfolio overview?", user=ctx.author._user)
				await pool.execute('INSERT INTO daily_reminder("discord_id", "remind") VALUES ($1, $2);', ctx.author.id, opt)
				return await ctx.send(f"Updated your settings. Daily Analysis is `{'enabled' if opt else 'disabled'}`")
		opt = rec["remind"]
		return await ctx.send(f"You have daily portfolio analysis dms: `{'enabled' if opt else 'disabled'}`")

	@commands.command(name="balance", aliases=["bal"], help="simple command to view your balance")
	@commands.cooldown(1, 30.0, commands.BucketType.user)
	async def view_bal(self, ctx: CryptoContext):
		await ctx.trigger_typing()
		us  = await self.getch_user(ctx.author.id)
		if not us:
			return await ctx.send("You do not have an account! Create one with `crypto create`!")
		async with self.bot.acquire() as pool:
			bal = await pool.fetchrow('SELECT * FROM balance  WHERE "user" = $1;', us['uu'])
		if bal is None:
			return await ctx.send("No balance found for account. Error. Aborting......")
		embed = discord.Embed(title=f"Balance for user `{ctx.author}`")
		embed.add_field(name="Balance", value=bal["balance"])
		embed.add_field(name="Last updated", value=maybe_dt_format(bal["updated_at"]))
		embed.add_field(name="User", value=str(bal["user"]), inline=False)
		return await ctx.send(embed=embed)

	async def get_crypto_price(self, symbol: str, cid: str) -> PriceType:
		cache_price = await self.bot.redis.get(f"{symbol}_price")
		if cache_price:
			return orjson.loads(str(cache_price))
		coin, pl, data =  await get_crypto_price(self.bot.session, self.bot.config.get("proxies/crypto_price"), cid)
		await self.bot.redis.set(f"{coin}_price", orjson.dumps(data, option=orjson.OPT_NAIVE_UTC), ex=300)
		await self.bot.redis.set(cid, orjson.dumps(pl, option=orjson.OPT_NAIVE_UTC), ex=300)
		return data


	@commands.command(name="portfolio", aliases=["pof", "investments"], help="view all your intvestments and more")
	@commands.cooldown(1, 600.0, commands.BucketType.user)
	async def portfolio_with_prices(self, ctx: CryptoContext):
		await ctx.trigger_typing()
		us  = await self.getch_user(ctx.author.id)
		if not us:
			return await ctx.send("You do not have an account! Create one with `crypto create`!")
		async with self.bot.acquire() as pool:
			qts = await pool.fetch("SELECT * FROM portfolios WHERE uu = $1 ORDER by quantity DESC;", us['uu'])
			bal = await pool.fetchrow('SELECT * FROM balance  WHERE "user" = $1;', us['uu'])
		if len(qts) == 0 or qts is None:
			return await ctx.send("You do not own any crypto atm! Use `crypto buy <asset>` to buy crypto")
		if bal is None:
			return await ctx.send("No balance found for account. Error. Aborting......")
		parsed_dict = [asyncpg_to_dict(rec) for rec in qts]
		sem = asyncio.Semaphore()
		tokens: List[Token] = orjson.loads(await self.bot.redis.get("token_list"))
		curs = []
		for elm in parsed_dict:
			symbol = elm["symbol"]
			tok = self.coin_cog.get_id_from_symbol(symbol, tokens)
			if tok:
				cid = tok['id']
				cache_price = await self.bot.redis.get(f"{symbol}_price")
				if cache_price:
					cache_price: PriceType =  orjson.loads(str(cache_price))
				else:
					async with sem:
						coin, pl, data =  await get_crypto_price(self.bot.session, self.bot.config.get("proxies/crypto_price"), cid)
						await self.bot.redis.set(f"{coin}_price", orjson.dumps(data, option=orjson.OPT_NAIVE_UTC), ex=300)
						await self.bot.redis.set(cid, orjson.dumps(pl, option=orjson.OPT_NAIVE_UTC), ex=300)
						cache_price = data
						await asyncio.sleep(0.5)

				curs.append([symbol, float(elm["quantity"]),cache_price["price"] ,elm["quantity"] * cache_price["price"]])
			else:
				curs.append([symbol, float(elm['quantity']), -1, 0])
		paggy = CryptoPortfolioEmbed(curs, bal['balance'],sum(c[3] for c in curs if isinstance(c[3], float)) , len(curs))
		vv = DaggyPaginatorClassic(ctx, paggy.parsed_embeds, timeout=500.0)
		await ctx.send(embed=vv.embeds[0], view=vv)
		return await vv.wait()

			



def setup(bot: CryptoBot):
	bot.add_cog(Portfolio(bot))
