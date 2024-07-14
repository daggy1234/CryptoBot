from typing import Any, Dict, TypedDict, MutableMapping, Union
import toml

class ConfigMissing(Exception):

	def __init__(self, key: str, *args: object) -> None:
	    super().__init__(*args)
	    self.message = f"Missing key {key}"


class Config:
	def __init__(self, data: MutableMapping[str, Any]) -> None:
	    self._data = data

	def get_from_parent_raw(self, key: str) -> Dict[str, Any]:
		try:
			return self._data[key]
		except KeyError:
			raise ConfigMissing(key)


	def get(self, key: str) -> str:
		try:
			base_key: Union[Dict, str] = dict(self._data)
			key_list = key.split("/")
			for key in key_list:
				base_key = base_key[key] # type: ignore
			
			if not isinstance(base_key, str):
				raise Exception("")
			return base_key
		except KeyError:
			raise ConfigMissing(key)

	def remove_credentials(self, input_st: str) -> str:
		for k,v in self._data.items():
			input_st = input_st.replace(v, f"[Ommited {k}]")
		return input_st

def load_config() -> Config:
	with open("config.toml", "r") as file:
		raw = toml.load(file)
		print(raw)
	return Config(raw)


