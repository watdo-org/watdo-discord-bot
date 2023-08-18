import os

IS_DEV = bool(int(os.environ["IS_DEV"]))
REDIS_URL = str(os.environ["REDIS_URL"])
DISCORD_TOKEN = str(os.environ["DISCORD_TOKEN"])
