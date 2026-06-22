import time


class RateLimiter:
    def __init__(self):
        self.requests = {}

    def allow(self, key, limit, window_seconds):
        now = time.time()
        bucket = self.requests.setdefault(key, [])
        cutoff = now - window_seconds
        bucket[:] = [timestamp for timestamp in bucket if timestamp >= cutoff]

        if len(bucket) >= limit:
            retry_after = max(1, int(window_seconds - (now - bucket[0])))
            return False, retry_after

        bucket.append(now)
        return True, 0


rate_limiter = RateLimiter()
