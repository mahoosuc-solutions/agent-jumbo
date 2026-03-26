from __future__ import annotations

SEED_TERRITORIES = [
    {
        "state": "MA",
        "metro_name": "Greater Boston",
        "cluster_name": "Boston Public + Health Core",
        "priority_tier": 1,
        "status": "planned",
        "coverage_thresholds": {
            "required_successful_collectors": 2,
            "max_discovered_backlog": 0,
        },
        "collector_bundle": [
            {
                "name": "boston-public-rfp-json",
                "adapter": "json_file",
                "config": {"path": "data/opportunity_feeds/boston-public-rfp.json"},
            },
            {
                "name": "boston-health-watch-csv",
                "adapter": "csv_file",
                "config": {
                    "path": "data/opportunity_feeds/boston-health-watch.csv",
                    "defaults": {"territory_id": 1, "source_type": "health_watch"},
                },
            },
        ],
        "zips": [
            {"zip_code": "02108", "city": "Boston", "state": "MA"},
            {"zip_code": "02109", "city": "Boston", "state": "MA"},
            {"zip_code": "02110", "city": "Boston", "state": "MA"},
            {"zip_code": "02111", "city": "Boston", "state": "MA"},
            {"zip_code": "02114", "city": "Boston", "state": "MA"},
            {"zip_code": "02115", "city": "Boston", "state": "MA"},
            {"zip_code": "02210", "city": "Boston", "state": "MA"},
        ],
    },
    {
        "state": "NY",
        "metro_name": "New York City",
        "cluster_name": "NYC Gov + Health Corridor",
        "priority_tier": 1,
        "status": "planned",
        "coverage_thresholds": {
            "required_successful_collectors": 2,
            "max_discovered_backlog": 0,
        },
        "collector_bundle": [
            {
                "name": "nyc-gov-rfp-json",
                "adapter": "json_file",
                "config": {"path": "data/opportunity_feeds/nyc-gov-rfp.json"},
            },
            {
                "name": "nyc-health-watch-jsonl",
                "adapter": "jsonl_file",
                "config": {"path": "data/opportunity_feeds/nyc-health-watch.jsonl"},
            },
        ],
        "zips": [
            {"zip_code": "10001", "city": "New York", "state": "NY"},
            {"zip_code": "10007", "city": "New York", "state": "NY"},
            {"zip_code": "10013", "city": "New York", "state": "NY"},
            {"zip_code": "10016", "city": "New York", "state": "NY"},
            {"zip_code": "10451", "city": "Bronx", "state": "NY"},
            {"zip_code": "11101", "city": "Long Island City", "state": "NY"},
            {"zip_code": "11201", "city": "Brooklyn", "state": "NY"},
        ],
    },
    {
        "state": "DC",
        "metro_name": "Washington",
        "cluster_name": "DC Federal + Public Health Beltway",
        "priority_tier": 1,
        "status": "planned",
        "coverage_thresholds": {
            "required_successful_collectors": 2,
            "max_discovered_backlog": 0,
        },
        "collector_bundle": [
            {
                "name": "dc-federal-rfp-json",
                "adapter": "json_file",
                "config": {"path": "data/opportunity_feeds/dc-federal-rfp.json"},
            },
            {
                "name": "dc-public-health-csv",
                "adapter": "csv_file",
                "config": {
                    "path": "data/opportunity_feeds/dc-public-health.csv",
                    "defaults": {"territory_id": 3, "source_type": "public_health_watch"},
                },
            },
        ],
        "zips": [
            {"zip_code": "20001", "city": "Washington", "state": "DC"},
            {"zip_code": "20002", "city": "Washington", "state": "DC"},
            {"zip_code": "20004", "city": "Washington", "state": "DC"},
            {"zip_code": "20005", "city": "Washington", "state": "DC"},
            {"zip_code": "20036", "city": "Washington", "state": "DC"},
            {"zip_code": "20814", "city": "Bethesda", "state": "MD"},
            {"zip_code": "22202", "city": "Arlington", "state": "VA"},
        ],
    },
    {
        "state": "IL",
        "metro_name": "Chicago",
        "cluster_name": "Chicago Civic + Health Services Core",
        "priority_tier": 2,
        "status": "planned",
        "coverage_thresholds": {
            "required_successful_collectors": 2,
            "max_discovered_backlog": 0,
        },
        "collector_bundle": [
            {
                "name": "chicago-civic-rfp-json",
                "adapter": "json_file",
                "config": {"path": "data/opportunity_feeds/chicago-civic-rfp.json"},
            },
            {
                "name": "chicago-health-watch-csv",
                "adapter": "csv_file",
                "config": {
                    "path": "data/opportunity_feeds/chicago-health-watch.csv",
                    "defaults": {"territory_id": 4, "source_type": "health_watch"},
                },
            },
        ],
        "zips": [
            {"zip_code": "60601", "city": "Chicago", "state": "IL"},
            {"zip_code": "60602", "city": "Chicago", "state": "IL"},
            {"zip_code": "60603", "city": "Chicago", "state": "IL"},
            {"zip_code": "60604", "city": "Chicago", "state": "IL"},
            {"zip_code": "60607", "city": "Chicago", "state": "IL"},
            {"zip_code": "60611", "city": "Chicago", "state": "IL"},
            {"zip_code": "60612", "city": "Chicago", "state": "IL"},
        ],
    },
]


def build_territory_profiles() -> dict[tuple[str, str, str], dict]:
    return {
        (territory["state"], territory["metro_name"], territory["cluster_name"]): territory
        for territory in SEED_TERRITORIES
    }


TERRITORY_PROFILES = build_territory_profiles()
