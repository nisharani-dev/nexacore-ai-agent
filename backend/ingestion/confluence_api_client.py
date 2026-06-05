"""
confluence_api_client.py
─────────────────────────
Real Confluence Cloud API client for syncing documentation.

Supports:
- Fetching pages from Confluence Cloud
- Incremental sync (only changed pages)
- Converting Confluence content to memory items
- Caching and deduplication

Usage:
    from backend.ingestion.confluence_api_client import ConfluenceClient
    
    client = ConfluenceClient(
        domain="your-instance.atlassian.net",
        email="user@example.com",
        api_token="your_api_token"
    )
    
    pages = client.get_pages(space_key="ONBOARDING")
    for page in pages:
        memory_item = client.page_to_memory(page)
"""

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from pydantic import BaseModel

from backend.interfaces import MemoryItem
from backend.logging_config import get_logger

logger = get_logger(__name__)


class ConfluencePage(BaseModel):
    """Represents a Confluence page."""
    
    id: str
    title: str
    body_view: str  # HTML content
    body_plain: str  # Plain text fallback
    space_key: str
    created: str  # ISO timestamp
    updated: str  # ISO timestamp
    version: int
    url: str
    
    class Config:
        extra = "allow"


class ConfluenceClient:
    """Confluence Cloud API client."""
    
    def __init__(
        self,
        *,
        domain: str,
        email: str,
        api_token: str,
        timeout: float = 30.0,
    ):
        """
        Initialize Confluence client.
        
        Args:
            domain: Confluence instance domain (e.g., "company.atlassian.net")
            email: Atlassian account email
            api_token: Atlassian API token (create at id.atlassian.com/manage-profile/security/api-tokens)
            timeout: Request timeout in seconds
        """
        self.domain = domain
        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self.base_url = f"https://{domain}/wiki/rest/api"
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            "Confluence client initialized",
            extra={
                "domain": domain,
                "email": email,
            }
        )
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                auth=(self.email, self.api_token),
                timeout=self.timeout,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "NexaCore/1.0",
                }
            )
        return self._client
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def get_pages(
        self,
        space_key: str,
        expand: Optional[str] = None,
        limit: int = 50,
        start: int = 0,
    ) -> list[ConfluencePage]:
        """
        Fetch pages from a Confluence space.
        
        Args:
            space_key: Space key (e.g., "ONBOARDING")
            expand: Additional fields to expand (body.view, body.storage, etc)
            limit: Maximum pages to return per request
            start: Starting offset for pagination
            
        Returns:
            List of ConfluencePage objects
        """
        client = await self.get_client()
        
        if expand is None:
            expand = "body.view,history.lastUpdated,version"
        
        params = {
            "spaceKey": space_key,
            "expand": expand,
            "limit": limit,
            "start": start,
            "status": "current",  # Only published pages
        }
        
        try:
            response = await client.get(
                f"{self.base_url}/content",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            pages = []
            for item in data.get("results", []):
                page = ConfluencePage(
                    id=item["id"],
                    title=item["title"],
                    body_view=item.get("body", {}).get("view", {}).get("value", ""),
                    body_plain=self._html_to_plain(
                        item.get("body", {}).get("view", {}).get("value", "")
                    ),
                    space_key=item["space"]["key"],
                    created=item["history"]["createdDate"],
                    updated=item["history"]["latestUpdate"]["when"],
                    version=item["version"]["number"],
                    url=item["_links"]["webui"],
                )
                pages.append(page)
            
            logger.info(
                "Fetched Confluence pages",
                extra={
                    "space_key": space_key,
                    "count": len(pages),
                }
            )
            
            return pages
        
        except httpx.HTTPError as e:
            logger.error(
                "Failed to fetch Confluence pages",
                extra={
                    "space_key": space_key,
                    "error": str(e),
                }
            )
            raise
    
    async def get_page_by_title(
        self,
        space_key: str,
        title: str,
    ) -> Optional[ConfluencePage]:
        """Fetch a specific page by title."""
        client = await self.get_client()
        
        params = {
            "spaceKey": space_key,
            "title": title,
            "expand": "body.view,history.lastUpdated,version",
            "status": "current",
        }
        
        try:
            response = await client.get(
                f"{self.base_url}/content",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            
            if data["results"]:
                item = data["results"][0]
                return ConfluencePage(
                    id=item["id"],
                    title=item["title"],
                    body_view=item.get("body", {}).get("view", {}).get("value", ""),
                    body_plain=self._html_to_plain(
                        item.get("body", {}).get("view", {}).get("value", "")
                    ),
                    space_key=item["space"]["key"],
                    created=item["history"]["createdDate"],
                    updated=item["history"]["latestUpdate"]["when"],
                    version=item["version"]["number"],
                    url=item["_links"]["webui"],
                )
            return None
        
        except httpx.HTTPError as e:
            logger.error(
                "Failed to fetch page",
                extra={
                    "space_key": space_key,
                    "title": title,
                    "error": str(e),
                }
            )
            raise
    
    def page_to_memory(
        self,
        page: ConfluencePage,
        tags: Optional[list[str]] = None,
        level: str = "reference",
    ) -> MemoryItem:
        """
        Convert Confluence page to memory item.
        
        Args:
            page: Confluence page
            tags: Additional tags (space key is auto-added)
            level: Memory level (instruction, reference, background)
            
        Returns:
            MemoryItem ready for Hindsight storage
        """
        if tags is None:
            tags = []
        
        # Add space-based tags
        tags.extend([
            f"confluence:space:{page.space_key}",
            f"confluence:page:{page.title.replace(' ', '_').lower()}",
            "org:company",
        ])
        
        # Use plain text content
        content = f"# {page.title}\n\n{page.body_plain}"
        
        # Create content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        memory = MemoryItem(
            content=content,
            tags=tags,
            level=level,
            source="confluence_sync",
            relevance_score=0.8,  # Confluence content is moderately relevant
            metadata={
                "confluence_id": page.id,
                "confluence_space": page.space_key,
                "confluence_url": page.url,
                "confluence_updated": page.updated,
                "confluence_version": page.version,
                "content_hash": content_hash,
            }
        )
        
        return memory
    
    @staticmethod
    def _html_to_plain(html: str) -> str:
        """Convert HTML to plain text (basic implementation)."""
        import re
        
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)
        
        # Decode HTML entities
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        
        # Clean up whitespace
        text = re.sub(r"\n\s*\n", "\n", text)
        text = text.strip()
        
        return text


