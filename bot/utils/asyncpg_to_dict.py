from typing import Dict,Any
import asyncpg
import uuid


def asyncpg_to_dict(data: asyncpg.Record) -> Dict[str, Any]:
	a = {}
	for i in data.items():
		val = i[1]
		if isinstance(val, uuid.UUID):
			val = str(val)
		a[i[0]] = val
	return a