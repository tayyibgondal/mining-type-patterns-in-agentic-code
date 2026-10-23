#!/usr/bin/env python3
"""Extract detailed information from human PR dataset."""

import pandas as pd
import requests
import re
import time
import json
from tqdm import tqdm
from typing import Optional, Dict, Any, Set
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', None)

def parse_pr_url(pr_url: str) -> Optional[Dict[str, str]]:
    """Parse GitHub PR URL to extract owner, repo, and PR number."""
    pattern = r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
    match = re.match(pattern, pr_url)
    if match:
        return {
            'owner': match.group(1),
            'repo': match.group(2),
            'pr_number': match.group(3)
        }
    return None

def fetch_pr_details(owner: str, repo: str, pr_number: str) -> Optional[Dict[str, Any]]:
    """Fetch PR details from GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 403 and 'rate limit' in response.text.lower():
            print(f"\nRate limit exceeded. Waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'title': data.get('title', ''),
                'description': data.get('body', ''),
                'state': data.get('state', ''),
                'created_at': data.get('created_at', ''),
                'closed_at': data.get('closed_at', ''),
                'merged_at': data.get('merged_at', ''),
                'patch_url': data.get('patch_url', '')
            }
        else:
            print(f"\nError fetching PR {owner}/{repo}#{pr_number}: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"\nException fetching PR {owner}/{repo}#{pr_number}: {str(e)}")
        return None

def fetch_pr_patch(patch_url: str) -> Optional[str]:
    """Fetch the git diff (patch) from the patch URL."""
    headers = {}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    
    try:
        response = requests.get(patch_url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            return None
    except Exception as e:
        print(f"\nException fetching patch: {str(e)}")
        return None

def load_progress(progress_file: str) -> Dict[str, Any]:
    """Load progress from JSON file."""
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading progress file: {e}")
            return {'processed_indices': [], 'last_updated': None}
    return {'processed_indices': [], 'last_updated': None}

def save_progress(progress_file: str, processed_indices: Set[int]):
    """Save progress to JSON file."""
    progress_data = {
        'processed_indices': sorted(list(processed_indices)),
        'last_updated': datetime.now().isoformat(),
        'total_processed': len(processed_indices)
    }
    try:
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    except Exception as e:
        print(f"Error saving progress file: {e}")

def process_human_pr_dataset():
    """Process the human PR dataset and extract additional information."""
    output_file = "human_pr_detailed_info.csv"
    progress_file = "extraction_progress.json"
    
    print("Loading human_pr_df dataset...")
    human_pr_df = pd.read_parquet("hf://datasets/hao-li/AIDev/human_pull_request.parquet")
    
    print(f"\nDataset loaded with {len(human_pr_df)} rows")
    print("\nExisting columns:")
    print(human_pr_df.columns.tolist())
    print("\nSample data:")
    print(human_pr_df.head())
    
    progress = load_progress(progress_file)
    processed_indices = set(progress['processed_indices'])
    
    if os.path.exists(output_file):
        print(f"\nFound existing output file: {output_file}")
        result_df = pd.read_csv(output_file)
        print(f"Loaded {len(result_df)} previously processed rows")
    else:
        print("\nCreating new output file")
        result_df = human_pr_df.copy()
        result_df['pr_title'] = ''
        result_df['pr_description'] = ''
        result_df['pr_state'] = ''
        result_df['pr_created_at'] = ''
        result_df['pr_closed_at'] = ''
        result_df['pr_merged_at'] = ''
        result_df['patch_text'] = ''
    
    all_indices = set(range(len(human_pr_df)))
    remaining_indices = sorted(all_indices - processed_indices)
    
    if not remaining_indices:
        print("\n✓ All PRs have been processed!")
        return result_df
    
    print(f"\n{'='*60}")
    print(f"Progress Summary:")
    print(f"  Total PRs: {len(human_pr_df)}")
    print(f"  Already processed: {len(processed_indices)}")
    print(f"  Remaining: {len(remaining_indices)}")
    if progress['last_updated']:
        print(f"  Last updated: {progress['last_updated']}")
    print(f"{'='*60}\n")
    
    for idx in tqdm(remaining_indices, desc="Extracting PR details"):
        row = human_pr_df.iloc[idx]
        
        pr_url = None
        for col in ['html_url', 'url', 'pr_url', 'link', 'pr_link']:
            if col in row.index and pd.notna(row[col]):
                pr_url = row[col]
                break
        
        if not pr_url:
            print(f"\nWarning: No PR URL found at index {idx}")
            processed_indices.add(idx)
            save_progress(progress_file, processed_indices)
            continue
        
        pr_info = parse_pr_url(pr_url)
        if not pr_info:
            print(f"\nWarning: Could not parse PR URL: {pr_url}")
            processed_indices.add(idx)
            save_progress(progress_file, processed_indices)
            continue
        
        pr_details = fetch_pr_details(pr_info['owner'], pr_info['repo'], pr_info['pr_number'])
        
        if pr_details:
            result_df.at[idx, 'pr_title'] = pr_details['title']
            result_df.at[idx, 'pr_description'] = pr_details['description'] or ''
            result_df.at[idx, 'pr_state'] = pr_details['state']
            result_df.at[idx, 'pr_created_at'] = pr_details['created_at']
            result_df.at[idx, 'pr_closed_at'] = pr_details['closed_at'] or ''
            result_df.at[idx, 'pr_merged_at'] = pr_details['merged_at'] or ''
            
            if pr_details['patch_url']:
                patch_text = fetch_pr_patch(pr_details['patch_url'])
                if patch_text:
                    result_df.at[idx, 'patch_text'] = patch_text
        
        processed_indices.add(idx)
        result_df.to_csv(output_file, index=False)
        save_progress(progress_file, processed_indices)
        time.sleep(0.1)
    
    print(f"\n{'='*60}")
    print("Extraction complete!")
    print(f"{'='*60}")
    print(f"\nTotal PRs processed: {len(processed_indices)}")
    print(f"Output saved to: {output_file}")
    print(f"Progress saved to: {progress_file}")
    print("\nSample of extracted data:")
    cols_to_show = ['pr_title', 'pr_state', 'pr_created_at']
    available_cols = [c for c in cols_to_show if c in result_df.columns]
    if available_cols:
        print(result_df[available_cols].head())
    
    return result_df

if __name__ == "__main__":
    print("="*60)
    print("Human PR Dataset - Detailed Information Extraction")
    print("="*60)
    
    if not os.environ.get('GITHUB_TOKEN'):
        print("\nWARNING: No GITHUB_TOKEN environment variable found.")
        print("You may hit rate limits quickly (60 requests/hour vs 5000/hour with token)")
        print("Set it with: export GITHUB_TOKEN='your_token_here'\n")
    else:
        print(f"\n✓ GitHub token loaded successfully")
    
    df = process_human_pr_dataset()
    
    print("\n✓ Script completed successfully!")

