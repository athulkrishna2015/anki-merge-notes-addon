from datetime import datetime

class Logger:
    _instance = None
    _logs = []
    _listeners = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] {message}"
        self._logs.append(entry)
        if len(self._logs) > 1000:
            self._logs.pop(0)
            
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception:
                pass

    def get_logs(self):
        return "\n".join(self._logs)

    def clear(self):
        self._logs = []
        for listener in self._listeners:
            try:
                listener(None)
            except Exception:
                pass

    def add_listener(self, listener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

logger = Logger()
