#!/bin/bash

sqlite3 new_results.db << SQLITE_EOF | while IFS='|' read -r id response_json
SELECT id, response_json FROM results;
SQLITE_EOF
do
    echo "Entry ID: $id"
    echo "$response_json" | jq '.' 2>/dev/null || echo "Invalid JSON: $response_json"
    echo "----------------------------------------"
done
