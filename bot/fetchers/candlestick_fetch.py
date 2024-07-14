import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import List, TypedDict, Any
import aiohttp
import mplfinance as mpf
import functools
from concurrent.futures import ProcessPoolExecutor
import pandas as pd

def process_data_to_graph(data: List[Any], symbol: str, time_str: str) -> BytesIO:
	print(data[0], data[1])
	eth_df = pd.DataFrame(data, columns=['dateTime', 'open', 'high', 'low', 'close', 'volume', 'closeTime', 'quoteAssetVolume', 'numberOfTrades', 'takerBuyBaseVol', 'takerBuyQuoteVol', 'ignore'])
	eth_df.dateTime = pd.to_datetime(eth_df.dateTime, unit='ms')
	eth_df.closeTime = pd.to_datetime(eth_df.closeTime, unit='ms')
	eth_df.set_index('dateTime', inplace=True)
	byt = BytesIO()
	mpf.plot(eth_df,title=f"\n{time_str} Candle for {symbol}", ylabel="Price in USD", ylabel_lower="Volume" , type='candle',volume=True, style='yahoo', savefig=byt)
	byt.seek(0)
	return byt





async def candlestick_graph(loop: asyncio.AbstractEventLoop, session: aiohttp.ClientSession,executor:  ProcessPoolExecutor,symbol: str, interval: str, prev: timedelta, time_str: str) -> BytesIO:
		timestamp = int((datetime.now(tz=timezone.utc) - prev).timestamp() * 1000)
		URL= f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}USDT&interval={interval}&startTime={timestamp}"
		print(URL)
		data = await session.get(URL)
		json = await data.json()
		try:
			json["code"]
		except:
			pass
		else:
			raise Exception("No Valid Data")
		new_list = []
		for item in json:
			new_list.append([
					item[0],
					float(item[1]),
					float(item[2]),
					float(item[3]),
					float(item[4]),
					float(item[5]),
					item[6],
					float(item[7]),
					float(item[8]),
					item[9],
					float(item[10]),
					float(item[11])
				])
		fn = functools.partial(process_data_to_graph, new_list, symbol, time_str)
		exe = await loop.run_in_executor(executor, fn)
		return exe


