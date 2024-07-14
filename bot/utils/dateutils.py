
from datetime import datetime
from typing import Any, Union
import discord
from dateutil.parser import parse

def maybe_dt_format(entry: Union[str, datetime]) -> str:
	if isinstance(entry, str):
		entry = parse(entry)
	return discord.utils.format_dt(entry)