import asyncio
from bot.utils.context import CryptoContext
from bot.bot import CryptoBot
import discord
from typing import Optional, Tuple
from discord.ext import commands


class Tutorial(commands.Cog):

	def __init__(self, bot: CryptoBot) -> None:
		self.bot = bot

	async def wait_for_command(self, ctx_og: CryptoContext, command_name: str, *, timeout : float = 180.0)-> Tuple[bool, Optional[CryptoContext]]:

		def check_func(ctx: CryptoContext) -> bool:
			if ctx.command is None:
				return False
			return ctx_og.author.id == ctx.author.id and ctx.command.qualified_name.lower() == command_name and ctx.channel.id == ctx_og.channel.id

		try:
			ctx = await self.bot.wait_for('command_completion', timeout=timeout, check=check_func)
		except asyncio.TimeoutError:
			return False, None
		else:
			return True, ctx

	@commands.command(name="tutorial", help="learn how to use cryptocord with an interactive tutorial")
	async def crypto_tutorial(self, ctx: CryptoContext):
		await ctx.send(embed=discord.Embed(description=f"{ctx.author.mention} Welcome to cryptocord! Lets start off with the basics.\n- Cryptocord is a bot that lets you immerse yourself with crypto\n- View graphs, info and latest crypto data\n- Buy,Sell crypto currencies\n- Create and auction nft's"))
		await ctx.send(embed=discord.Embed(description="Okay lets first view your profile! Use the `crypto profile` command! You have 3minds"))
		stat, ctx_profile = await self.wait_for_command(ctx, 'profile')
		if not stat or not ctx_profile:
			return await ctx.reply("You didn't use `crypto profile`. Try again :(")
		await ctx_profile.reply(embed=discord.Embed(description="Lovely! Now lets explore a crypto you'd like to buy. Use `crypto info <coin>` to view info about a coin!\n(hint: if you don't know of a crpto to view info of one from `crypto trending`)"))
		stat_i, ctx_i = await self.wait_for_command(ctx, 'info')
		if not ctx_i or not stat_i:
			return await ctx.reply("You didn't use `crypto info <coin>`. Try again :(")
		await ctx_i.reply(embed=discord.Embed(description="Lovely! You can view your profile. Understand the info. Now lets buy some crypto. \n. Use `crypto buy <name/symbol>`!\n(use the symbol you got information for)"))
		buy_done, ctx_buy = await self.wait_for_command(ctx, 'buy', timeout=500.0)
		if not buy_done or not ctx_buy:
			return await ctx.reply("You didn't buy any crypto with `crypto buy` :(. Try again later")
		await ctx_buy.reply(embed=discord.Embed(description="Lovely! Okay lets sell some currency!\n`crypto sell <crypto>` command! Sell a quantity of the quantity you just bought!"))
		stat_s, ctx_sell = await self.wait_for_command(ctx, 'sell', timeout=600.0)
		if not stat_s or not ctx_sell:
			return await ctx.reply("You didn't use `crypto sell`. Try again :(")
		await ctx_sell.reply(embed=discord.Embed(description="Okay lets view yourportfolio! This command shows you all of the crypto you own as well your investment values. Use the `crypto portfolio` command!"))
		stat_p, ctx_port = await self.wait_for_command(ctx, 'portoflio')
		if not stat_p or not ctx_port:
			return await ctx.reply("You didn't use `crypto portoflio`. Try again :(")
		await ctx_port.reply(embed=discord.Embed(description="Congratulations! you've completed the tutorial for buying, selling and vieweing your investments!"))




def setup(bot: CryptoBot):
	bot.add_cog(Tutorial(bot))


