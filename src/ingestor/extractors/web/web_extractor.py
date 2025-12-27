"""Web content extractor using Crawl4AI."""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ...types import ExtractedImage, ExtractionResult, MediaType
from ..base import BaseExtractor


class WebExtractor(BaseExtractor):
    """Extract content from web pages using Crawl4AI.

    Supports:
    - Single page extraction
    - Deep crawling with BFS/DFS/BestFirst strategies
    - Domain restriction
    - URL pattern filtering
    """

    media_type = MediaType.WEB

    def __init__(
        self,
        strategy: str = "bfs",
        max_depth: int = 2,
        max_pages: int = 50,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        same_domain: bool = True,
    ):
        """Initialize web extractor.

        Args:
            strategy: Crawl strategy (bfs, dfs, bestfirst)
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            include_patterns: URL patterns to include
            exclude_patterns: URL patterns to exclude
            same_domain: Restrict to same domain
        """
        self.strategy = strategy
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.same_domain = same_domain

    async def extract(self, source: str | Path) -> ExtractionResult:
        """Extract content from a URL.

        Args:
            source: URL to extract from

        Returns:
            Extraction result with markdown content
        """
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        url = str(source)

        # Handle .url files
        if str(source).endswith(".url"):
            url = self._read_url_file(Path(source))

        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
        )

        run_config = CrawlerRunConfig(
            wait_until="networkidle",
            word_count_threshold=10,
            remove_overlay_elements=True,
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=run_config)

            if not result.success:
                return ExtractionResult(
                    markdown=f"# Error\n\nFailed to crawl: {url}\n\n{result.error_message}",
                    title="Error",
                    source=url,
                    media_type=MediaType.WEB,
                    images=[],
                    metadata={"error": result.error_message},
                )

            # Get markdown content
            markdown = result.markdown or ""

            # Extract title
            title = result.metadata.get("title", urlparse(url).netloc) if result.metadata else urlparse(url).netloc

            # Extract images and get URL mapping
            images, image_url_map = self._extract_images(result)

            # Rewrite image paths in markdown to point to extracted images
            if image_url_map:
                markdown = self._rewrite_image_paths(markdown, image_url_map)

            return ExtractionResult(
                markdown=markdown,
                title=title,
                source=url,
                media_type=MediaType.WEB,
                images=images,
                metadata={
                    "url": url,
                    "links_count": len(result.links.get("internal", [])) + len(result.links.get("external", [])) if result.links else 0,
                },
            )

    async def crawl_deep(self, source: str | Path) -> list[ExtractionResult]:
        """Perform deep crawling of a website.

        Args:
            source: Starting URL

        Returns:
            List of extraction results for each page
        """
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy

        url = str(source)
        if str(source).endswith(".url"):
            url = self._read_url_file(Path(source))

        # Select strategy
        if self.strategy == "dfs":
            strategy = DFSDeepCrawlStrategy(
                max_depth=self.max_depth,
                max_pages=self.max_pages,
                include_external=not self.same_domain,
            )
        else:  # Default to BFS
            strategy = BFSDeepCrawlStrategy(
                max_depth=self.max_depth,
                max_pages=self.max_pages,
                include_external=not self.same_domain,
            )

        # Apply URL filters
        if self.include_patterns:
            strategy.url_filter = lambda u: any(p in u for p in self.include_patterns)
        if self.exclude_patterns:
            original_filter = strategy.url_filter or (lambda u: True)
            strategy.url_filter = lambda u: original_filter(u) and not any(p in u for p in self.exclude_patterns)

        browser_config = BrowserConfig(headless=True, verbose=False)
        run_config = CrawlerRunConfig(
            deep_crawl_strategy=strategy,
            wait_until="networkidle",
        )

        results = []
        async with AsyncWebCrawler(config=browser_config) as crawler:
            crawl_results = await crawler.arun(url=url, config=run_config)
            # Handle both list and single result
            if not isinstance(crawl_results, list):
                crawl_results = [crawl_results]

            for result in crawl_results:
                if result.success:
                    markdown = result.markdown or ""
                    title = result.metadata.get("title", "") if result.metadata else ""
                    images, image_url_map = self._extract_images(result)

                    # Rewrite image paths
                    if image_url_map:
                        markdown = self._rewrite_image_paths(markdown, image_url_map)

                    results.append(ExtractionResult(
                        markdown=markdown,
                        title=title,
                        source=result.url,
                        media_type=MediaType.WEB,
                        images=images,
                        metadata={"url": result.url},
                    ))

        return results

    def _read_url_file(self, path: Path) -> str:
        """Read URL from a .url file.

        Args:
            path: Path to .url file

        Returns:
            URL string
        """
        content = path.read_text(encoding="utf-8")

        # Windows .url format
        for line in content.splitlines():
            if line.startswith("URL="):
                return line[4:].strip()

        # Plain URL
        return content.strip()

    def _extract_images(self, result: Any) -> tuple[list[ExtractedImage], dict[str, str]]:
        """Extract images from crawl result.

        Args:
            result: Crawl4AI result

        Returns:
            Tuple of (list of extracted images, URL to filename mapping)
        """
        images: list[ExtractedImage] = []
        image_url_map: dict[str, str] = {}  # Map original URLs to new filenames

        if hasattr(result, "media") and result.media:
            img_data = result.media.get("images", [])
            for i, img in enumerate(img_data):
                if isinstance(img, dict) and img.get("data"):
                    # Image data is base64 encoded
                    import base64
                    try:
                        data = base64.b64decode(img["data"])
                        ext = img.get("type", "png").lower()
                        if ext == "jpg":
                            ext = "jpeg"

                        filename = f"web_image_{i+1}.{ext}"

                        images.append(ExtractedImage(
                            filename=filename,
                            data=data,
                            format=ext,
                            context=img.get("alt", ""),
                        ))

                        # Map original URL to new filename
                        if img.get("src"):
                            image_url_map[img["src"]] = filename
                    except Exception:
                        pass

        return images, image_url_map

    def _rewrite_image_paths(self, markdown: str, image_url_map: dict[str, str]) -> str:
        """Rewrite image URLs in markdown to point to extracted images.

        Args:
            markdown: Original markdown from Crawl4AI
            image_url_map: Mapping of original URLs to new filenames

        Returns:
            Markdown with rewritten image paths
        """
        import re

        # Pattern to match markdown images: ![alt](url)
        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

        def replace_url(match):
            alt_text = match.group(1)
            original_url = match.group(2)

            # Check if we have this image extracted
            if original_url in image_url_map:
                return f"![{alt_text}](./img/{image_url_map[original_url]})"

            # Try matching just the filename part
            url_filename = original_url.split("/")[-1].split("?")[0]
            for url, filename in image_url_map.items():
                if url.endswith(url_filename):
                    return f"![{alt_text}](./img/{filename})"

            # Keep original if we don't have it extracted
            return match.group(0)

        return img_pattern.sub(replace_url, markdown)

    def supports(self, source: str | Path) -> bool:
        """Check if this extractor handles the source.

        Args:
            source: Source to check

        Returns:
            True if this is a web URL or .url file
        """
        source_str = str(source)

        # Check for .url files
        if source_str.lower().endswith(".url"):
            return True

        # Check for web URLs
        if source_str.startswith(("http://", "https://")):
            # Exclude YouTube URLs
            parsed = urlparse(source_str)
            youtube_domains = ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"]
            return parsed.netloc not in youtube_domains

        return False
