import aiohttp
import asyncio
from typing import Optional, Dict, Any
from config import settings

class GmailFarmerAPI:
    """Клієнт для роботи з Gmail Farmer Trade API"""
    
    def __init__(self):
        # Налаштовуємо базовий URL та хедери
        self.base_url = f"{settings.API_DOMAIN}/api/v1/accounts"
        self.api_key = settings.API_KEY
        self.headers = {"key": self.api_key}
        # Додаємо таймаут (наприклад, 30 секунд), щоб запити не тривали вічно
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Базовий метод для HTTP запитів з обробкою помилок"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(method, url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 402:
                        raise Exception("Недостатньо коштів на балансі API")
                    elif response.status == 403:
                        raise Exception("Невірний API ключ. Перевірте налаштування")
                    elif response.status == 404:
                        raise Exception("Ресурс API не знайдено")
                    else:
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get('message', 'Unknown error')
                        except:
                            error_msg = await response.text()
                        raise Exception(f"API Error ({response.status}): {error_msg}")
        except aiohttp.ClientConnectorError:
            raise Exception(f"Помилка з'єднання з API: {settings.API_DOMAIN} недоступний")
        except asyncio.TimeoutError:
            raise Exception("Перевищено час очікування відповіді від API")
    
    async def get_price(self, is_2fa: bool = False) -> float:
        """Отримати поточну ціну акаунта"""
        params = {"is2fa": str(is_2fa).lower()}
        data = await self._request("GET", "/price", params)
        return float(data["usdPrice"])
    
    async def get_balance(self) -> float:
        """Отримати баланс"""
        data = await self._request("GET", "/balance")
        return float(data["balance"])
    
    async def get_max_per_purchase(self, is_2fa: bool = False) -> int:
        """Отримати максимальну кількість акаунтів для одного замовлення"""
        params = {"is2fa": str(is_2fa).lower()}
        data = await self._request("GET", "/max-per-purchase", params)
        return int(data["maxPerPurchase"])
    
    async def buy_accounts(self, count: int, is_2fa: bool = False) -> Dict[str, Any]:
        """Купити акаунти"""
        params = {
            "count": count,
            "is2fa": str(is_2fa).lower()
        }
        return await self._request("GET", "/buy", params)
    
    async def get_packs(self, page: int = 1, limit: int = 100) -> Dict[str, Any]:
        """Отримати список куплених пакетів"""
        params = {"page": page, "limit": limit}
        return await self._request("GET", "/packs", params)
    
    async def get_pack(self, pack_id: str) -> Dict[str, Any]:
        """Отримати деталі конкретного пакету"""
        return await self._request("GET", f"/pack/{pack_id}")

# Глобальний екземпляр API клієнта
api_client = GmailFarmerAPI()