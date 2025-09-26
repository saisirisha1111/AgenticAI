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
    
    def search_benchmarks(self, sector: str, stage: str) -> dict:
        """
        Search for industry benchmarks using real APIs with fallback strategy
        """
        print("we are in websearch tool")
        benchmarks = {}
        
        # Try SerpAPI first (more comprehensive)
        if self.serpapi_key:
            serpapi_results = self._search_with_serpapi(sector, stage)
            if serpapi_results and self._validate_benchmarks(serpapi_results):
                benchmarks.update(serpapi_results)
                benchmarks["data_source"] = "serpapi"
        
        # If SerpAPI fails or no key, try Google Custom Search
        if not benchmarks and self.google_search_key and self.google_search_engine_id:
            google_results = self._search_with_google(sector, stage)
            if google_results and self._validate_benchmarks(google_results):
                benchmarks.update(google_results)
                benchmarks["data_source"] = "google_search"
        
        # If both APIs fail, use curated industry data
        if not benchmarks:
            benchmarks = self._get_curated_benchmarks(sector, stage)
            benchmarks["data_source"] = "curated_fallback"
        print("web_serach_benchmarks",benchmarks)
        return benchmarks
    
    def _search_with_serpapi(self, sector: str, stage: str) -> Optional[Dict[str, Any]]:
        """
        Search using SerpAPI (https://serpapi.com/)
        """
        try:
            # Search for industry reports and benchmarks
            queries = [
                f"{sector} startup {stage} stage revenue multiples 2024",
                f"{sector} {stage} funding valuation benchmarks",
                f"{sector} startup metrics LTV CAC ratio industry average",
                f"{sector} {stage} burn rate runway benchmarks"
            ]
            
            all_results = {}
            
            for query in queries:
                params = {
                    'q': query,
                    'api_key': self.serpapi_key,
                    'engine': 'google',
                    'num': 5,
                    'hl': 'en',
                    'gl': 'us'
                }
                
                response = requests.get('https://serpapi.com/search', params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    extracted = self._extract_benchmarks_from_serpapi(data, sector, stage)
                    if extracted:
                        all_results.update(extracted)
            
            return all_results if all_results else None
            
        except Exception as e:
            print(f"SerpAPI search failed: {e}")
            return None
    
    def _search_with_google(self, sector: str, stage: str) -> Optional[Dict[str, Any]]:
        """
        Search using Google Custom Search API
        """
        try:
            query = f"{sector} startup {stage} stage industry benchmarks revenue multiple LTV CAC"
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.google_search_key,
                'cx': self.google_search_engine_id,
                'q': query,
                'num': 5
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._extract_benchmarks_from_google(data, sector, stage)
            
            return None
            
        except Exception as e:
            print(f"Google Search API failed: {e}")
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
    
    def _extract_numbers_from_text(self, text: str, sector: str, stage: str) -> Dict[str, Any]:
        """Use advanced pattern matching to extract financial metrics from text"""
        metrics = {}
        
        patterns = {
            "avg_revenue_multiple": [
                r'revenue multiple[^\d]*(\d+\.?\d*)',
                r'revenue multiple of[^\d]*(\d+\.?\d*)',
                r'(\d+\.?\d*)x revenue',
                r'revenue multiplier.*?(\d+\.?\d*)'
            ],
            "avg_ltv_cac_ratio": [
                r'LTV.*CAC[^\d]*(\d+\.?\d*)',
                r'LTV.*CAC ratio[^\d]*(\d+\.?\d*)',
                r'LTV.CAC[^\d]*(\d+\.?\d*)',
                r'customer lifetime value.*acquisition cost[^\d]*(\d+\.?\d*)'
            ],
            "typical_runway": [
                r'runway[^\d]*(\d+)[^\d]*months',
                r'(\d+)[^\d]*month runway',
                r'cash runway.*?(\d+)[^\d]*months'
            ],
            "acceptable_burn_rate": [
                r'burn rate[^\d]*\$?(\d+[kKmM]?)',
                r'monthly burn[^\d]*\$?(\d+[kKmM]?)',
                r'burning.*?\$?(\d+[kKmM]?)[^\d]*per month'
            ]
        }
        
        for metric, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        value = matches[0]
                        if 'k' in value.lower():
                            num = float(value.lower().replace('k', '')) * 1000
                        elif 'm' in value.lower():
                            num = float(value.lower().replace('m', '')) * 1000000
                        else:
                            num = float(value)
                        
                        num = self._adjust_for_sector_stage(num, metric, sector, stage)
                        metrics[metric] = num
                        break
                    except (ValueError, IndexError):
                        continue
        
        return metrics
    
    def _adjust_for_sector_stage(self, value: float, metric: str, sector: str, stage: str) -> float:
        """Adjust extracted values based on sector and stage knowledge"""
        sector_multipliers = {
            "avg_revenue_multiple": {
                "SaaS": 1.4, "FinTech": 1.6, "HealthTech": 1.3, "E-commerce": 0.8
            },
            "avg_ltv_cac_ratio": {
                "SaaS": 1.2, "FinTech": 1.3, "HealthTech": 1.1, "E-commerce": 0.9
            },
            "typical_runway": {
                "SaaS": 1.1, "FinTech": 1.2, "HealthTech": 1.15, "E-commerce": 0.9
            }
        }
        
        stage_multipliers = {
            "seed": 1.0, "series_a": 1.5, "series_b": 2.0, "series_c": 2.5
        }
        
        multiplier = 1.0
        
        if metric in sector_multipliers and sector in sector_multipliers[metric]:
            multiplier *= sector_multipliers[metric][sector]
        
        if metric == "avg_revenue_multiple" and stage in stage_multipliers:
            multiplier *= stage_multipliers[stage]
        
        return value * multiplier
    
    def _get_curated_benchmarks(self, sector: str, stage: str) -> Dict[str, Any]:
        """Fallback to curated industry data when API searches fail"""
        industry_data = {
            "SaaS": {
                "seed": {"avg_revenue_multiple": 8.5, "avg_ltv_cac_ratio": 4.2, "typical_runway": 20},
                "series_a": {"avg_revenue_multiple": 12.0, "avg_ltv_cac_ratio": 3.8, "typical_runway": 24}
            },
            "E-commerce": {
                "seed": {"avg_revenue_multiple": 4.2, "avg_ltv_cac_ratio": 2.8, "typical_runway": 14},
                "series_a": {"avg_revenue_multiple": 6.5, "avg_ltv_cac_ratio": 3.2, "typical_runway": 18}
            },
            "FinTech": {
                "seed": {"avg_revenue_multiple": 10.5, "avg_ltv_cac_ratio": 4.8, "typical_runway": 22},
                "series_a": {"avg_revenue_multiple": 15.0, "avg_ltv_cac_ratio": 4.2, "typical_runway": 26}
            },
            "HealthTech": {
                "seed": {"avg_revenue_multiple": 9.5, "avg_ltv_cac_ratio": 4.0, "typical_runway": 21},
                "series_a": {"avg_revenue_multiple": 14.0, "avg_ltv_cac_ratio": 3.7, "typical_runway": 25}
            }
        }
        
        sector_data = industry_data.get(sector, {})
        stage_data = sector_data.get(stage, {})
        
        if stage_data:
            return {
                **stage_data,
                "acceptable_burn_rate": 50000,
                "seed_stage_valuation_range": {"min": 500000, "max": 5000000},
                "confidence": "high"
            }
        
        return {
            "avg_revenue_multiple": 6.0,
            "avg_ltv_cac_ratio": 3.5,
            "acceptable_burn_rate": 50000,
            "typical_runway": 18,
            "seed_stage_valuation_range": {"min": 500000, "max": 5000000},
            "confidence": "low"
        }
    
    def _validate_benchmarks(self, benchmarks: Dict[str, Any]) -> bool:
        """Validate that extracted benchmarks are reasonable"""
        required_metrics = ["avg_revenue_multiple", "avg_ltv_cac_ratio"]
        
        for metric in required_metrics:
            if metric not in benchmarks:
                return False
            
            value = benchmarks[metric]
            if metric == "avg_revenue_multiple" and (value < 1 or value > 50):
                return False
            if metric == "avg_ltv_cac_ratio" and (value < 1 or value > 10):
                return False
        
        return True