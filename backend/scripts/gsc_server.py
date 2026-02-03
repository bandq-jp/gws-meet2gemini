#!/usr/bin/env python3
"""
Google Search Console MCP Server.

Based on https://github.com/AminForou/mcp-gsc
Modified to use service account authentication via GOOGLE_APPLICATION_CREDENTIALS
for consistent authentication with GA4 MCP server.
"""

import json
import os
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("gsc-server")

# Service account file path from environment variable
CREDENTIALS_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

mcp = FastMCP("gsc-server")

_service = None


def get_gsc_service():
    """Get or create authenticated GSC service using service account."""
    global _service
    if _service:
        return _service

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Service account file not found: {CREDENTIALS_FILE}. "
            "Set GOOGLE_APPLICATION_CREDENTIALS environment variable."
        )

    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )

    _service = build("searchconsole", "v1", credentials=creds)
    return _service


# ── Property Management ──


@mcp.tool()
def list_properties() -> str:
    """List all Search Console properties the service account has access to."""
    service = get_gsc_service()
    site_list = service.sites().list().execute()
    sites = site_list.get("siteEntry", [])
    if not sites:
        return "No Search Console properties found."
    result = "Search Console Properties:\n\n"
    for site in sites:
        result += f"- **{site['siteUrl']}** (Permission: {site['permissionLevel']})\n"
    return result


@mcp.tool()
def get_site_details(site_url: str) -> str:
    """Get detailed information about a specific Search Console property."""
    service = get_gsc_service()
    try:
        site = service.sites().get(siteUrl=site_url).execute()
        return json.dumps(site, indent=2)
    except Exception as e:
        return f"Error getting site details: {str(e)}"


# ── Search Analytics ──


@mcp.tool()
def get_search_analytics(
    site_url: str,
    days: int = 28,
    dimensions: str = "query",
) -> str:
    """Get search performance data for a site.

    Args:
        site_url: The URL of the site (e.g., 'sc-domain:example.com' or 'https://example.com/')
        days: Number of days to look back (default: 28)
        dimensions: Comma-separated dimensions: query, page, country, device, date, searchAppearance
    """
    service = get_gsc_service()
    from datetime import datetime, timedelta

    end_date = datetime.now() - timedelta(days=3)
    start_date = end_date - timedelta(days=days)

    dim_list = [d.strip() for d in dimensions.split(",")]
    request_body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "dimensions": dim_list,
        "rowLimit": 25,
    }
    try:
        response = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=request_body)
            .execute()
        )
        rows = response.get("rows", [])
        if not rows:
            return f"No data found for {site_url} in the last {days} days."

        result = f"Search Analytics for {site_url} (last {days} days):\n\n"
        result += "| " + " | ".join(dim_list) + " | Clicks | Impressions | CTR | Position |\n"
        result += "| " + " | ".join(["---"] * (len(dim_list) + 4)) + " |\n"

        for row in rows:
            keys = row.get("keys", [])
            clicks = row.get("clicks", 0)
            impressions = row.get("impressions", 0)
            ctr = row.get("ctr", 0) * 100
            position = row.get("position", 0)
            result += f"| {' | '.join(str(k) for k in keys)} | {clicks:,} | {impressions:,} | {ctr:.1f}% | {position:.1f} |\n"

        return result
    except Exception as e:
        return f"Error fetching analytics: {str(e)}"


