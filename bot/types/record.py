import asyncpg

class UserRecord(asyncpg.Record):

	def __init__(self) -> None:
	    super().__init__()
	    