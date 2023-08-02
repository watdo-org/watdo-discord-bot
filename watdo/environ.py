import os

IS_DEV = bool(int(os.environ["IS_DEV"]))
DISCORD_TOKEN = str(os.environ["DISCORD_TOKEN"])
REDISHOST = str(os.environ["REDISHOST"])
REDISPORT = int(os.environ["REDISPORT"])
REDISUSER = str(os.environ["REDISUSER"])
REDISPASSWORD = str(os.environ["REDISPASSWORD"])
