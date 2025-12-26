"""Deep Research Agent using Gemini API.

Provides programmatic access to Google's Gemini Deep Research Agent
for autonomous multi-step research tasks.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, AsyncIterator, Any
from pathlib import Path


class ResearchStatus(Enum):
    """Status of a research task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Default output format that requests structured references
DEFAULT_OUTPUT_FORMAT = """
## Output Format Requirements

For all academic papers, GitHub repositories, and other resources mentioned:

1. **Papers**: Always include the arXiv ID (e.g., arXiv:2005.11401) or DOI (e.g., 10.1038/nature12373) when available
2. **GitHub repos**: Include full URLs (e.g., https://github.com/owner/repo)
3. **YouTube videos**: Include full URLs
4. **Books**: Include ISBN when available

At the end of the report, include a "## References" section listing all sources with their identifiers.
"""


@dataclass
class ResearchConfig:
    """Configuration for deep research tasks.
    
    Attributes:
        output_format: Instructions for formatting the output (e.g., sections, tables)
        max_wait_time: Maximum time to wait for research completion (seconds)
        poll_interval: Interval between status checks (seconds)
        enable_streaming: Whether to stream progress updates
        enable_thinking: Whether to show agent's thinking process
        file_search_stores: Optional list of file search store names for RAG
        include_identifiers: Whether to request arXiv IDs/DOIs in output
    """
    output_format: Optional[str] = None
    max_wait_time: int = 3600  # 60 minutes max
    poll_interval: int = 10
    enable_streaming: bool = True
    enable_thinking: bool = True
    file_search_stores: Optional[list[str]] = None
    include_identifiers: bool = True  # Request arXiv IDs, DOIs, etc.