@mcp.tool()
def get_performance_overview(site_url: str, days: int = 28) -> str:
    """Get a performance overview with summary metrics and daily trends."""
    service = get_gsc_service()
    from datetime import datetime, timedelta

    end_date = datetime.now() - timedelta(days=3)
    start_date = end_date - timedelta(days=days)

    try:
        # Summary
        summary_body = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
        }
        summary = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=summary_body)
            .execute()
        )
        rows = summary.get("rows", [{}])
        total = rows[0] if rows else {}
        total_clicks = total.get("clicks", 0)
        total_impressions = total.get("impressions", 0)
        avg_ctr = total.get("ctr", 0) * 100
        avg_position = total.get("position", 0)

        result = f"## Performance Overview: {site_url}\n"
        result += f"**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n\n"
        result += f"| Metric | Value |\n|---|---|\n"
        result += f"| Total Clicks | {total_clicks:,} |\n"
        result += f"| Total Impressions | {total_impressions:,} |\n"
        result += f"| Average CTR | {avg_ctr:.1f}% |\n"
        result += f"| Average Position | {avg_position:.1f} |\n\n"

        # Daily trend
        daily_body = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "dimensions": ["date"],
        }
        daily = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=daily_body)
            .execute()
        )
        daily_rows = daily.get("rows", [])
        if daily_rows:
            result += "### Daily Trend\n\n"
            result += "| Date | Clicks | Impressions | CTR | Position |\n"
            result += "|---|---|---|---|---|\n"
            for row in sorted(daily_rows, key=lambda r: r["keys"][0]):
                d = row["keys"][0]
                result += f"| {d} | {row.get('clicks', 0):,} | {row.get('impressions', 0):,} | {row.get('ctr', 0) * 100:.1f}% | {row.get('position', 0):.1f} |\n"

        return result
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_advanced_search_analytics(
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: str = "query",
    search_type: str = "web",
    row_limit: int = 100,
    sort_by: str = "clicks",
    filter_dimension: str = "",
    filter_expression: str = "",
    filter_operator: str = "contains",
) -> str:
    """Advanced search analytics with filtering and sorting.

    Args:
        site_url: Site URL
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        dimensions: Comma-separated: query, page, country, device, date, searchAppearance
        search_type: web, image, video, news, googleNews, discover
        row_limit: Max rows (up to 25000)
        sort_by: clicks, impressions, ctr, position
        filter_dimension: Dimension to filter on
        filter_expression: Filter value
        filter_operator: contains, equals, notContains, notEquals, includingRegex, excludingRegex
    """
    service = get_gsc_service()
    dim_list = [d.strip() for d in dimensions.split(",")]
    request_body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dim_list,
        "type": search_type,
        "rowLimit": min(row_limit, 25000),
    }

    if filter_dimension and filter_expression:
        request_body["dimensionFilterGroups"] = [
            {
                "filters": [
                    {
                        "dimension": filter_dimension,
                        "operator": filter_operator,
                        "expression": filter_expression,
                    }
                ]
            }
        ]

    try:
        response = (
            service.searchanalytics()
            .query(siteUrl=site_url, body=request_body)
            .execute()
        )
        rows = response.get("rows", [])
        if not rows:
            return f"No data found for the specified criteria."

        sort_map = {"clicks": "clicks", "impressions": "impressions", "ctr": "ctr", "position": "position"}
        sort_key = sort_map.get(sort_by, "clicks")
        reverse = sort_key != "position"
        rows.sort(key=lambda r: r.get(sort_key, 0), reverse=reverse)

        result = f"Advanced Analytics ({start_date} to {end_date}):\n\n"
        result += "| " + " | ".join(dim_list) + " | Clicks | Impressions | CTR | Position |\n"
        result += "| " + " | ".join(["---"] * (len(dim_list) + 4)) + " |\n"

        for row in rows:
            keys = row.get("keys", [])
            clicks = row.get("clicks", 0)
            impressions = row.get("impressions", 0)
            ctr = row.get("ctr", 0) * 100
            position = row.get("position", 0)
            result += f"| {' | '.join(str(k) for k in keys)} | {clicks:,} | {impressions:,} | {ctr:.1f}% | {position:.1f} |\n"

        return result
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def compare_search_periods(
    site_url: str,
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
    dimensions: str = "query",
    limit: int = 20,
) -> str:
    """Compare search performance between two time periods.

    Args:
        site_url: Site URL
        period1_start/end: First period (YYYY-MM-DD)
        period2_start/end: Second period (YYYY-MM-DD)
        dimensions: Comma-separated dimensions
        limit: Max rows per period
    """
    service = get_gsc_service()
    dim_list = [d.strip() for d in dimensions.split(",")]

    def fetch_period(start, end):
        body = {
            "startDate": start,
            "endDate": end,
            "dimensions": dim_list,
            "rowLimit": limit,
        }
        return (
            service.searchanalytics()
            .query(siteUrl=site_url, body=body)
            .execute()
            .get("rows", [])
        )

    try:
        rows1 = fetch_period(period1_start, period1_end)
        rows2 = fetch_period(period2_start, period2_end)

        data1 = {tuple(r["keys"]): r for r in rows1}
        data2 = {tuple(r["keys"]): r for r in rows2}
        all_keys = set(data1.keys()) | set(data2.keys())

        result = f"## Period Comparison\n"
        result += f"**Period 1:** {period1_start} to {period1_end}\n"
        result += f"**Period 2:** {period2_start} to {period2_end}\n\n"
        result += "| " + " | ".join(dim_list) + " | P1 Clicks | P2 Clicks | Change | P1 Impr | P2 Impr | P1 CTR | P2 CTR | P1 Pos | P2 Pos |\n"
        result += "| " + " | ".join(["---"] * (len(dim_list) + 9)) + " |\n"

        sorted_keys = sorted(
            all_keys,
            key=lambda k: data1.get(k, {}).get("clicks", 0),
            reverse=True,
        )

        for keys in sorted_keys[:limit]:
            r1 = data1.get(keys, {})
            r2 = data2.get(keys, {})
            c1 = r1.get("clicks", 0)
            c2 = r2.get("clicks", 0)
            diff = c1 - c2
            sign = "+" if diff > 0 else ""
            result += (
                f"| {' | '.join(str(k) for k in keys)}"
                f" | {c1:,} | {c2:,} | {sign}{diff:,}"
                f" | {r1.get('impressions', 0):,} | {r2.get('impressions', 0):,}"
                f" | {r1.get('ctr', 0) * 100:.1f}% | {r2.get('ctr', 0) * 100:.1f}%"
                f" | {r1.get('position', 0):.1f} | {r2.get('position', 0):.1f} |\n"
            )

        return result
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def get_search_by_page_query(
    site_url: str,
    page_url: str,
    days: int = 28,
) -> str:
    """Get search queries and performance for a specific page.

    Args:
        site_url: Site URL
        page_url: The specific page URL to analyze
        days: Number of days (default 28)
    """
    service = get_gsc_service()
    from datetime import datetime, timedelta

    end_date = datetime.now() - timedelta(days=3)
    start_date = end_date - timedelta(days=days)

    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "dimensions": ["query"],
        "dimensionFilterGroups": [
            {"filters": [{"dimension": "page", "operator": "equals", "expression": page_url}]}
        ],
        "rowLimit": 50,
    }

    try:
        response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        rows = response.get("rows", [])
        if not rows:
            return f"No search data found for {page_url}"

        result = f"## Queries for: {page_url}\n\n"
        result += "| Query | Clicks | Impressions | CTR | Position |\n"
        result += "|---|---|---|---|---|\n"
        for row in sorted(rows, key=lambda r: r.get("clicks", 0), reverse=True):
            q = row["keys"][0]
            result += f"| {q} | {row.get('clicks', 0):,} | {row.get('impressions', 0):,} | {row.get('ctr', 0) * 100:.1f}% | {row.get('position', 0):.1f} |\n"
        return result
    except Exception as e:
        return f"Error: {str(e)}"


