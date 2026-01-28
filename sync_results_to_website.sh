#!/bin/bash
# Local script to manually sync benchmark results to website repository
# Usage: ./sync_results_to_website.sh [website_repo_path]

set -e

WEBSITE_REPO=${1:-"../sagellm-website"}
BENCHMARK_REPO=$(pwd)

echo "==================================="
echo "Benchmark Results → Website Sync"
echo "==================================="
echo "Benchmark repo: $BENCHMARK_REPO"
echo "Website repo:   $WEBSITE_REPO"
echo ""

# Check if website repo exists
if [ ! -d "$WEBSITE_REPO" ]; then
    echo "❌ Website repository not found at: $WEBSITE_REPO"
    echo "Usage: $0 [website_repo_path]"
    exit 1
fi

# Find all leaderboard files
echo "🔍 Finding leaderboard files..."
leaderboard_files=$(find outputs/ -name "*_leaderboard.json" -type f 2>/dev/null || true)

if [ -z "$leaderboard_files" ]; then
    echo "❌ No leaderboard files found in outputs/"
    exit 1
fi

file_count=$(echo "$leaderboard_files" | wc -l)
echo "✓ Found $file_count leaderboard files"
echo ""

# Create results directory in website
results_dir="$WEBSITE_REPO/data/results"
mkdir -p "$results_dir"
echo "✓ Created results directory: $results_dir"
echo ""

# Copy files
echo "📦 Copying files..."
copied_count=0

echo "$leaderboard_files" | while IFS= read -r file; do
    if [ -n "$file" ] && [ -f "$file" ]; then
        # Extract backend/model/run_id from path
        # outputs/cpu/gpt2/short_20260128_005/short_input_leaderboard.json
        backend=$(echo "$file" | cut -d'/' -f2)
        model=$(echo "$file" | cut -d'/' -f3)
        run_id=$(echo "$file" | cut -d'/' -f4)
        filename=$(basename "$file")
        
        # Create destination directory
        dest_dir="$results_dir/${backend}/${model}"
        mkdir -p "$dest_dir"
        
        # Copy file with run_id prefix
        dest_file="$dest_dir/${run_id}_${filename}"
        cp "$file" "$dest_file"
        
        echo "  ✓ $file"
        echo "    → $dest_file"
        
        copied_count=$((copied_count + 1))
    fi
done

# Get final count
copied_count=$(find "$results_dir" -name "*_leaderboard.json" -type f | wc -l)

echo ""
echo "==================================="
echo "✅ Sync completed!"
echo "==================================="
echo "Files copied: $copied_count"
echo "Destination:  $results_dir"
echo ""
echo "Next steps:"
echo "1. cd $WEBSITE_REPO"
echo "2. git status"
echo "3. git add data/results/"
echo "4. git commit -m 'chore: sync benchmark results'"
echo "5. git push"
