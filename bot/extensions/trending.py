from bot.utils.context import CryptoContext
from bot.bot import CryptoBot
import discord
from bot.utils.numerical_paginator import NumericalPaginator
from bot.fetchers.trending_token import trending_token
from discord.ext import commands


class Trending(commands.Cog):

	def __init__(self, bot: CryptoBot) -> None:
		self.bot = bot

	@commands.command(name="trending", help="Get 7 trending cryptocurrencies")
	async def trending_crypto(self, ctx: CryptoContext):
		data = await trending_token(self.bot.session)
		embeds = []
		for coin in data:
			embed = discord.Embed(title=f'Coin: {coin["name"]} [{coin["id"]}]')
			embed.set_thumbnail(url=coin["image"])
			embed.add_field(name="Symbol", value=coin["symbol"])
			embed.add_field(name="Price in BTC", value=coin["price_btc"])
			embed.add_field(name="Market Cap Rank", value=coin["market_cap_rank"], inline=False)
			embeds.append(embed)
		view = NumericalPaginator(ctx, embeds)
		await ctx.send(embed=embeds[0], view=view)

def setup(bot: CryptoBot):
	bot.add_cog(Trending(bot))
