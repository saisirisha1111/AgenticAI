import re
from google.cloud import bigquery
from Backend.tools.web_search_tool import WebSearchTool


def financial_analysis(structured_data: dict) -> dict:
    """
    Tool to calculate financial metrics and perform benchmarking.
    """

    def extract_number(value) -> float:
        """Extract numeric value from string or number"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = re.sub(r'[^\d.]', '', value)
            return float(cleaned) if cleaned else None
        return None

    def calculate_metrics(financials: dict, traction: dict) -> dict:
        """Calculate key financial metrics"""
        print("Calculate key financial metrics")
        metrics = {}

        revenue = extract_number(financials.get("revenue"))
        current_mrr = extract_number(traction.get("current_mrr"))
        ask_amount = extract_number(financials.get("ask_amount"))
        equity_offered = extract_number(financials.get("equity_offered"))
        burn_rate = extract_number(financials.get("burn_rate"))

        # Annual Revenue
        if current_mrr:
            metrics["annual_revenue"] = current_mrr * 12
        elif revenue:
            metrics["annual_revenue"] = revenue

        # Implied Valuation
        if ask_amount and equity_offered and equity_offered > 0:
            metrics["implied_valuation"] = ask_amount / (equity_offered / 100)

        # Valuation Multiple
        if metrics.get("implied_valuation") and metrics.get("annual_revenue"):
            metrics["revenue_multiple"] = (
                metrics["implied_valuation"] / metrics["annual_revenue"]
            )

        # Runway calculation
        if burn_rate and burn_rate > 0:
            assumed_cash = ask_amount * 2 if ask_amount else 100000
            metrics["runway_months"] = assumed_cash / burn_rate
        print(f"metrics,{metrics}")
        return metrics

    # def get_industry_benchmarks(data: dict) -> dict:
    #     """Get industry benchmarks (simulated)"""
    #     return {
    #         "avg_revenue_multiple": 6.0,
    #         "avg_ltv_cac_ratio": 3.5,
    #         "acceptable_burn_rate": 50000,
    #         "typical_runway": 18,
    #         "seed_stage_valuation_range": {"min": 500000, "max": 5000000},
    #     }

    def insert_benchmarks_into_bigquery(sector: str, stage: str, benchmarks: dict) -> bool:
        """Insert new benchmarks into BigQuery table"""
        print("Insert new benchmarks into BigQuery table")
        try:
            client = bigquery.Client()
            
            table_id = "ai-analyst-poc.startup_benchmarks.industry_benchmarks"
            
            rows_to_insert = [{
                "sector": sector,
                "stage": stage,
                "avg_revenue_multiple": benchmarks.get("avg_revenue_multiple", 6.0),
                "avg_ltv_cac_ratio": benchmarks.get("avg_ltv_cac_ratio", 3.5),
                "acceptable_burn_rate": benchmarks.get("acceptable_burn_rate", 50000),
                "typical_runway": benchmarks.get("typical_runway", 18),
                "min_valuation": benchmarks.get("seed_stage_valuation_range", {}).get("min", 500000),
                "max_valuation": benchmarks.get("seed_stage_valuation_range", {}).get("max", 5000000),
                "data_source": benchmarks.get("data_source", "web_search"),
                "last_updated": bigquery.ScalarQueryParameter("CURRENT_TIMESTAMP", "TIMESTAMP", None)
            }]
            
            errors = client.insert_rows_json(table_id, rows_to_insert)
            
            if errors:
                print(f"Errors inserting into BigQuery: {errors}")
                return False
            else:
                print(f"Successfully inserted benchmarks for {sector} - {stage}")
                return True
                
        except Exception as e:
            print(f"Failed to insert into BigQuery: {e}")
            return False

    def get_industry_benchmarks_from_bigquery(sector: str, stage: str) -> dict:
    """Get industry benchmarks from BigQuery table (sector+stage or sector-only average)"""
    print("Get industry benchmarks from BigQuery table")
    try:
        client = bigquery.Client()

        # ✅ Step 1: Check if (sector, stage) exists
        check_query = f"""
        SELECT COUNT(*) as record_count
        FROM `ai-analyst-poc.startup_benchmarks.vw_industry_benchmarks`
        WHERE sector = '{sector}' AND stage = '{stage}'
        """
        check_job = client.query(check_query)
        check_result = list(check_job)

        if check_result and check_result[0].record_count > 0:
            # Case 1: Exact sector + stage match
            query = f"""
            SELECT 
                avg_revenue_multiple,
                avg_ltv_cac_ratio,
                acceptable_burn_rate,
                typical_runway,
                seed_stage_valuation_range
            FROM `ai-analyst-poc.startup_benchmarks.vw_industry_benchmarks`
            WHERE sector = '{sector}' AND stage = '{stage}'
            LIMIT 1
            """
        else:
            # Case 2: No exact stage match → fallback to sector averages
            query = f"""
            SELECT 
                AVG(avg_revenue_multiple) as avg_revenue_multiple,
                AVG(avg_ltv_cac_ratio) as avg_ltv_cac_ratio,
                AVG(acceptable_burn_rate) as acceptable_burn_rate,
                AVG(typical_runway) as typical_runway
            FROM `ai-analyst-poc.startup_benchmarks.vw_industry_benchmarks`
            WHERE sector = '{sector}'
            """

        query_job = client.query(query)
        results = list(query_job)

        if not results:
            return None

        row = results[0]

        # Default valuation range
        valuation_range = {"min": 500000, "max": 5000000}

        # Only available in Case 1 (exact match)
        if (hasattr(row, 'seed_stage_valuation_range') and 
            row.seed_stage_valuation_range and
            hasattr(row.seed_stage_valuation_range, 'min') and
            hasattr(row.seed_stage_valuation_range, 'max')):
            min_val = row.seed_stage_valuation_range.min
            max_val = row.seed_stage_valuation_range.max
            if min_val is not None and max_val is not None:
                valuation_range = {"min": float(min_val), "max": float(max_val)}

        return {
            "avg_revenue_multiple": float(row.avg_revenue_multiple) if row.avg_revenue_multiple else 6.0,
            "avg_ltv_cac_ratio": float(row.avg_ltv_cac_ratio) if row.avg_ltv_cac_ratio else 3.5,
            "acceptable_burn_rate": float(row.acceptable_burn_rate) if row.acceptable_burn_rate else 50000,
            "typical_runway": float(row.typical_runway) if row.typical_runway else 18,
            "seed_stage_valuation_range": valuation_range,
            "data_source": "bigquery"
        }

    except Exception as e:
        print(f"BigQuery query failed: {e}")
        return None


    # def get_industry_benchmarks_simulated() -> dict:
    #     """Fallback simulated benchmarks"""
    #     return {
    #         "avg_revenue_multiple": 6.0,
    #         "avg_ltv_cac_ratio": 3.5,
    #         "acceptable_burn_rate": 50000,
    #         "typical_runway": 18,
    #         "seed_stage_valuation_range": {"min": 500000, "max": 5000000},
    #         "data_source": "simulated"
    #     }

    def get_industry_benchmarks(data: dict) -> dict:
        """Get industry benchmarks with web search fallback and auto-insertion"""
        # Extract sector and stage from data if available
        sector = data.get("sector")
        stage = data.get("stage", "seed")
        
        # Try BigQuery first with exact match
        benchmarks = get_industry_benchmarks_from_bigquery(sector, stage)
        # print(f"benchmark.....................................{benchmark}")
        if benchmarks is not None:
            benchmarks["query_context"] = {
                "sector_used": sector if sector else "not_provided",
                "stage_used": stage,
                "benchmark_source": "bigquery_exact_match"
            }
            return benchmarks
        
        # # If no exact match, try sector-only match
        # if sector:
        #     sector_benchmarks = get_industry_benchmarks_from_bigquery(sector, None)
        #     if sector_benchmarks is not None:
        #         sector_benchmarks["query_context"] = {
        #             "sector_used": sector,
        #             "stage_used": stage,
        #             "benchmark_source": "bigquery_sector_average"
        #         }
        #         return sector_benchmarks
        
        # If still no data, use web search
        web_search_tool = WebSearchTool()
        web_benchmarks = web_search_tool.search_benchmarks(sector, stage)
         
        # Insert the web search results into BigQuery for future use
        if sector and stage:
            insert_success = insert_benchmarks_into_bigquery(sector, stage, web_benchmarks)
            if insert_success:
                web_benchmarks["data_source"] = "web_search_inserted"
            else:
                web_benchmarks["data_source"] = "web_search_failed_insert"
        
        web_benchmarks["query_context"] = {
            "sector_used": sector if sector else "not_provided",
            "stage_used": stage,
            "benchmark_source": web_benchmarks.get("data_source", "web_search"),
            "confidence": web_benchmarks.get("confidence", "medium")
        }
        
        return web_benchmarks

    def generate_conclusion(metrics: dict, benchmarks: dict, data: dict) -> str:
        """Generate analytical conclusion"""
        conclusions = []

        rev_multiple = metrics.get("revenue_multiple")
        if rev_multiple:
            avg_multiple = benchmarks["avg_revenue_multiple"]
            if rev_multiple > avg_multiple * 1.5:
                conclusions.append(
                    f"High valuation multiple ({rev_multiple:.1f}x vs industry avg {avg_multiple:.1f}x)"
                )
            elif rev_multiple < avg_multiple * 0.7:
                conclusions.append(
                    f"Conservative valuation multiple ({rev_multiple:.1f}x)"
                )
            else:
                conclusions.append(
                    f"Reasonable valuation multiple ({rev_multiple:.1f}x)"
                )

        runway = metrics.get("runway_months")
        if runway:
            typical_runway = benchmarks["typical_runway"]
            if runway < 12:
                conclusions.append(
                    f"Short runway ({runway:.1f} months) - urgent need for funding"
                )
            elif runway > 24:
                conclusions.append(f"Comfortable runway ({runway:.1f} months)")
            else:
                conclusions.append(f"Adequate runway ({runway:.1f} months)")

        growth_trend = data.get("traction", {}).get("mrr_growth_trend", "")
        if growth_trend == "steep":
            conclusions.append("Strong growth trajectory indicated")
        elif growth_trend == "flat":
            conclusions.append("Flat growth trajectory - requires investigation")

        return (
            ". ".join(conclusions) + "."
            if conclusions
            else "Insufficient data for detailed analysis."
        )

    def generate_recommendation(metrics: dict, benchmarks: dict) -> str:
        """Generate investment recommendation"""
        rev_multiple = metrics.get("revenue_multiple")
        runway = metrics.get("runway_months")

        if not rev_multiple:
            return "Cannot assess valuation without revenue data"

        if rev_multiple <= benchmarks["avg_revenue_multiple"]:
            return "Valuation appears reasonable based on revenue multiples"
        elif rev_multiple <= benchmarks["avg_revenue_multiple"] * 1.3:
            return "Slightly premium valuation, justified by strong growth"
        else:
            return "High valuation multiple - requires exceptional growth justification"

    try:
        financials = structured_data.get("financials", {})
        traction = structured_data.get("traction", {})

        metrics = calculate_metrics(financials, traction)
        benchmarks = get_industry_benchmarks(structured_data)
        conclusion = generate_conclusion(metrics, benchmarks, structured_data)

        return {
            "calculated_metrics": metrics,
            "industry_benchmarks": benchmarks,
            "analysis_conclusion": conclusion,
            "recommendation": generate_recommendation(metrics, benchmarks),
        }

    except Exception as e:
        return {"error": f"Financial analysis failed: {str(e)}"}