@dataclass
class ResearchResult:
    """Result of a deep research task.
    
    Attributes:
        query: Original research query
        report: The generated research report (markdown)
        status: Final status of the research
        interaction_id: Gemini Interaction ID for follow-ups
        citations: List of cited sources
        thinking_steps: Agent's reasoning steps (if streaming enabled)
        duration_seconds: Time taken to complete research
        error: Error message if failed
    """
    query: str
    report: str
    status: ResearchStatus
    interaction_id: Optional[str] = None
    citations: list[dict] = field(default_factory=list)
    thinking_steps: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    error: Optional[str] = None
    
    @property
    def succeeded(self) -> bool:
        """Check if research completed successfully."""
        return self.status == ResearchStatus.COMPLETED
    
    def save(self, output_path: Path) -> None:
        """Save research result to files.
        
        Args:
            output_path: Directory to save results
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save report
        report_file = output_path / "research_report.md"
        report_file.write_text(self.report)
        
        # Save metadata
        import json
        metadata = {
            "query": self.query,
            "status": self.status.value,
            "interaction_id": self.interaction_id,
            "citations": self.citations,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }
        metadata_file = output_path / "research_metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
        
        # Save thinking steps if available
        if self.thinking_steps:
            thinking_file = output_path / "thinking_steps.md"
            thinking_content = "# Research Thinking Steps\n\n"
            for i, step in enumerate(self.thinking_steps, 1):
                thinking_content += f"## Step {i}\n{step}\n\n"
            thinking_file.write_text(thinking_content)


class DeepResearcher:
    """Deep Research Agent using Gemini API.
    
    Conducts autonomous multi-step research tasks using Google's
    Gemini Deep Research Agent via the Interactions API.
    
    Example:
        ```python
        researcher = DeepResearcher()
        result = await researcher.research(
            "What are the latest advances in quantum computing?"
        )
        print(result.report)
        ```
    """
    
    AGENT_NAME = "deep-research-pro-preview-12-2025"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[ResearchConfig] = None,
    ):
        """Initialize the Deep Researcher.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            config: Research configuration
        """
        self.api_key = api_key
        self.config = config or ResearchConfig()
        self._client = None
    
    def _get_client(self):
        """Get or create the Gemini client."""
        if self._client is None:
            try:
                from google import genai
            except ImportError:
                raise ImportError(
                    "google-genai package not installed. "
                    "Install with: pip install google-genai"
                )
            
            if self.api_key:
                self._client = genai.Client(api_key=self.api_key)
            else:
                # Uses GOOGLE_API_KEY env var or Application Default Credentials
                self._client = genai.Client()
        
        return self._client
    
    def _build_prompt(self, query: str) -> str:
        """Build the research prompt with optional formatting instructions.
        
        Args:
            query: The research query
            
        Returns:
            Complete prompt with formatting instructions
        """
        prompt = query
        
        # Add custom output format if provided
        if self.config.output_format:
            prompt += f"\n\n{self.config.output_format}"
        
        # Add identifier format requirements
        if self.config.include_identifiers:
            prompt += f"\n\n{DEFAULT_OUTPUT_FORMAT}"
        
        return prompt
    
    def _build_tools(self) -> Optional[list[dict]]:
        """Build the tools configuration.
        
        Returns:
            Tools list if file search is configured, else None
        """
        if not self.config.file_search_stores:
            return None
        
        return [
            {
                "type": "file_search",
                "file_search_store_names": self.config.file_search_stores
            }
        ]
    
    async def research(
        self,
        query: str,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> ResearchResult:
        """Conduct a deep research task.
        
        Args:
            query: The research query/topic
            on_progress: Optional callback for progress updates
            
        Returns:
            ResearchResult with the report and metadata
        """
        client = self._get_client()
        prompt = self._build_prompt(query)
        tools = self._build_tools()
        
        start_time = time.time()
        thinking_steps = []
        report_text = ""
        interaction_id = None
        citations = []
        
        try:
            if self.config.enable_streaming:
                # Streaming mode with progress updates
                result = await self._research_streaming(
                    client, prompt, tools, on_progress, thinking_steps
                )
                report_text = result["report"]
                interaction_id = result["interaction_id"]
                citations = result.get("citations", [])
            else:
                # Polling mode
                result = await self._research_polling(client, prompt, tools)
                report_text = result["report"]
                interaction_id = result["interaction_id"]
                citations = result.get("citations", [])
            
            duration = time.time() - start_time
            
            return ResearchResult(
                query=query,
                report=report_text,
                status=ResearchStatus.COMPLETED,
                interaction_id=interaction_id,
                citations=citations,
                thinking_steps=thinking_steps,
                duration_seconds=duration,
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return ResearchResult(
                query=query,
                report="",
                status=ResearchStatus.FAILED,
                interaction_id=interaction_id,
                thinking_steps=thinking_steps,
                duration_seconds=duration,
                error=str(e),
            )
    
    async def _research_streaming(
        self,
        client,
        prompt: str,
        tools: Optional[list[dict]],
        on_progress: Optional[Callable[[str], None]],
        thinking_steps: list[str],
    ) -> dict:
        """Execute research with streaming.
        
        Args:
            client: Gemini client
            prompt: Research prompt
            tools: Optional tools configuration
            on_progress: Progress callback
            thinking_steps: List to collect thinking steps
            
        Returns:
            Dict with report, interaction_id, citations
        """
        create_kwargs = {
            "input": prompt,
            "agent": self.AGENT_NAME,
            "background": True,
            "stream": True,
        }
        
        if self.config.enable_thinking:
            create_kwargs["agent_config"] = {
                "type": "deep-research",
                "thinking_summaries": "auto"
            }
        
        if tools:
            create_kwargs["tools"] = tools
        
        # Run in thread pool since google-genai may be sync
        loop = asyncio.get_event_loop()
        
        interaction_id = None
        last_event_id = None
        report_parts = []
        is_complete = False
        
        def process_stream(stream):
            nonlocal interaction_id, last_event_id, is_complete
            
            for chunk in stream:
                if chunk.event_type == "interaction.start":
                    interaction_id = chunk.interaction.id
                    if on_progress:
                        on_progress(f"Research started: {interaction_id}")
                
                if hasattr(chunk, 'event_id') and chunk.event_id:
                    last_event_id = chunk.event_id
                
                if chunk.event_type == "content.delta":
                    if hasattr(chunk.delta, 'type'):
                        if chunk.delta.type == "text":
                            text = chunk.delta.text
                            report_parts.append(text)
                            if on_progress:
                                on_progress(text)
                        elif chunk.delta.type == "thought_summary":
                            thought = chunk.delta.content.text
                            thinking_steps.append(thought)
                            if on_progress:
                                on_progress(f"[Thinking] {thought}")
                
                if chunk.event_type in ['interaction.complete', 'error']:
                    is_complete = True
        
        # Initial stream
        initial_error = None
        try:
            stream = await loop.run_in_executor(
                None,
                lambda: client.interactions.create(**create_kwargs)
            )
            await loop.run_in_executor(None, lambda: process_stream(stream))
        except Exception as e:
            initial_error = e
            if on_progress:
                on_progress(f"Connection dropped: {e}")
        
        # If initial connection failed and we have no interaction_id, raise the error
        if initial_error and not interaction_id:
            raise initial_error
        
        # Reconnection loop
        max_retries = 10
        retry_count = 0
        
        while not is_complete and interaction_id and retry_count < max_retries:
            if on_progress:
                on_progress(f"Reconnecting from event {last_event_id}...")
            
            await asyncio.sleep(2)
            retry_count += 1
            
            try:
                get_kwargs = {
                    "id": interaction_id,
                    "stream": True,
                }
                if last_event_id:
                    get_kwargs["last_event_id"] = last_event_id
                
                resume_stream = await loop.run_in_executor(
                    None,
                    lambda: client.interactions.get(**get_kwargs)
                )
                await loop.run_in_executor(None, lambda: process_stream(resume_stream))
            except Exception as e:
                if on_progress:
                    on_progress(f"Reconnection failed: {e}")
        
        return {
            "report": "".join(report_parts),
            "interaction_id": interaction_id,
            "citations": [],  # Extract from report if needed
        }
    
    async def _research_polling(
        self,
        client,
        prompt: str,
        tools: Optional[list[dict]],
    ) -> dict:
        """Execute research with polling.
        
        Args:
            client: Gemini client
            prompt: Research prompt
            tools: Optional tools configuration
            
        Returns:
            Dict with report, interaction_id, citations
        """
        loop = asyncio.get_event_loop()
        
        create_kwargs = {
            "input": prompt,
            "agent": self.AGENT_NAME,
            "background": True,
        }
        
        if tools:
            create_kwargs["tools"] = tools
        
        # Start research
        interaction = await loop.run_in_executor(
            None,
            lambda: client.interactions.create(**create_kwargs)
        )
        
        interaction_id = interaction.id
        
        # Poll for completion
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.config.max_wait_time:
                raise TimeoutError(
                    f"Research did not complete within {self.config.max_wait_time}s"
                )
            
            interaction = await loop.run_in_executor(
                None,
                lambda: client.interactions.get(interaction_id)
            )
            
            if interaction.status == "completed":
                return {
                    "report": interaction.outputs[-1].text,
                    "interaction_id": interaction_id,
                    "citations": [],
                }
            elif interaction.status == "failed":
                raise Exception(f"Research failed: {interaction.error}")
            
            await asyncio.sleep(self.config.poll_interval)
    
    async def follow_up(
        self,
        question: str,
        interaction_id: str,
    ) -> str:
        """Ask a follow-up question about a completed research.
        
        Args:
            question: Follow-up question
            interaction_id: ID of the completed research interaction
            
        Returns:
            Response text
        """
        client = self._get_client()
        loop = asyncio.get_event_loop()
        
        interaction = await loop.run_in_executor(
            None,
            lambda: client.interactions.create(
                input=question,
                model="gemini-3-pro-preview",
                previous_interaction_id=interaction_id
            )
        )
        
        return interaction.outputs[-1].text


# Convenience function
async def deep_research(
    query: str,
    output_format: Optional[str] = None,
    api_key: Optional[str] = None,
    on_progress: Optional[Callable[[str], None]] = None,
) -> ResearchResult:
    """Convenience function for quick research tasks.
    
    Args:
        query: Research query/topic
        output_format: Optional formatting instructions
        api_key: Google API key
        on_progress: Progress callback
        
    Returns:
        ResearchResult with report
        
    Example:
        ```python
        result = await deep_research(
            "What are the key trends in AI safety research?",
            output_format="Format as an executive summary with bullet points."
        )
        print(result.report)
        ```
    """
    config = ResearchConfig(output_format=output_format)
    researcher = DeepResearcher(api_key=api_key, config=config)
    return await researcher.research(query, on_progress=on_progress)
