from abc import ABC, abstractmethod
from typing import List, Dict, Any
from src.models.lead import BusinessProfile

class BaseScraper(ABC):
    @abstractmethod
    def search(self, category: str, location: str, limit: int = 10) -> List[BusinessProfile]:
        pass
