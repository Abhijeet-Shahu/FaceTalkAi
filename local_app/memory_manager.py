import json
import os

class MemoryManager:

    def __init__(self, file="memory.json"):
        self.file = file
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump({}, f)

    def save(self, key, value):
        with open(self.file, "r") as f:
            data = json.load(f)

        data[key] = value

        with open(self.file, "w") as f:
            json.dump(data, f)

    def load(self, key):
        with open(self.file, "r") as f:
            data = json.load(f)
        return data.get(key)