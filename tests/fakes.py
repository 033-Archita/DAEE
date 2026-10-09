class FakeRedis:
    def __init__(self):
        self.values, self.lists, self.sets, self.hashes = {}, {}, {}, {}

    def ping(self): return True
    def get(self, key): return self.values.get(key)
    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True
    def delete(self, key):
        existed = key in self.values
        self.values.pop(key, None)
        return int(existed)
    def expire(self, key, seconds): return True
    def llen(self, key): return len(self.lists.get(key, []))
    def lrange(self, key, start, end):
        values = self.lists.get(key, [])
        return values[start:] if end == -1 else values[start:end + 1]
    def rpush(self, key, *values):
        self.lists.setdefault(key, []).extend(values)
        return len(self.lists[key])
    def lpush(self, key, *values):
        self.lists.setdefault(key, [])[:0] = list(values)
        return len(self.lists[key])
    def lpop(self, key, count=None):
        values = self.lists.get(key, [])
        if not values: return None
        if count is None: return values.pop(0)
        result, self.lists[key] = values[:count], values[count:]
        return result
    def smembers(self, key): return self.sets.get(key, set())
    def sadd(self, key, *values):
        before = len(self.sets.setdefault(key, set()))
        self.sets[key].update(values)
        return len(self.sets[key]) - before
    def hgetall(self, key): return self.hashes.get(key, {}).copy()
    def hset(self, key, mapping):
        target = self.hashes.setdefault(key, {})
        new_fields = sum(field not in target for field in mapping)
        target.update(mapping)
        return new_fields
    def hincrby(self, key, field, amount=1):
        target = self.hashes.setdefault(key, {})
        target[field] = str(int(target.get(field, 0)) + amount)
        return int(target[field])