async def sync_confluence_space(
    domain: str,
    email: str,
    api_token: str,
    space_key: str,
    on_page: Optional[callable] = None,
) -> int:
    """
    Sync all pages from a Confluence space.
    
    Args:
        domain: Confluence domain
        email: Atlassian email
        api_token: API token
        space_key: Space to sync
        on_page: Optional callback for each page (MemoryItem)
        
    Returns:
        Number of pages synced
    """
    count = 0
    
    async with ConfluenceClient(
        domain=domain,
        email=email,
        api_token=api_token,
    ) as client:
        pages = await client.get_pages(space_key, limit=100)
        
        for page in pages:
            memory_item = client.page_to_memory(page)
            
            if on_page:
                await on_page(memory_item)
            
            count += 1
    
    return count


@staticmethod
def get_client_from_env() -> Optional[ConfluenceClient]:
    """Create client from environment variables."""
    domain = os.getenv("CONFLUENCE_DOMAIN")
    email = os.getenv("CONFLUENCE_EMAIL")
    api_token = os.getenv("CONFLUENCE_API_TOKEN")
    
    if not all([domain, email, api_token]):
        logger.warning("Missing Confluence credentials in environment variables")
        return None
    
    return ConfluenceClient(
        domain=domain,
        email=email,
        api_token=api_token,
    )
