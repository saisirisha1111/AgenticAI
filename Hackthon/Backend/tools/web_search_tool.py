import os
import requests
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime
from google.cloud import bigquery

class WebSearchTool:
    """Tool to search for industry benchmarks online using real APIs"""
    
    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.google_search_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.google_search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro", temperature=0.2
        )
    
    def search_benchmarks(self, sector: str, stage: str) -> dict:
        """
        Search for industry benchmarks using real APIs with fallback strategy
        """
        print("we are in websearch tool")
        benchmarks = {}
        
        # Try SerpAPI first (more comprehensive)
        if self.serpapi_key:
            serpapi_results = self._search_with_serpapi(sector, stage)
            print("serpapi_results#######################**********",serpapi_results)
            if serpapi_results and self._validate_benchmarks(serpapi_results, stage):
                benchmarks.update(serpapi_results)
                benchmarks["data_source"] = "serpapi"
        
        # If SerpAPI fails or no key, try Google Custom Search
        if not benchmarks and self.google_search_key and self.google_search_engine_id:
            google_results = self._search_with_google(sector, stage)
            print("google_results#######################**********",google_results)
            if google_results and self._validate_benchmarks(google_results, stage):
                benchmarks.update(google_results)
                benchmarks["data_source"] = "google_search"
        
        # If both APIs fail, use curated industry data
        # if not benchmarks:
        #     benchmarks = self._get_curated_benchmarks(sector, stage)
        #     benchmarks["data_source"] = "curated_fallback"
        print("web_serach_benchmarks",benchmarks)
        return benchmarks
    

    def _search_with_serpapi(self, sector: str, stage: str) -> Optional[Dict[str, Any]]:
        """
        Search using SerpAPI (https://serpapi.com/)
        """
        print("we are in serp api search...........")
        try:
            # 🧠 Refined, context-rich queries
            queries = [
                f"{sector} startup {stage} stage average revenue multiple 2024 site:crunchbase.com OR site:cbinsights.com OR site:techcrunch.com",
                f"{sector} startup {stage} stage valuation benchmarks 2024 site:tracxn.com OR site:dealroom.co OR site:angel.co",
                f"{sector} {stage} startup average LTV CAC ratio metrics site:saastr.com OR site:forentrepreneurs.com",
                f"{sector} {stage} stage startup typical runway and monthly burn rate benchmarks site:medium.com OR site:startupschool.org",
                f"{sector} {stage} stage valuation range pre-money post-money 2024 site:techcrunch.com OR site:dealroom.co",
                f"{sector} startup {stage} KPIs benchmarks 2024 site:crunchbase.com OR site:cbinsights.com",
            ]

            all_results = {}

            # 🔁 Iterate through all smart queries
            for query in queries:
                params = {
                    "q": query,
                    "api_key": self.serpapi_key,
                    "engine": "google",
                    "num": 10,
                    "hl": "en",
                    "gl": "us",
                    "safe": "active"
                }

                response = requests.get("https://serpapi.com/search", params=params, timeout=15)

                if response.status_code != 200:
                    print(f"⚠️ SerpAPI request failed with status {response.status_code} for query: {query}")
                    continue

                data = response.json()
                organic_results = data.get("organic_results", [])
                if not organic_results:
                    continue

                # 🧩 Combine top titles/snippets for LLM extraction
                combined_text = " ".join(
                    f"{item.get('title', '')}. {item.get('snippet', '')}"
                    for item in organic_results[:5]
                )

                # ✅ Use LLM to extract benchmarks instead of regex
                extracted = self._extract_numbers_from_text(combined_text, sector, stage)

                if extracted:
                    print(f"✅ Extracted metrics from query: '{query}' → {extracted}")
                    all_results.update(extracted)

            # 🧠 Post-processing: prefer higher-confidence LLM outputs
            return all_results if all_results else None

        except Exception as e:
            print(f"❌ SerpAPI search failed: {e}")
            return None
    
    def _search_with_google(self, sector: str, stage: str) -> Optional[Dict[str, Any]]:
        """
        Search using Google Custom Search API
        """
        print("we are in google seraching ..........")
        try:
            # 🧠 Smarter, context-rich benchmark queries
            queries = [
                f"{sector} startup {stage} stage average revenue multiple 2024 site:crunchbase.com OR site:cbinsights.com OR site:techcrunch.com",
                f"{sector} {stage} funding and valuation benchmarks 2024 site:dealroom.co OR site:tracxn.com",
                f"{sector} startup {stage} average LTV CAC ratio benchmarks site:saastr.com OR site:forentrepreneurs.com",
                f"{sector} startup {stage} stage typical runway and burn rate benchmarks site:medium.com OR site:startupschool.org",
                f"{sector} {stage} stage startup pre-money and post-money valuation range site:dealroom.co OR site:techcrunch.com",
                f"{sector} startup {stage} KPIs metrics 2024 site:crunchbase.com OR site:cbinsights.com",
                f"{sector} startup {stage} industry performance benchmarks 2024",
            ]

            all_results = {}

            for query in queries:
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": self.google_search_key,
                    "cx": self.google_search_engine_id,
                    "q": query,
                    "num": 10,
                    "lr": "lang_en"
                }

                response = requests.get(url, params=params, timeout=15)

                if response.status_code != 200:
                    print(f"⚠️ Google Search API failed with status {response.status_code} for query: {query}")
                    continue

                data = response.json()
                if "items" not in data:
                    continue

                # 🧩 Combine top snippets & titles for LLM extraction
                combined_text = " ".join(
                    f"{item.get('title', '')}. {item.get('snippet', '')}"
                    for item in data["items"][:5]
                )

                # ✅ Use LLM (not regex) to extract benchmark metrics
                extracted = self._extract_numbers_from_text(combined_text, sector, stage)

                if extracted:
                    print(f"✅ Extracted metrics from Google query: '{query}' → {extracted}")
                    all_results.update(extracted)

            # 🧠 Return all gathered metrics (or None if no useful results)
            return all_results if all_results else None

        except Exception as e:
            print(f"❌ Google Search API error: {e}")
            return None
        
    def _extract_benchmarks_from_serpapi(self, data: Dict[str, Any], sector: str, stage: str) -> Dict[str, Any]:
        """Extract benchmark numbers from SerpAPI results"""
        benchmarks = {}
        
        if 'organic_results' not in data:
            return benchmarks
        
        full_text = ""
        for result in data['organic_results'][:3]:
            snippet = result.get('snippet', '')
            full_text += snippet + " "
        
        benchmarks.update(self._extract_numbers_from_text(full_text, sector, stage))
        
        return benchmarks
    
    def _extract_benchmarks_from_google(self, data: Dict[str, Any], sector: str, stage: str) -> Dict[str, Any]:
        """Extract benchmark numbers from Google Custom Search results"""
        benchmarks = {}
        
        if 'items' not in data:
            return benchmarks
        
        full_text = ""
        for item in data['items'][:3]:
            snippet = item.get('snippet', '')
            full_text += snippet + " "
        
        benchmarks.update(self._extract_numbers_from_text(full_text, sector, stage))
        
        return benchmarks
    
    # def _extract_numbers_from_text(self, text: str, sector: str, stage: str) -> Dict[str, Any]:
    #     """Use advanced pattern matching to extract financial metrics from text"""
    #     metrics = {}
        
    #     patterns = {
    #         "avg_revenue_multiple": [
    #             r'revenue multiple[^\d]*(\d+\.?\d*)',
    #             r'revenue multiple of[^\d]*(\d+\.?\d*)',
    #             r'(\d+\.?\d*)x revenue',
    #             r'revenue multiplier.*?(\d+\.?\d*)'
    #         ],
    #         "avg_ltv_cac_ratio": [
    #             r'LTV.*CAC[^\d]*(\d+\.?\d*)',
    #             r'LTV.*CAC ratio[^\d]*(\d+\.?\d*)',
    #             r'LTV.CAC[^\d]*(\d+\.?\d*)',
    #             r'customer lifetime value.*acquisition cost[^\d]*(\d+\.?\d*)'
    #         ],
    #         "typical_runway": [
    #             r'runway[^\d]*(\d+)[^\d]*months',
    #             r'(\d+)[^\d]*month runway',
    #             r'cash runway.*?(\d+)[^\d]*months'
    #         ],
    #         "acceptable_burn_rate": [
    #             r'burn rate[^\d]*\$?(\d+[kKmM]?)',
    #             r'monthly burn[^\d]*\$?(\d+[kKmM]?)',
    #             r'burning.*?\$?(\d+[kKmM]?)[^\d]*per month'
    #         ],
    #         "valuation_min": [
    #             r'valuation.*?\$?(\d+[kKmM]?)[^\d]*(\d+[kKmM]?)[^\d]*to',
    #             r'valuation range.*?\$?(\d+[kKmM]?)[^\d]*\s*-\s*',
    #             r'valued between.*?\$?(\d+[kKmM]?)[^\d]*and',
    #             r'pre-money valuation.*?\$?(\d+[kKmM]?)',
    #             r'seed valuation.*?\$?(\d+[kKmM]?)'
    #         ],
    #         "valuation_max": [
    #             r'valuation.*?\$?(\d+[kKmM]?)[^\d]*to[^\d]*\$?(\d+[kKmM]?)',
    #             r'valuation range.*?\$?\d+[kKmM]?[^\d]*\s*-\s*\$?(\d+[kKmM]?)',
    #             r'valued between.*?\$?\d+[kKmM]?[^\d]*and[^\d]*\$?(\d+[kKmM]?)',
    #             r'up to.*?\$?(\d+[kKmM]?)[^\d]*valuation',
    #             r'valuation cap.*?\$?(\d+[kKmM]?)'
    #         ]
    #     }
        
    #     for metric, pattern_list in patterns.items():
    #         for pattern in pattern_list:
    #             matches = re.findall(pattern, text, re.IGNORECASE)
    #             if matches:
    #                 try:
    #                     # Handle both single matches and tuples
    #                     if isinstance(matches[0], tuple):
    #                         # Take the first non-empty element from the tuple
    #                         value = next((item for item in matches[0] if item), None)
    #                     else:
    #                         value = matches[0]
                        
    #                     if not value:
    #                         continue
                            
    #                     # Convert string value to number
    #                     value_str = str(value).lower()
    #                     if 'k' in value_str:
    #                         num = float(value_str.replace('k', '')) * 1000
    #                     elif 'm' in value_str:
    #                         num = float(value_str.replace('m', '')) * 1000000
    #                     else:
    #                         num = float(value_str)
                        
    #                     num = self._adjust_for_sector_stage(num, metric, sector, stage)
    #                     metrics[metric] = num
    #                     break
    #                 except (ValueError, IndexError, StopIteration) as e:
    #                     print(f"Error processing {metric} with value '{value}': {e}")
    #                     continue

    #     valuation_range = self._build_valuation_range(metrics, sector, stage)
    #     if valuation_range:
    #         metrics["seed_stage_valuation_range"] = valuation_range
    #     return metrics
    
    # def _build_valuation_range(self, metrics: Dict[str, Any], sector: str, stage: str) -> Optional[Dict[str, float]]:
    #     """Build valuation range from extracted min/max values or use defaults"""
    #     min_val = metrics.get("valuation_min")
    #     max_val = metrics.get("valuation_max")
        
    #     # If we have both min and max, use them
    #     if min_val and max_val:
    #         return {"min": min_val, "max": max_val}
        
    #     # If we have only one, estimate the other
    #     elif min_val and not max_val:
    #         return {"min": min_val, "max": min_val * 3}  # Common 3x multiple
        
    #     elif max_val and not min_val:
    #         return {"min": max_val / 3, "max": max_val}  # Common 3x multiple
        
        # else:
        #     # Use sector/stage specific defaults
        #     return self._get_default_valuation_range(sector, stage)

    # def _get_default_valuation_range(self, sector: str, stage: str) -> Dict[str, float]:
    #     """Get default valuation ranges based on sector and stage"""
    #     # Base valuation ranges by stage (in USD)
    #     stage_ranges = {
    #         "pre_seed": {"min": 250000, "max": 2000000},
    #         "seed": {"min": 500000, "max": 5000000},
    #         "series_a": {"min": 3000000, "max": 15000000},
    #         "series_b": {"min": 15000000, "max": 50000000},
    #         "series_c": {"min": 50000000, "max": 100000000},
    #         "series_d+": {"min": 100000000, "max": 500000000}
    #     }
    
    #     # Sector multipliers (some sectors command higher valuations)
    #     sector_multipliers = {
    #         "AI": 1.8, "FinTech": 1.6, "HealthTech": 1.5, 
    #         "SaaS": 1.4, "CleanTech": 1.3, "Biotech": 2.0,
    #         "E-commerce": 0.9, "Marketplace": 1.2, "Hardware": 0.8
    #     }
        
    #     # Get base range for stage
    #     base_range = stage_ranges.get(stage.lower(), stage_ranges["seed"])
    #     multiplier = sector_multipliers.get(sector, 1.0)
        
    #     return {
    #         "min": base_range["min"] * multiplier,
    #         "max": base_range["max"] * multiplier
    #     }
    

    # def _adjust_for_sector_stage(self, value: float, metric: str, sector: str, stage: str) -> float:
    #     """Adjust extracted values based on sector and stage knowledge"""
    #     sector_multipliers = {
    #         "avg_revenue_multiple": {
    #             "SaaS": 1.4, "FinTech": 1.6, "HealthTech": 1.3, "E-commerce": 0.8
    #         },
    #         "avg_ltv_cac_ratio": {
    #             "SaaS": 1.2, "FinTech": 1.3, "HealthTech": 1.1, "E-commerce": 0.9
    #         },
    #         "typical_runway": {
    #             "SaaS": 1.1, "FinTech": 1.2, "HealthTech": 1.15, "E-commerce": 0.9
    #         }
    #     }
        
    #     stage_multipliers = {
    #         "seed": 1.0, "series_a": 1.5, "series_b": 2.0, "series_c": 2.5
    #     }
        
    #     multiplier = 1.0
        
    #     if metric in sector_multipliers and sector in sector_multipliers[metric]:
    #         multiplier *= sector_multipliers[metric][sector]
        
    #     if metric == "avg_revenue_multiple" and stage in stage_multipliers:
    #         multiplier *= stage_multipliers[stage]
        
    #     return value * multiplier
    
    # def _get_curated_benchmarks(self, sector: str, stage: str) -> Dict[str, Any]:
    #     """Fallback to curated industry data when API searches fail"""
    #     industry_data = {
    #         "SaaS": {
    #             "seed": {"avg_revenue_multiple": 8.5, "avg_ltv_cac_ratio": 4.2, "typical_runway": 20},
    #             "series_a": {"avg_revenue_multiple": 12.0, "avg_ltv_cac_ratio": 3.8, "typical_runway": 24}
    #         },
    #         "E-commerce": {
    #             "seed": {"avg_revenue_multiple": 4.2, "avg_ltv_cac_ratio": 2.8, "typical_runway": 14},
    #             "series_a": {"avg_revenue_multiple": 6.5, "avg_ltv_cac_ratio": 3.2, "typical_runway": 18}
    #         },
    #         "FinTech": {
    #             "seed": {"avg_revenue_multiple": 10.5, "avg_ltv_cac_ratio": 4.8, "typical_runway": 22},
    #             "series_a": {"avg_revenue_multiple": 15.0, "avg_ltv_cac_ratio": 4.2, "typical_runway": 26}
    #         },
    #         "HealthTech": {
    #             "seed": {"avg_revenue_multiple": 9.5, "avg_ltv_cac_ratio": 4.0, "typical_runway": 21},
    #             "series_a": {"avg_revenue_multiple": 14.0, "avg_ltv_cac_ratio": 3.7, "typical_runway": 25}
    #         }
    #     }
        
    #     sector_data = industry_data.get(sector, {})
    #     stage_data = sector_data.get(stage, {})
        
    #     if stage_data:
    #         return {
    #             **stage_data,
    #             "acceptable_burn_rate": 50000,
    #             "confidence": "high"
    #         }
        
    #     # General startup benchmarks with dynamic valuation range
    #     default_valuation = self._get_default_valuation_range(sector, stage)
    #     return {
    #         "avg_revenue_multiple": 6.0,
    #         "avg_ltv_cac_ratio": 3.5,
    #         "acceptable_burn_rate": 50000,
    #         "typical_runway": 18,
    #         "seed_stage_valuation_range": default_valuation,
    #         "confidence": "low"
    #     }
    



    def _extract_numbers_from_text(self, text: str, sector: str, stage: str) -> Dict[str, Any]:
        """
        Use LLM to intelligently extract structured financial benchmark metrics from text.
        """
        prompt = f"""
        You are a financial data extraction expert. 
        Extract key startup benchmark metrics from the following text.

        **Text:**
        {text}

        **Context:**
        Sector: {sector}
        Stage: {stage}

        Extract the following metrics if present, else return null:
        - avg_revenue_multiple (float)
        - avg_ltv_cac_ratio (float)
        - typical_runway (in months, integer)
        - acceptable_burn_rate (in USD per month, float)
        - seed_stage_valuation_range (object with "min" and "max" in USD)

        Respond **only** in this JSON format:
        {{
            "avg_revenue_multiple": <float or null>,
            "avg_ltv_cac_ratio": <float or null>,
            "typical_runway": <int or null>,
            "acceptable_burn_rate": <float or null>,
            "seed_stage_valuation_range": {{
                "min": <float or null>,
                "max": <float or null>
            }}
        }}
        """

        try:
            response = self.llm.invoke(prompt)
            response_text = response.content.strip()

            # Try parsing JSON safely
            data = json.loads(response_text)
            print("✅ LLM Extracted Benchmarks:", data)
            return data
        except Exception as e:
            print(f"❌ LLM extraction failed: {e}")
            return {}

    
    def _validate_benchmarks(self, benchmarks: Dict[str, Any], stage: str) -> bool:
        """Strict validation of benchmarks with cross-metric consistency checks"""
        
        # Realistic ranges by stage
        realistic_ranges = {
            "avg_revenue_multiple": {
                "seed": (3.0, 12.0),
                "series_a": (6.0, 20.0),
                "series_b": (8.0, 25.0),
                "series_c": (10.0, 30.0),
                "default": (4.0, 15.0)
            },
            "avg_ltv_cac_ratio": {
                "seed": (2.0, 6.0),
                "series_a": (2.5, 5.5),
                "series_b": (3.0, 5.0),
                "series_c": (3.5, 4.5),
                "default": (2.0, 5.0)
            },
            "typical_runway": {
                "seed": (12, 24),
                "series_a": (18, 36),
                "series_b": (24, 48),
                "series_c": (30, 60),
                "default": (12, 36)
            },
            "acceptable_burn_rate": {
                "seed": (10000, 100000),
                "series_a": (50000, 300000),
                "series_b": (100000, 500000),
                "series_c": (250000, 1000000),
                "default": (20000, 200000)
            }
        }
        
        # Required metrics
        required_metrics = ["avg_revenue_multiple", "avg_ltv_cac_ratio"]
        for metric in required_metrics:
            if metric not in benchmarks:
                print(f"❌ Missing required metric: {metric}")
                return False
        
        # Individual metric validation
        valid_metrics = 0
        total_metrics = 0
        
        for metric, value in benchmarks.items():
            if metric in realistic_ranges:
                total_metrics += 1
                
                # Get stage-specific range
                stage_ranges = realistic_ranges[metric]
                min_val, max_val = stage_ranges.get(stage.lower(), stage_ranges.get("default", (0, float('inf'))))
                
                # Check range
                if min_val <= value <= max_val:
                    valid_metrics += 1
                    print(f"✅ {metric}: {value} (within range {min_val}-{max_val})")
                else:
                    print(f"❌ {metric}: {value} (outside range {min_val}-{max_val})")
        
        # ✅ Additional: Validate valuation range (seed_stage_valuation_range)
        if "seed_stage_valuation_range" in benchmarks:
            val_range = benchmarks["seed_stage_valuation_range"]
            min_val = val_range.get("min")
            max_val = val_range.get("max")

            # Stage-specific realistic valuation ranges (in USD)
            valuation_ranges = {
                "pre_seed": (250000, 2000000),
                "seed": (500000, 5000000),
                "series_a": (3000000, 15000000),
                "series_b": (15000000, 50000000),
                "series_c": (50000000, 100000000),
                "series_d+": (100000000, 500000000),
                "default": (500000, 10000000)
            }

            min_real, max_real = valuation_ranges.get(stage.lower(), valuation_ranges["default"])

            # Validation checks
            if (min_val is not None and max_val is not None and 
                min_real <= min_val <= max_real and
                min_real <= max_val <= max_real and
                min_val < max_val):
                valid_metrics += 1
                print(f"✅ Valuation range ${min_val:,.0f}–${max_val:,.0f} (within realistic bounds ${min_real:,}-${max_real:,})")
            else:
                print(f"❌ Valuation range ${min_val:,.0f}–${max_val:,.0f} (outside realistic bounds ${min_real:,}-${max_real:,})")

        # Cross-metric consistency checks
        consistency_checks = self._check_benchmark_consistency(benchmarks)
        valid_consistency = sum(consistency_checks.values())
        
        # Final validation criteria
        metric_success_rate = valid_metrics / total_metrics if total_metrics > 0 else 0
        consistency_success_rate = valid_consistency / len(consistency_checks) if consistency_checks else 1
        
        print(f"Metric validation: {valid_metrics}/{total_metrics} ({metric_success_rate:.1%})")
        print(f"Consistency validation: {valid_consistency}/{len(consistency_checks)} ({consistency_success_rate:.1%})")
        
        # Require both good metric quality and consistency
        if metric_success_rate >= 0.7 and consistency_success_rate >= 0.7:
            print("✅ Benchmarks validation PASSED")
            return True
        else:
            print("❌ Benchmarks validation FAILED")
            return False


    def _check_benchmark_consistency(self, benchmarks: Dict[str, Any]) -> Dict[str, bool]:
        """Check internal consistency between different benchmark metrics"""
        checks = {}
        
        # Check 1: Revenue multiple vs LTV/CAC ratio
        # Higher LTV/CAC should generally correlate with higher multiples
        if "avg_revenue_multiple" in benchmarks and "avg_ltv_cac_ratio" in benchmarks:
            multiple = benchmarks["avg_revenue_multiple"]
            ltv_cac = benchmarks["avg_ltv_cac_ratio"]
            
            # Rough consistency check
            expected_min_multiple = ltv_cac * 1.5  # Very rough heuristic
            checks["multiple_vs_ltv_cac"] = multiple >= expected_min_multiple
            print(f"Consistency - Multiple {multiple} vs LTV/CAC {ltv_cac}: {checks['multiple_vs_ltv_cac']}")
        
        # Check 2: Burn rate vs runway relationship
        if "acceptable_burn_rate" in benchmarks and "typical_runway" in benchmarks:
            burn_rate = benchmarks["acceptable_burn_rate"]
            runway = benchmarks["typical_runway"]
            
            # Burn rate should be reasonable for the runway
            # Typical seed: $50k burn × 18 months = $900k total funding
            reasonable_burn = burn_rate <= (2000000 / runway)  # $2M max funding assumption
            checks["burn_vs_runway"] = reasonable_burn
            print(f"Consistency - Burn rate ${burn_rate:,.0f} vs {runway} months runway: {checks['burn_vs_runway']}")
        
        # Check 3: Valuation range sanity
        if "seed_stage_valuation_range" in benchmarks:
            val_range = benchmarks["seed_stage_valuation_range"]
            min_val = val_range.get("min", 0)
            max_val = val_range.get("max", 0)
            
            checks["valuation_range_sane"] = (0 < min_val < max_val and max_val/min_val <= 10)
            print(f"Consistency - Valuation range ${min_val:,.0f}-${max_val:,.0f}: {checks['valuation_range_sane']}")
        
        return checks