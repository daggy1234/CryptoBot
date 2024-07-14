from bot.utils.context import CryptoContext
from bot.bot import CryptoBot
import discord
from bot.utils.numerical_paginator import NumericalPaginator
from bot.fetchers.trending_token import trending_token
from discord.ext import commands
import traceback


class ErrorEmbed(discord.Embed):

	def __init__(self, error: commands.CommandError, description:str):
	    super().__init__(title=f"Error Occured: {error!r}", description=description)


class ErrorHandling(commands.Cog):

	def __init__(self, bot: CryptoBot) -> None:
		self.bot = bot

	@commands.Cog.listener('on_command_error')
	async def error_handler(self, ctx: CryptoContext, error):
		ers = f"{error}"
		traceback_text = "".join(traceback.format_exception(type(error), error, error.__traceback__, 4))
		cog = ctx.cog
		if cog:
			if cog._get_overridden_method(cog.cog_command_error) is not None:
				return
		ignored = (commands.CommandNotFound)
		if isinstance(error, ignored):
			return


	

def setup(bot: CryptoBot):
	bot.add_cog(ErrorHandling(bot))
