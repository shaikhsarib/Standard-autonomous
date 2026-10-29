import sys
import os
import uvicorn
import logging

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

if __name__ == "__main__":
    print("\n" + "="*60)
    print(" [Standard Autonomous] Command Center & Backend API")
    print(f" Dashboard: http://127.0.0.1:8000")
    print(f" Swagger Docs: http://127.0.0.1:8000/docs")
    print("="*60 + "\n")
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=True)
