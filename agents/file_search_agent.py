#!/usr/bin/env python3
"""
File Search Agent - Document and File Search Specialist
Provides intelligent file search, document retrieval, and content discovery.
"""
import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from utils.logger import get_logger
from utils.rag_client import rag_client
from utils.groq_client import groq_client
from utils.file_based_retriever import file_retriever
from utils.vector_search import get_vector_search_engine, search_documents
from utils.explainability import create_explanation_trace, add_reasoning_step, add_final_decision
from reinforcement.rl_context import RLContext

logger = get_logger(__name__)

class FileSearchAgent:
    """Agent specialized in searching and retrieving information from files and documents."""

    def __init__(self):
        self.name = "FileSearchAgent"
        self.description = "Intelligent file and document search and retrieval with vector-backed search"
        self.rl_context = RLContext()
        self.persona = "information_retriever"

        # Search keywords
        self.search_keywords = [
            "search", "find", "locate", "retrieve", "lookup", "discover",
            "file", "document", "folder", "directory", "path", "content"
        ]

        # Initialize vector search engine
        self.vector_engine = get_vector_search_engine()

        logger.info("✅ FileSearchAgent initialized with RAG API, file search, and vector search capabilities")

    def _get_knowledge_context(self, query: str) -> str:
        """Get relevant knowledge from RAG API for search context."""
        try:
            # Enhance query with search context
            enhanced_query = f"Information retrieval and search strategies: {query}"

            # Query RAG API
            response = rag_client.query(enhanced_query, top_k=3)

            if response.get("status") == "success" and response.get("results"):
                # Combine relevant results
                contexts = []
                for result in response["results"][:2]:  # Top 2 results
                    if isinstance(result, dict) and "content" in result:
                        contexts.append(result["content"])

                return " ".join(contexts) if contexts else ""

            logger.warning("⚠️ No search context retrieved from RAG API")
            return ""

        except Exception as e:
            logger.error(f"❌ Error getting search context: {str(e)}")
            return ""

    def _search_files(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search through files using file-based retriever."""
        try:
            # Use file-based retriever for local file search
            results = file_retriever.search(query, limit=max_results)

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("text", ""),
                    "source": result.get("source", "unknown"),
                    "score": result.get("similarity_score", 0.0),
                    "file_name": Path(result.get("source", "")).name,
                    "search_type": "semantic_similarity"
                })

            return formatted_results

        except Exception as e:
            logger.error(f"❌ File search error: {str(e)}")
            return []

    def _search_with_vector(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search using vector similarity search."""
        try:
            # Use vector search engine
            vector_results = search_documents(query, top_k=max_results, score_threshold=0.1)

            # Format results
            formatted_results = []
            for result in vector_results:
                formatted_results.append({
                    "content": result.get("text", ""),
                    "source": result.get("source", "vector_index"),
                    "score": result.get("score", 0.0),
                    "file_name": result.get("metadata", {}).get("filename", "unknown"),
                    "search_type": "vector_similarity",
                    "doc_id": result.get("doc_id", ""),
                    "rank": result.get("rank", 0)
                })

            return formatted_results

        except Exception as e:
            logger.error(f"❌ Vector search error: {str(e)}")
            return []

    def _search_with_rag(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search using RAG API for broader knowledge retrieval."""
        try:
            response = rag_client.query(query, top_k=max_results)

            if response.get("status") == "success" and response.get("results"):
                formatted_results = []
                for result in response["results"]:
                    if isinstance(result, dict) and "content" in result:
                        formatted_results.append({
                            "content": result["content"],
                            "source": result.get("source", "rag_api"),
                            "score": result.get("score", 0.0),
                            "file_name": result.get("document_id", "unknown"),
                            "search_type": "knowledge_base"
                        })

                return formatted_results

            return []

        except Exception as e:
            logger.error(f"❌ RAG search error: {str(e)}")
            return []

    def _enhance_with_groq(self, query: str, search_results: List[Dict[str, Any]],
                          knowledge_context: str = "") -> tuple[str, bool]:
        """Enhance response using Groq with search expertise."""
        try:
            # Prepare search results summary
            results_summary = ""
            if search_results:
                results_summary = "\n".join([
                    f"- {result['file_name']}: {result['content'][:100]}..."
                    for result in search_results[:3]
                ])
            else:
                results_summary = "No relevant files found."

            # Build search enhancement prompt
            prompt = f"""As an expert information retrieval specialist, provide comprehensive search results and analysis for: "{query}"

{f'Relevant Context: {knowledge_context}' if knowledge_context else 'Apply information retrieval best practices.'}

Search Results Found:
{results_summary}

Please respond as a professional search specialist who:
- Analyzes and synthesizes information from multiple sources
- Provides clear, organized results with proper attribution
- Identifies the most relevant and authoritative information
- Offers additional search strategies if needed
- Maintains accuracy and relevance in results

Your search analysis should include:
- Summary of key findings and relevant information
- Source attribution and credibility assessment
- Recommendations for further investigation if needed
- Clear organization of results by relevance and type

Search Results Analysis:"""

            response, success = groq_client.generate_response(prompt, max_tokens=1200, temperature=0.6)

            if success and response:
                return response, True
            else:
                logger.warning("⚠️ Groq enhancement failed, using fallback")
                return self._fallback_search_results(query, search_results, knowledge_context), False

        except Exception as e:
            logger.error(f"❌ Groq enhancement error: {str(e)}")
            return self._fallback_search_results(query, search_results, knowledge_context), False

    def _fallback_search_results(self, query: str, search_results: List[Dict[str, Any]],
                               knowledge_context: str = "") -> str:
        """Provide fallback search results when Groq is unavailable."""
        base_response = f"Search Results for '{query}':\n\n"

        if search_results:
            base_response += "Found the following relevant information:\n\n"
            for i, result in enumerate(search_results[:5], 1):
                base_response += f"{i}. **{result['file_name']}** (Relevance: {result['score']:.2f})\n"
                base_response += f"   {result['content'][:200]}...\n\n"
        else:
            base_response += "No relevant files or documents were found matching your search criteria.\n\n"
            base_response += "Suggestions:\n"
            base_response += "• Try using different keywords\n"
            base_response += "• Check spelling and terminology\n"
            base_response += "• Consider broader or more specific search terms\n"

        if knowledge_context:
            base_response += f"\nAdditional Context: {knowledge_context[:300]}..."

        return base_response

    def _detect_search_type(self, query: str) -> str:
        """Detect the type of search requested."""
        query_lower = query.lower()

        if any(word in query_lower for word in ["file", "document", "folder", "directory"]):
            return "file_system"
        elif any(word in query_lower for word in ["knowledge", "information", "data", "facts"]):
            return "knowledge_base"
        elif any(word in query_lower for word in ["specific", "exact", "particular"]):
            return "exact_match"
        else:
            return "general_search"

    def process_query(self, query: str, task_id: str = None) -> Dict[str, Any]:
        """Process a file search query with explainability."""
        task_id = task_id or str(uuid.uuid4())

        try:
            logger.info(f"🔍 FileSearchAgent processing query: '{query[:100]}...'")

            # Create explainability trace
            trace_id = create_explanation_trace(self.name, query, {"task_id": task_id})

            # Step 1: Detect search type
            search_type = self._detect_search_type(query)
            add_reasoning_step(
                trace_id, "classification", 
                f"Classified search type as: {search_type}",
                {"query": query}, {"search_type": search_type},
                confidence=0.8, evidence=[f"Query contains keywords indicating {search_type}"]
            )

            # Step 2: Get knowledge context from RAG API
            knowledge_context = self._get_knowledge_context(query)
            add_reasoning_step(
                trace_id, "analysis",
                "Retrieved contextual knowledge for search enhancement",
                {"query": query}, {"context_length": len(knowledge_context)},
                confidence=0.7, evidence=["RAG API provided relevant context"] if knowledge_context else []
            )

            # Step 3: Perform multi-modal search
            search_results = []

            # Vector search (primary method)
            vector_results = self._search_with_vector(query, max_results=3)
            search_results.extend(vector_results)
            add_reasoning_step(
                trace_id, "inference",
                f"Vector search returned {len(vector_results)} results",
                {"query": query}, {"vector_results": len(vector_results)},
                confidence=0.9, evidence=[f"Vector similarity search with {len(vector_results)} matches"]
            )

            # File-based search (fallback)
            if search_type in ["file_system", "general_search"]:
                file_results = self._search_files(query, max_results=2)
                search_results.extend(file_results)
                add_reasoning_step(
                    trace_id, "inference",
                    f"File-based search returned {len(file_results)} results",
                    {"search_type": search_type}, {"file_results": len(file_results)},
                    confidence=0.7, evidence=[f"File system search with {len(file_results)} matches"]
                )

            # RAG search for knowledge base
            kb_results = self._search_with_rag(query, max_results=2)
            search_results.extend(kb_results)
            add_reasoning_step(
                trace_id, "inference",
                f"Knowledge base search returned {len(kb_results)} results",
                {"query": query}, {"kb_results": len(kb_results)},
                confidence=0.8, evidence=[f"RAG API returned {len(kb_results)} knowledge matches"]
            )

            # Remove duplicates and sort by score
            seen_sources = set()
            unique_results = []
            for result in sorted(search_results, key=lambda x: x.get("score", 0), reverse=True):
                if result["source"] not in seen_sources:
                    seen_sources.add(result["source"])
                    unique_results.append(result)

            search_results = unique_results[:5]  # Limit to top 5

            # Add reasoning step for result consolidation
            add_reasoning_step(
                trace_id, "analysis",
                f"Consolidated and ranked {len(search_results)} unique results",
                {"total_results": len(unique_results)}, {"final_results": len(search_results)},
                confidence=0.8, evidence=[f"Removed duplicates and selected top {len(search_results)} results"]
            )

            # Step 4: Enhance with Groq using search expertise
            enhanced_response, groq_used = self._enhance_with_groq(query, search_results, knowledge_context)
            
            # Add final decision to explainability trace
            add_final_decision(
                trace_id, "recommendation",
                f"Provided search results with {len(search_results)} relevant documents",
                confidence=0.8 if search_results else 0.3,
                justification=f"Found {len(search_results)} relevant results using multi-modal search approach",
                alternatives=[{"method": "single_source_search", "reason": "less comprehensive"}],
                risk_factors=["No results found"] if not search_results else []
            )

            # Step 4: Log RL context
            self.rl_context.log_action(
                task_id=task_id,
                agent=self.name,
                model="groq" if groq_used else "fallback",
                action="file_search",
                metadata={
                    "query": query,
                    "search_type": search_type,
                    "results_found": len(search_results),
                    "knowledge_retrieved": bool(knowledge_context),
                    "groq_enhanced": groq_used,
                    "persona": self.persona
                }
            )

            # Step 5: Prepare response with explainability
            from utils.explainability import get_explanation, get_explanation_summary
            
            response_data = {
                "response": enhanced_response,
                "query_id": task_id,
                "query": query,
                "agent": self.name,
                "persona": self.persona,
                "search_type": search_type,
                "search_results": search_results,
                "knowledge_context_used": bool(knowledge_context),
                "groq_enhanced": groq_used,
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "explainability": {
                    "trace_id": trace_id,
                    "explanation": get_explanation(trace_id),
                    "summary": get_explanation_summary(trace_id)
                },
                "metadata": {
                    "search_keywords": [kw for kw in self.search_keywords if kw in query.lower()],
                    "processing_type": "file_search_with_vector_support",
                    "enhancement_method": "groq" if groq_used else "fallback",
                    "total_results": len(search_results),
                    "search_sources": list(set(result["source"] for result in search_results)),
                    "vector_search_enabled": True
                }
            }

            logger.info(f"✅ FileSearchAgent completed processing for task {task_id} - found {len(search_results)} results")
            return response_data

        except Exception as e:
            logger.error(f"❌ FileSearchAgent error: {str(e)}")

            # Return error response
            return {
                "response": "I apologize, but I'm experiencing difficulties searching for files at this moment. Please try again later.",
                "query_id": task_id,
                "query": query,
                "agent": self.name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def run(self, input_path: str, live_feed: str = "", model: str = "file_search_agent",
            input_type: str = "text", task_id: str = None) -> Dict[str, Any]:
        """Main entry point for agent execution - compatible with existing interface."""
        return self.process_query(input_path, task_id)

    def health_check(self) -> Dict[str, Any]:
        """Check agent health and dependencies."""
        health_status = {
            "agent": self.name,
            "status": "healthy",
            "rag_api_available": False,
            "groq_api_available": False,
            "file_retriever_available": False,
            "vector_search_available": False,
            "timestamp": datetime.now().isoformat()
        }

        # Check RAG API
        try:
            rag_health = rag_client.health_check()
            health_status["rag_api_available"] = rag_health.get("available", False)
        except Exception as e:
            logger.warning(f"RAG API health check failed: {e}")

        # Check Groq API
        try:
            groq_health = groq_client.health_check()
            health_status["groq_api_available"] = groq_health.get("available", False)
        except Exception as e:
            logger.warning(f"Groq API health check failed: {e}")

        # Check file retriever
        try:
            file_stats = file_retriever.get_stats()
            health_status["file_retriever_available"] = file_stats.get("total_chunks", 0) > 0
        except Exception as e:
            logger.warning(f"File retriever health check failed: {e}")

        # Check vector search
        try:
            vector_health = self.vector_engine.health_check()
            health_status["vector_search_available"] = vector_health.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Vector search health check failed: {e}")

        # Overall status
        services_available = sum([
            health_status["rag_api_available"],
            health_status["groq_api_available"],
            health_status["file_retriever_available"],
            health_status["vector_search_available"]
        ])

        if services_available == 0:
            health_status["status"] = "degraded"
        elif services_available < 2:
            health_status["status"] = "partial"

        return health_status