# blockchain_logger.py
import json
import hashlib
import os
from datetime import datetime

BLOCKCHAIN_FILE = "blockchain_logs.json"


class Blockchain:
    def __init__(self):
        self.chain = []
        if os.path.exists(BLOCKCHAIN_FILE):
            self.load_chain()
        else:
            self.create_genesis_block()
            self.save_chain()

    def create_genesis_block(self):
        genesis_block = {
            "index": 0,
            "timestamp": str(datetime.now()),
            "data": "Genesis Block",
            "previous_hash": "0",
            "hash": self.calculate_hash(0, "0", "Genesis Block")
        }
        self.chain.append(genesis_block)

    def calculate_hash(self, index, previous_hash, data):
        block_string = f"{index}{previous_hash}{data}".encode()
        return hashlib.sha256(block_string).hexdigest()

    def add_block(self, data):
        # Reload from disk first to avoid overwriting blocks from other processes (e.g. monitor vs api)
        if os.path.exists(BLOCKCHAIN_FILE):
            self.load_chain()

        last_block = self.chain[-1]
        index = last_block["index"] + 1
        previous_hash = last_block["hash"]
        block_hash = self.calculate_hash(index, previous_hash, data)

        block = {
            "index": index,
            "timestamp": str(datetime.now()),
            "data": data,
            "previous_hash": previous_hash,
            "hash": block_hash
        }

        self.chain.append(block)
        self.save_chain()

    def save_chain(self):
        import time
        for _ in range(5):
            try:
                with open(BLOCKCHAIN_FILE, "w") as f:
                    json.dump(self.chain, f, indent=4)
                return
            except:
                time.sleep(0.1)

    def load_chain(self):
        import time
        for _ in range(5):
            try:
                with open(BLOCKCHAIN_FILE, "r") as f:
                    self.chain = json.load(f)
                return
            except:
                time.sleep(0.1)


# 🔥 THIS PART WAS MISSING
if __name__ == "__main__":
    bc = Blockchain()
    print("[INFO] Blockchain Logger Initialized")
    print("[INFO] Genesis Block Created")
