"""Short leases for open marking interfaces; server probes never create a lease."""
import threading
import time


class MarkingClients:
    def __init__(self, ttl_s=7.0, clock=time.monotonic):
        self._ttl = ttl_s
        self._clock = clock
        self._seen = {}
        self._lock = threading.Lock()

    def touch(self, client_id):
        with self._lock:
            self._expire()
            self._seen[client_id] = self._clock()

    def remove(self, client_id):
        with self._lock:
            self._seen.pop(client_id, None)

    def _expire(self):
        cutoff = self._clock() - self._ttl
        self._seen = {key: seen for key, seen in self._seen.items() if seen > cutoff}

    def status(self):
        with self._lock:
            self._expire()
            return {"connected": bool(self._seen), "count": len(self._seen)}
