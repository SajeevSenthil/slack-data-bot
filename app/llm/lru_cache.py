from threading import Lock


class _Node:
    def __init__(self, key=None, value=None):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None


class LRUCache:
    def __init__(self, capacity):
        if capacity <= 0:
            raise ValueError("capacity must be greater than 0")

        self.capacity = capacity
        self.map = {}
        self.lock = Lock()

        # Sentinel nodes simplify insert/remove logic.
        self.head = _Node()
        self.tail = _Node()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _add_to_front(self, node):
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def _remove_node(self, node):
        prev_node = node.prev
        next_node = node.next
        prev_node.next = next_node
        next_node.prev = prev_node
        node.prev = None
        node.next = None

    def _move_to_front(self, node):
        self._remove_node(node)
        self._add_to_front(node)

    def _pop_lru(self):
        lru = self.tail.prev
        if lru is self.head:
            return None
        self._remove_node(lru)
        return lru

    def get(self, key):
        with self.lock:
            node = self.map.get(key)
            if not node:
                return None
            self._move_to_front(node)
            return node.value

    def put(self, key, value):
        with self.lock:
            existing = self.map.get(key)
            if existing:
                existing.value = value
                self._move_to_front(existing)
                return

            node = _Node(key, value)
            self.map[key] = node
            self._add_to_front(node)

            if len(self.map) > self.capacity:
                lru = self._pop_lru()
                if lru:
                    self.map.pop(lru.key, None)
