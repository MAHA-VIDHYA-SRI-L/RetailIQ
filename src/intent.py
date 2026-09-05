"""Natural-language intent classification and entity resolution for RetailIQ.

Translates operator questions into structured application intents using Google Gemini
with deterministic fallback, database entity verification, ambiguity detection,
and relative date grounding.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.database import get_connection, get_products, get_stores
from src.gemini_client import GeminiClient
from src.models import StructuredIntent

logger = logging.getLogger(__name__)

SUPPORTED_INTENTS = [
    "SALES_SUMMARY",
    "PRODUCT_PERFORMANCE",
    "STORE_PERFORMANCE",
    "PRODUCT_COMPARISON",
    "STORE_COMPARISON",
    "CATEGORY_PERFORMANCE",
    "SALES_TREND",
    "INVENTORY_RISK",
    "OVERSTOCK",
    "REORDER_RECOMMENDATION",
    "INVENTORY_HEALTH",
    "ATTENTION_ITEMS",
    "UNKNOWN",
]


class IntentClassifier:
    """Classifies retail queries into structured intents with verified entity grounding."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None) -> None:
        self.gemini = gemini_client or GeminiClient()

    # --------------------------------------------------------------------------
    # 1. Database Entity Matching & Ambiguity Resolution
    # --------------------------------------------------------------------------

    STOPWORDS = {
        "what", "were", "your", "our", "their", "this", "that", "these", "those",
        "have", "from", "with", "about", "doing", "does", "selling", "sales", "sold",
        "show", "tell", "best", "most", "item", "items", "good", "well", "much",
        "many", "rate", "data", "view", "find", "give", "please", "help", "product",
        "products", "store", "stores", "month", "year", "week", "today", "can",
        "you", "the", "and", "for", "total", "summary", "how", "did", "performed",
        "perform", "running", "likely", "soon", "overstocked", "attention", "today",
        "compare", "between", "which", "will", "any", "all", "are", "low", "out",
        "tell", "write", "poem", "retailers", "retail", "query", "is"
    }

    def match_product(self, raw_product: Optional[str]) -> Tuple[Optional[str], Optional[str], bool, List[str]]:
        """Verify product name against database and detect ambiguities.

        Returns (product_id, product_name, is_ambiguous, candidate_matches).
        """
        if not raw_product or not raw_product.strip():
            return None, None, False, []

        query_clean = raw_product.strip().lower()
        all_products = get_products()

        # 1. Exact ID or exact Name match
        for p in all_products:
            if p["product_id"].lower() == query_clean or p["product_name"].lower() == query_clean:
                return p["product_id"], p["product_name"], False, [p["product_name"]]
            if p["product_name"].lower() in query_clean:
                return p["product_id"], p["product_name"], False, [p["product_name"]]

        # 2. Token scoring for queries and partial phrases (whole words, non-stopwords)
        tokens = [
            w for w in re.findall(r"\b[a-z0-9]{3,}\b", query_clean)
            if w not in self.STOPWORDS
        ]
        if not tokens:
            return None, None, False, []

        scored = []
        for p in all_products:
            p_name_lower = p["product_name"].lower()
            p_words = set(re.findall(r"\b[a-z0-9]{2,}\b", p_name_lower))
            score = sum(1 for t in tokens if t in p_words or t in p_name_lower)
            if score > 0:
                scored.append((score, p))

        if not scored:
            return None, None, False, []

        scored.sort(key=lambda x: x[0], reverse=True)
        top_score = scored[0][0]
        top_candidates = [p for s, p in scored if s == top_score]

        if len(top_candidates) == 1:
            return top_candidates[0]["product_id"], top_candidates[0]["product_name"], False, [top_candidates[0]["product_name"]]
        else:
            return None, None, True, [p["product_name"] for p in top_candidates[:5]]

    def match_store(self, raw_store: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Verify store name or city against database. Returns (store_id, store_name)."""
        if not raw_store or not raw_store.strip():
            return None, None

        query_clean = raw_store.strip().lower()
        stores = get_stores()

        for s in stores:
            s_id = s["store_id"].lower()
            s_city = s["city"].lower()
            s_name = s["store_name"].lower()

            if s_id == query_clean:
                return s["store_id"], s["store_name"]
            if s_city in query_clean or query_clean in s_city:
                return s["store_id"], s["store_name"]
            if any(word in query_clean for word in s_name.split() if len(word) > 3):
                return s["store_id"], s["store_name"]

        return None, None

    def match_category(self, raw_category: Optional[str]) -> Optional[str]:
        """Verify category name against catalog."""
        if not raw_category or not raw_category.strip():
            return None

        query_clean = raw_category.strip().lower()
        all_categories = {"electronics", "accessories", "home", "personal care", "office", "grocery"}
        for cat in all_categories:
            if cat in query_clean or query_clean in cat:
                return cat.title()
        return None

    # --------------------------------------------------------------------------
    # 2. Relative Date Grounding Against Dataset Bounds
    # --------------------------------------------------------------------------

    def resolve_dates(
        self,
        raw_start: Optional[str],
        raw_end: Optional[str],
        raw_query: str,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Resolve relative expressions against the actual available dataset bounds.

        Returns (start_date, end_date, date_resolution_note).
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MIN(date) as min_date, MAX(date) as max_date FROM sales;")
            bounds = cursor.fetchone()
            min_date_str = bounds["min_date"] if bounds else "2026-05-08"
            max_date_str = bounds["max_date"] if bounds else "2026-09-04"
        finally:
            conn.close()

        dt_max = datetime.strptime(max_date_str, "%Y-%m-%d").date()
        dt_min = datetime.strptime(min_date_str, "%Y-%m-%d").date()

        q_lower = raw_query.lower()
        start_date = raw_start
        end_date = raw_end
        note = None

        # Extract explicit ISO YYYY-MM-DD dates if not already extracted
        if not start_date and not end_date:
            explicit_dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", raw_query)
            if len(explicit_dates) >= 2:
                start_date, end_date = explicit_dates[0], explicit_dates[1]
                note = f"Extracted date range: {start_date} to {end_date}."
            elif len(explicit_dates) == 1:
                start_date, end_date = explicit_dates[0], explicit_dates[0]
                note = f"Extracted date: {start_date}."

        # Detect relative date expressions in user query if still unresolved
        if not start_date or not end_date:
            if "this month" in q_lower or "current month" in q_lower or "september" in q_lower:
                start_date = "2026-09-01"
                end_date = max_date_str
                note = f"Mapped to available September data ({start_date} to {end_date}; month is partial)."
            elif "last month" in q_lower or "previous month" in q_lower or "august" in q_lower:
                start_date = "2026-08-01"
                end_date = "2026-08-31"
                note = "Mapped to complete previous month of August (2026-08-01 to 2026-08-31)."
            elif "today" in q_lower:
                start_date = max_date_str
                end_date = max_date_str
                note = f"Mapped to latest transaction date in dataset ({max_date_str})."
            elif any(w in q_lower for w in ["last 7 days", "past 7 days", "past week", "this week", "last week"]):
                start_date = (dt_max - timedelta(days=6)).isoformat()
                end_date = max_date_str
                note = f"Mapped to 7-day window ({start_date} to {end_date})."
            elif any(w in q_lower for w in ["last 14 days", "past 14 days", "past 2 weeks"]):
                start_date = (dt_max - timedelta(days=13)).isoformat()
                end_date = max_date_str
                note = f"Mapped to 14-day window ({start_date} to {end_date})."
            elif any(w in q_lower for w in ["past 30 days", "last 30 days", "recent"]):
                start_date = (dt_max - timedelta(days=29)).isoformat()
                end_date = max_date_str
                note = f"Mapped to 30-day demand window ({start_date} to {end_date})."

        return start_date, end_date, note

    # --------------------------------------------------------------------------
    # 3. Rule-Based Fallback Intent Classifier
    # --------------------------------------------------------------------------

    def classify_deterministic(self, question: str) -> Dict[str, Any]:
        """Deterministic keyword-based intent classification for resilient offline operation."""
        q = question.lower()

        # 1. Attention & urgent issues
        if any(w in q for w in ["attention", "alert", "priority", "critical", "what should i pay attention"]):
            return {"intent": "ATTENTION_ITEMS", "confidence": 0.90}

        # 2. Overstock
        if any(w in q for w in ["overstock", "excess inventory", "too much stock", "holding too much"]):
            return {"intent": "OVERSTOCK", "confidence": 0.95}

        # 3. Stock-Out Risk & Running Out
        if any(w in q for w in ["run out", "running out", "runs out", "stock out", "stock-out", "low stock", "low on stock", "low in stock", "running low", "shortage", "depleted", "coverage"]):
            return {"intent": "INVENTORY_RISK", "confidence": 0.95}

        # 4. Reorder recommendations
        if any(w in q for w in ["reorder", "replenish", "order more", "how much to order"]):
            return {"intent": "REORDER_RECOMMENDATION", "confidence": 0.92}

        # 5. Inventory health
        if any(w in q for w in ["inventory health", "warehouse health", "stock status", "inventory status"]):
            return {"intent": "INVENTORY_HEALTH", "confidence": 0.90}

        # 6. Store comparison or which store sells best / most revenue
        if any(w in q for w in ["which store", "compare stores", "store comparison", "top store", "best store", "store generated the most", "store sells best", "which store sells", "stores perform"]):
            return {"intent": "STORE_COMPARISON", "confidence": 0.95}

        # 7. Trend
        if any(w in q for w in ["trend", "daily sales", "over time", "sales chart", "spike", "drop"]):
            return {"intent": "SALES_TREND", "confidence": 0.90}

        # 8. Category performance
        all_cats = ["electronics", "accessories", "personal care", "grocery", "office", "category", "categories"]
        if any(w in q for w in all_cats) and any(w in q for w in ["performing", "performance", "sales", "revenue", "how are", "doing", "share"]):
            return {"intent": "CATEGORY_PERFORMANCE", "confidence": 0.92}

        # 9. Product comparison / Top products
        if any(w in q for w in ["top products", "best selling", "most revenue", "compare products", "highest sales"]):
            return {"intent": "PRODUCT_COMPARISON", "confidence": 0.92}

        # 10. Store performance
        if any(w in q for w in ["store", "bengaluru", "mumbai", "delhi", "hyderabad", "indiranagar", "bandra", "connaught", "hitec"]):
            return {"intent": "STORE_PERFORMANCE", "confidence": 0.85}

        # 11. Product performance
        if any(w in q for w in ["mouse", "keyboard", "earbuds", "headphones", "cable", "lamp", "flask", "tea", "coffee", "wireless", "perform", "doing"]):
            return {"intent": "PRODUCT_PERFORMANCE", "confidence": 0.88}

        # 12. Overall sales summary
        if any(w in q for w in ["revenue", "sales", "orders", "growth", "summary", "how did we do"]):
            return {"intent": "SALES_SUMMARY", "confidence": 0.85}

        return {"intent": "UNKNOWN", "confidence": 0.40}

    # --------------------------------------------------------------------------
    # 4. Primary Classification Pipeline (Gemini + Local Validation)
    # --------------------------------------------------------------------------

    def classify(self, question: str) -> StructuredIntent:
        """Translate question into a verified, grounded StructuredIntent."""
        raw_intent = "UNKNOWN"
        raw_product = None
        raw_store = None
        raw_category = None
        raw_start = None
        raw_end = None
        raw_comp = None
        raw_limit = None
        confidence = 0.50

        # Attempt Gemini structured intent understanding if configured
        if self.gemini.is_configured:
            system_instruction = (
                "You are RetailIQ's Intent Classifier. "
                "Analyze retail business questions and extract structured intent.\n"
                f"Supported intents: {SUPPORTED_INTENTS}\n"
                "Return ONLY a JSON object with keys:\n"
                "intent: string (one of supported intents),\n"
                "product: string or null (product name),\n"
                "store: string or null (store name or city),\n"
                "category: string or null (category name),\n"
                "start_date: string (YYYY-MM-DD) or null,\n"
                "end_date: string (YYYY-MM-DD) or null,\n"
                "comparison: string or null,\n"
                "limit: integer or null,\n"
                "confidence: float (0.0 to 1.0)"
            )

            prompt = f"User Question: '{question}'\nExtract the structured retail intent and entities."

            try:
                result = self.gemini.generate_structured_json(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=0.0,
                )
                if result and not result.get("error"):
                    raw_intent = result.get("intent", "UNKNOWN").upper()
                    raw_product = result.get("product")
                    raw_store = result.get("store")
                    raw_category = result.get("category")
                    raw_start = result.get("start_date")
                    raw_end = result.get("end_date")
                    raw_comp = result.get("comparison")
                    raw_limit = result.get("limit")
                    confidence = float(result.get("confidence", 0.90))
            except Exception as exc:
                logger.warning("Gemini intent extraction failed, falling back to deterministic: %s", exc)

        # If Gemini is unconfigured or failed to classify cleanly, use deterministic heuristic
        if raw_intent not in SUPPORTED_INTENTS or raw_intent == "UNKNOWN":
            fallback = self.classify_deterministic(question)
            raw_intent = fallback["intent"]
            confidence = fallback["confidence"]

        # Determine relevant text targets for entity resolution
        target_product_text = raw_product
        if not target_product_text and raw_intent in ("PRODUCT_PERFORMANCE", "REORDER_RECOMMENDATION", "STORE_COMPARISON"):
            target_product_text = question

        target_store_text = raw_store
        if not target_store_text and raw_intent == "STORE_PERFORMANCE":
            target_store_text = question

        target_cat_text = raw_category
        if not target_cat_text and raw_intent == "CATEGORY_PERFORMANCE":
            target_cat_text = question

        # Validate and match entities against SQLite database
        product_id, matched_product, is_ambiguous, candidates = self.match_product(target_product_text)
        store_id, matched_store = self.match_store(target_store_text)
        matched_cat = self.match_category(target_cat_text)
        start_date, end_date, date_note = self.resolve_dates(raw_start, raw_end, question)

        # Ambiguity detection
        needs_clarification = False
        clarification_msg = None

        if is_ambiguous and candidates:
            needs_clarification = True
            cand_str = ", ".join([f"'{c}'" for c in candidates])
            clarification_msg = (
                f"We found multiple products matching your query ({cand_str}). "
                "Which specific product would you like to analyze?"
            )
            confidence = 0.60

        # Refine intent ONLY if intent was UNKNOWN and a specific entity was positively matched
        if product_id and raw_intent == "UNKNOWN":
            raw_intent = "PRODUCT_PERFORMANCE"
        elif store_id and raw_intent == "UNKNOWN":
            raw_intent = "STORE_PERFORMANCE"

        # Extract candidate product/store names when not provided by Gemini
        candidate_prod = raw_product or matched_product
        if not candidate_prod and raw_intent in ("PRODUCT_PERFORMANCE", "REORDER_RECOMMENDATION"):
            cleaned = re.sub(
                r"(?i)\b(how\s+(is|did|are)|performing|performance|perform|doing|selling|sales|this\s+month|today|what\s+about|tell\s+me\s+about|why\s+should\s+i\s+reorder|reorder|how\s+much|what\s+should\s+i|what\s+to|what)\b",
                "",
                question,
            ).strip(" ?.,!")
            if cleaned.lower() in ("what", "what should i", "what to", "how", "why", "which", "anything", "items", "products", "something", "all", "the", "i"):
                cleaned = ""
            if cleaned and len(cleaned) > 1:
                candidate_prod = cleaned

        candidate_store = raw_store or matched_store
        if not candidate_store and raw_intent == "STORE_PERFORMANCE":
            cleaned = re.sub(
                r"(?i)\b(how\s+(is|did|are)|performing|performance|perform|doing|selling|sales|this\s+month|today|what\s+about|tell\s+me\s+about|which\s+store\s+sells|best|which\s+store\s+generated\s+the\s+most\s+revenue|most\s+revenue|generated|which\s+store)\b",
                "",
                question,
            ).strip(" ?.,!")
            if cleaned.lower() in ("what", "which", "store", "stores", "the", "all"):
                cleaned = ""
            if cleaned and len(cleaned) > 1:
                candidate_store = cleaned

        return StructuredIntent(
            intent=raw_intent,
            product=matched_product or candidate_prod,
            product_id=product_id,
            store=matched_store or candidate_store,
            store_id=store_id,
            category=matched_cat,
            start_date=start_date,
            end_date=end_date,
            comparison=raw_comp,
            limit=raw_limit,
            needs_clarification=needs_clarification,
            clarification_question=clarification_msg,
            confidence=confidence,
            raw_query=question,
            date_resolution_note=date_note,
        )
