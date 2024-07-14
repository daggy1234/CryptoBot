from discord.ext.commands import FlagConverter


class PosixLikeFlags(FlagConverter, delimiter=' ', prefix='--', case_insensitive=True):
	pass
