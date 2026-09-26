import redis

r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

r.delete("test_key")
r.delete("message")

print("cleared")