import requests
from core.config import settings

url = "https://api.tokenmetrics.com/v2/ai-reports?token_id=3306&page=0"

headers = {
    "accept": "application/json",
    "api_key": settings.TOKEN_METRICS_API_KEY
}
## Token ID for Ethereum is 3306
def get_token_metrics(token_id: str):
    print(settings.TOKEN_METRICS_API_KEY)
    url = f"https://api.tokenmetrics.com/v2/ai-reports?token_id={token_id}&page=0"
    response = requests.get(url, headers=headers)
    return response.json()
