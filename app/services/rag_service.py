import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        pass

    @staticmethod
    def clean_search_query(query: str) -> str:
        """Strip conversational prefixes, typos, and punctuation to optimize search engines."""
        cleaned = re.sub(
            r'^(tell me (about|the)?|what (is|are)|who (is|was)|can you (tell|explain|find)|search for|find me|give me|show me)\s+',
            '',
            query,
            flags=re.IGNORECASE
        ).strip()
        # Fix common typos
        cleaned = re.sub(r'\blastest\b', 'latest', cleaned, flags=re.IGNORECASE)
        # Remove trailing question marks or punctuation
        cleaned = cleaned.rstrip('?.!').strip()
        return cleaned if len(cleaned) >= 2 else query

    def search_web(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Perform robust web search via ddgs / DuckDuckGo."""
        results = []
        cleaned_query = self.clean_search_query(query)

        # Import DDGS with fallback
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        queries_to_try = [cleaned_query]
        if cleaned_query.lower() != query.lower():
            queries_to_try.append(query)

        for q in queries_to_try:
            try:
                with DDGS() as ddgs:
                    ddg_gen = ddgs.text(q, max_results=max_results)
                    for r in ddg_gen:
                        snippet = r.get("body", "") or r.get("snippet", "")
                        title = r.get("title", "")
                        url = r.get("href", "") or r.get("url", "")
                        # Filter out blank or useless homepage links if possible
                        if snippet and len(snippet) > 15:
                            results.append({
                                "title": title or "Source",
                                "snippet": snippet,
                                "url": url
                            })
                    if results:
                        break
            except Exception as e:
                logger.debug(f"Search attempt for '{q}' failed: {e}")

        # If still empty or only useless hits, return empty or notice
        return results[:max_results]

    def build_augmented_context(
        self,
        user_message: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
        search_results: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Compose user message with file attachments and web search results."""
        sections = []

        # 1. Attached Files Context
        if attachments:
            file_sections = []
            for att in attachments:
                fname = att.get("filename", "Attached File")
                content = att.get("content", "")
                file_sections.append(f"### [Attached Document: {fname}]\n```\n{content}\n```")
            sections.append(
                "## User Provided Documents:\n" + "\n\n".join(file_sections) +
                "\n\n*Please use the above documents to answer the user query.*"
            )

        # 2. Web Search Results Context
        if search_results:
            sr_sections = []
            for idx, r in enumerate(search_results, 1):
                title = r.get("title", "")
                url = r.get("url", "")
                snippet = r.get("snippet", "")
                sr_sections.append(f"[{idx}] {title}\nURL: {url}\nSummary: {snippet}")
            sections.append(
                "## Live Web Search Results (Real-Time Current Data):\n" + "\n\n".join(sr_sections) +
                "\n\n*INSTRUCTION: Synthesize the facts, news, and details from the above search results to directly answer the user's question. Cite the sources where appropriate. Never claim you cannot access current information, as it is provided above.*"
            )

        # 3. User's Query
        sections.append(f"## User Question:\n{user_message}")

        return "\n\n---\n\n".join(sections)

rag_service = RAGService()
