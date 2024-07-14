import asyncio
from io import BytesIO
from typing import List, TypedDict, Any
import aiohttp
from matplotlib.dates import DateFormatter
from matplotlib import pyplot as plt
import functools
from concurrent.futures import ProcessPoolExecutor
import pandas as pd

def process_data_to_graph(data: List[Any], symbol: str, days: str) -> BytesIO:
	eth_df = pd.DataFrame(data, columns=['dateTime', 'price'])
	eth_df.dateTime = pd.to_datetime(eth_df.dateTime, unit='ms')
	byt = BytesIO()
	plt.figure(figsize=(12.8, 9.6))
	plt.plot(eth_df['dateTime'], eth_df['price'])
	plt.title(f"Price for {symbol} over {days} days", fontsize=20)
	plt.xlabel("Time", fontsize=20)
	plt.ylabel("Price in USD", fontsize=20)
	ax = plt.gca()
	ax.xaxis.set_major_formatter(DateFormatter("%b %d %H:%M"))
	plt.savefig(byt)
	byt.seek(0)
	return byt

async def price_graph(loop: asyncio.AbstractEventLoop, session: aiohttp.ClientSession,executor:  ProcessPoolExecutor,url: str  ,symbol: str, fiat: str, days: int) -> BytesIO:
	out = await session.post(url, json={
			"currency": fiat,
			"coin": symbol,
			"days": str(days)
	})
	json = await out.json()
	prices = json["prices"]
	fn = functools.partial(process_data_to_graph, prices, symbol, days)
	exe = await loop.run_in_executor(executor, fn)
	return exe