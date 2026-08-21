import httpx
from bs4 import BeautifulSoup


async def fetch_page(url: str) -> dict:
    headers = {
        "User-Agent": "IndustrialProductIntelligence/0.1",
    }

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=20,
        headers=headers,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""
    text = " ".join(soup.get_text(" ", strip=True).split())

    return {
        "url": str(response.url),
        "title": title,
        "text": text,
    }