from typing import Any, Generic, List, Iterator
from typing import TypeVar

import discord
from discord.embeds import Embed
from pandas._libs.tslibs.nattype import iNaT

T = TypeVar('T')

class GroupDataNumbered(Generic[T]):

	def __init__(self, data: List[T], per_page: int) -> None:
	    self.data: List[T] = data
	    self.per_page : int = per_page

	def format_into_embed(self, items: List[T], count: int) -> discord.Embed:
		return discord.Embed()

	def divide_data(self) -> Iterator[List[T]]:
		data: List[T] = self.data
		for i in range(0,len(data), self.per_page):
			yield data[i:i + self.per_page]

	def assemble_data_into_embeds(self) -> List[discord.Embed]:
		embeds = []
		assembled_data = self.divide_data()
		for count, frame in enumerate(assembled_data):
			embeds.append(self.format_into_embed(frame, count))
		return embeds

	@property
	def parsed_embeds(self) -> List[discord.Embed]:
		return self.assemble_data_into_embeds();