# ── URL Inspection ──


@mcp.tool()
def inspect_url_enhanced(site_url: str, page_url: str) -> str:
    """Inspect a URL for indexing status, crawl info, and rich results."""
    service = get_gsc_service()
    try:
        result_data = (
            service.urlInspection()
            .index()
            .inspect(body={"inspectionUrl": page_url, "siteUrl": site_url})
            .execute()
        )
        r = result_data.get("inspectionResult", {})
        idx = r.get("indexStatusResult", {})
        crawl = idx.get("crawledAs", "N/A")
        robot = idx.get("robotsTxtState", "N/A")
        indexing = idx.get("indexingState", "N/A")
        verdict = idx.get("verdict", "N/A")
        last_crawl = idx.get("lastCrawlTime", "N/A")
        page_fetch = idx.get("pageFetchState", "N/A")
        referring = idx.get("referringUrls", [])

        result = f"## URL Inspection: {page_url}\n\n"
        result += f"| Property | Value |\n|---|---|\n"
        result += f"| Verdict | {verdict} |\n"
        result += f"| Indexing State | {indexing} |\n"
        result += f"| Page Fetch | {page_fetch} |\n"
        result += f"| Crawled As | {crawl} |\n"
        result += f"| Robots.txt | {robot} |\n"
        result += f"| Last Crawl | {last_crawl} |\n"

        if referring:
            result += f"\n**Referring URLs:**\n"
            for url in referring[:5]:
                result += f"- {url}\n"

        # Rich results
        rich = r.get("richResultsResult", {})
        if rich:
            detected = rich.get("detectedItems", [])
            if detected:
                result += f"\n**Rich Results:**\n"
                for item in detected:
                    result += f"- {item.get('richResultType', 'Unknown')}\n"

        # Mobile usability
        mobile = r.get("mobileUsabilityResult", {})
        if mobile:
            result += f"\n**Mobile Usability:** {mobile.get('verdict', 'N/A')}\n"
            issues = mobile.get("issues", [])
            for issue in issues:
                result += f"  - {issue.get('issueType', 'Unknown')}: {issue.get('severity', '')}\n"

        return result
    except Exception as e:
        return f"Error inspecting URL: {str(e)}"


@mcp.tool()
def batch_url_inspection(site_url: str, urls: str) -> str:
    """Inspect multiple URLs for indexing status (max 10).

    Args:
        site_url: Site URL
        urls: Newline-separated list of URLs to inspect (max 10)
    """
    url_list = [u.strip() for u in urls.strip().split("\n") if u.strip()][:10]
    results = []
    for url in url_list:
        r = inspect_url_enhanced(site_url, url)
        results.append(r)
    return "\n---\n".join(results)


# ── Sitemaps ──


@mcp.tool()
def get_sitemaps(site_url: str) -> str:
    """List all sitemaps submitted for a site."""
    service = get_gsc_service()
    try:
        result_data = service.sitemaps().list(siteUrl=site_url).execute()
        sitemaps = result_data.get("sitemap", [])
        if not sitemaps:
            return f"No sitemaps found for {site_url}"

        result = f"## Sitemaps for {site_url}\n\n"
        result += "| Sitemap | Type | Submitted | Last Downloaded | URLs |\n"
        result += "|---|---|---|---|---|\n"
        for sm in sitemaps:
            result += (
                f"| {sm.get('path', 'N/A')}"
                f" | {sm.get('type', 'N/A')}"
                f" | {sm.get('lastSubmitted', 'N/A')}"
                f" | {sm.get('lastDownloaded', 'N/A')}"
                f" | {sm.get('contents', [{}])[0].get('submitted', 'N/A') if sm.get('contents') else 'N/A'} |\n"
            )
        return result
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
