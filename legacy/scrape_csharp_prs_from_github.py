#!/usr/bin/env python3
"""
Scrape C# PRs from GitHub to augment human baseline dataset.

This script searches GitHub for merged C# PRs (especially type-related ones)
and outputs in the same format as the AIDev human PR dataset.
"""

import pandas as pd
import requests
import time
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

if not GITHUB_TOKEN:
    print("❌ ERROR: No GITHUB_TOKEN found!")
    print("\nPlease set your GitHub token in one of these ways:")
    print("1. Create a .env file with: GITHUB_TOKEN=your_token_here")
    print("2. Export it: export GITHUB_TOKEN='your_token_here'")
    print("\nGet a token from: https://github.com/settings/tokens")
    exit(1)
else:
    # Show first/last 4 chars for verification
    token_preview = f"{GITHUB_TOKEN[:4]}...{GITHUB_TOKEN[-4:]}" if len(GITHUB_TOKEN) > 8 else "***"
    print(f"✓ GitHub token loaded: {token_preview}")


class GitHubCSharpPRScraper:
    """Scrape C# PRs from GitHub with focus on type-related changes."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or GITHUB_TOKEN
        self.session = requests.Session()
        if self.token:
            self.session.headers.update({
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            })
        else:
            self.session.headers.update({
                'Accept': 'application/vnd.github.v3+json'
            })
        
        self.rate_limit_remaining = 5000 if self.token else 60
        self.rate_limit_reset = None
    
    def check_rate_limit(self):
        """Check GitHub API rate limit."""
        try:
            response = self.session.get('https://api.github.com/rate_limit', timeout=10)
            
            if response.status_code == 401:
                print("\n❌ ERROR: GitHub token is invalid!")
                print("\nYour token is not authorized. Please check:")
                print("1. Token is correct (no extra spaces)")
                print("2. Token hasn't expired")
                print("3. Token has 'repo' and 'public_repo' scopes")
                print("\nGet a new token: https://github.com/settings/tokens")
                print("Required scopes: 'repo' (or at least 'public_repo')")
                exit(1)
            
            if response.status_code == 200:
                data = response.json()
                self.rate_limit_remaining = data['resources']['core']['remaining']
                self.rate_limit_reset = data['resources']['core']['reset']
                print(f"✓ Token valid! Rate limit: {self.rate_limit_remaining} requests remaining")
                return self.rate_limit_remaining
            else:
                print(f"⚠️  Unexpected response: {response.status_code}")
        except Exception as e:
            print(f"❌ Error checking rate limit: {e}")
        return self.rate_limit_remaining
    
    def wait_for_rate_limit(self):
        """Wait if rate limit is exhausted."""
        if self.rate_limit_remaining < 10:
            if self.rate_limit_reset:
                wait_time = max(0, self.rate_limit_reset - time.time()) + 5
                print(f"\n⏰ Rate limit low. Waiting {wait_time:.0f} seconds...")
                time.sleep(wait_time)
                self.check_rate_limit()
    
    def search_csharp_prs(self, 
                          query_keywords: List[str],
                          max_results: int = 100,
                          min_stars: int = 100) -> List[Dict]:
        """
        Search for C# PRs on GitHub.
        
        Args:
            query_keywords: Keywords to search for (type-related terms)
            max_results: Maximum number of PRs to fetch
            min_stars: Minimum stars for repositories
        """
        print(f"\n{'='*80}")
        print(f"Searching for C# PRs with keywords: {', '.join(query_keywords)}")
        print(f"{'='*80}\n")
        
        all_prs = []
        seen_pr_urls = set()
        
        for keyword in query_keywords:
            print(f"\n🔍 Searching for: '{keyword}'")
            
            # Search query for merged C# PRs
            query = f"{keyword} language:csharp type:pr is:merged stars:>{min_stars}"
            
            page = 1
            prs_for_keyword = 0
            
            while prs_for_keyword < (max_results // len(query_keywords)) and page <= 10:
                self.wait_for_rate_limit()
                
                try:
                    url = 'https://api.github.com/search/issues'
                    params = {
                        'q': query,
                        'sort': 'created',
                        'order': 'desc',
                        'per_page': 30,
                        'page': page
                    }
                    
                    response = self.session.get(url, params=params, timeout=30)
                    self.rate_limit_remaining -= 1
                    
                    if response.status_code == 401:
                        print("\n❌ ERROR: Authentication failed!")
                        print("Your GitHub token is invalid or expired.")
                        print("\nPlease check your .env file or GITHUB_TOKEN environment variable.")
                        print("Get a new token: https://github.com/settings/tokens")
                        exit(1)
                    
                    if response.status_code == 403:
                        print("⚠️  Rate limit hit. Waiting...")
                        time.sleep(60)
                        continue
                    
                    if response.status_code != 200:
                        print(f"❌ Error: {response.status_code}")
                        if response.status_code == 422:
                            print("   Search query may be invalid")
                        break
                    
                    data = response.json()
                    items = data.get('items', [])
                    
                    if not items:
                        print(f"   No more results for '{keyword}'")
                        break
                    
                    print(f"   Page {page}: Found {len(items)} PRs")
                    
                    for item in items:
                        pr_url = item.get('html_url', '')
                        
                        # Skip duplicates
                        if pr_url in seen_pr_urls:
                            continue
                        
                        seen_pr_urls.add(pr_url)
                        
                        # Basic PR info
                        pr_info = {
                            'number': item.get('number'),
                            'title': item.get('title', ''),
                            'html_url': pr_url,
                            'state': item.get('state', ''),
                            'created_at': item.get('created_at', ''),
                            'closed_at': item.get('closed_at', ''),
                            'user_login': item.get('user', {}).get('login', ''),
                            'repo_url': item.get('repository_url', ''),
                            'body': item.get('body', ''),
                            'search_keyword': keyword
                        }
                        
                        all_prs.append(pr_info)
                        prs_for_keyword += 1
                    
                    page += 1
                    time.sleep(1)  # Be nice to GitHub
                    
                except Exception as e:
                    print(f"❌ Error searching: {e}")
                    break
            
            print(f"   ✓ Collected {prs_for_keyword} PRs for '{keyword}'")
        
        print(f"\n{'='*80}")
        print(f"Total unique PRs found: {len(all_prs)}")
        print(f"{'='*80}\n")
        
        return all_prs
    
    def fetch_pr_details(self, pr_info: Dict) -> Optional[Dict]:
        """Fetch detailed PR information including patch."""
        self.wait_for_rate_limit()
        
        try:
            # Extract owner/repo from PR URL
            html_url = pr_info['html_url']
            parts = html_url.replace('https://github.com/', '').split('/')
            owner = parts[0]
            repo = parts[1]
            pr_number = pr_info['number']
            
            # Fetch PR details
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            response = self.session.get(url, timeout=30)
            self.rate_limit_remaining -= 1
            
            if response.status_code == 403:
                print(f"⚠️  Rate limit hit for PR #{pr_number}")
                time.sleep(60)
                return None
            
            if response.status_code != 200:
                return None
            
            pr_data = response.json()
            
            # Fetch patch
            patch_url = pr_data.get('patch_url')
            patch_text = ''
            
            if patch_url:
                time.sleep(0.5)
                patch_response = self.session.get(patch_url, timeout=30)
                if patch_response.status_code == 200:
                    patch_text = patch_response.text
            
            # Format in same structure as human_pr_data.csv
            detailed_info = {
                'id': pr_data.get('id'),
                'number': pr_data.get('number'),
                'title': pr_data.get('title', ''),
                'body': pr_data.get('body', ''),
                'state': pr_data.get('state', ''),
                'created_at': pr_data.get('created_at', ''),
                'closed_at': pr_data.get('closed_at', ''),
                'merged_at': pr_data.get('merged_at', ''),
                'html_url': pr_data.get('html_url', ''),
                'repo_url': f"https://github.com/{owner}/{repo}",
                'additions': pr_data.get('additions', 0),
                'deletions': pr_data.get('deletions', 0),
                'changed_files': pr_data.get('changed_files', 0),
                'user_login': pr_data.get('user', {}).get('login', ''),
                'merged_by': pr_data.get('merged_by', {}).get('login', '') if pr_data.get('merged_by') else '',
                'patch_text': patch_text,
                'search_keyword': pr_info.get('search_keyword', ''),
            }
            
            return detailed_info
            
        except Exception as e:
            print(f"❌ Error fetching PR details: {e}")
            return None
    
    def scrape_csharp_prs(self, 
                          max_prs: int = 500,
                          output_file: str = 'scraped_csharp_prs.csv',
                          resume: bool = True) -> pd.DataFrame:
        """
        Main scraping function.
        
        Args:
            max_prs: Target number of PRs to collect
            output_file: Output CSV file
            resume: Resume from existing file if available
        """
        print("="*80)
        print("C# PR Scraper - GitHub Search")
        print("="*80)
        
        # Check rate limit
        self.check_rate_limit()
        
        # Load existing data if resuming
        existing_df = pd.DataFrame()
        if resume and os.path.exists(output_file):
            print(f"\n✓ Found existing file: {output_file}")
            existing_df = pd.read_csv(output_file)
            print(f"✓ Loaded {len(existing_df)} existing PRs")
        
        # Type-related search keywords
        type_keywords = [
            'nullable reference',
            'record type',
            'type annotation',
            'generic constraint',
            'pattern matching',
            'type safety',
            'interface implementation',
            'abstract class',
            'type parameter',
            'value type',
            'reference type',
            'type conversion',
        ]
        
        # Search for PRs
        pr_list = self.search_csharp_prs(
            query_keywords=type_keywords,
            max_results=max_prs * 2,  # Search for more to filter later
            min_stars=50  # Lower threshold to get more results
        )
        
        # Filter out PRs we already have
        if not existing_df.empty:
            existing_urls = set(existing_df['html_url'].tolist())
            pr_list = [pr for pr in pr_list if pr['html_url'] not in existing_urls]
            print(f"\n✓ After filtering duplicates: {len(pr_list)} new PRs to fetch")
        
        # Fetch detailed info for each PR
        print(f"\n{'='*80}")
        print(f"Fetching detailed information for {len(pr_list)} PRs...")
        print(f"{'='*80}\n")
        
        detailed_prs = []
        
        for i, pr_info in enumerate(tqdm(pr_list[:max_prs], desc="Fetching PR details")):
            details = self.fetch_pr_details(pr_info)
            
            if details:
                detailed_prs.append(details)
                
                # Save incrementally every 10 PRs
                if (i + 1) % 10 == 0:
                    temp_df = pd.DataFrame(detailed_prs)
                    if not existing_df.empty:
                        combined_df = pd.concat([existing_df, temp_df], ignore_index=True)
                    else:
                        combined_df = temp_df
                    
                    combined_df.to_csv(output_file, index=False)
                    print(f"\n💾 Progress saved: {len(combined_df)} total PRs")
            
            time.sleep(1)  # Be nice to GitHub
        
        # Final save
        if detailed_prs:
            new_df = pd.DataFrame(detailed_prs)
            
            if not existing_df.empty:
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                final_df = new_df
            
            # Remove duplicates
            final_df = final_df.drop_duplicates(subset=['html_url'], keep='first')
            
            final_df.to_csv(output_file, index=False)
            
            print(f"\n{'='*80}")
            print(f"✅ SCRAPING COMPLETE")
            print(f"{'='*80}")
            print(f"Total PRs collected: {len(final_df)}")
            print(f"New PRs added: {len(new_df)}")
            print(f"Output file: {output_file}")
            print(f"{'='*80}\n")
            
            # Show sample
            print("Sample PRs:")
            print(final_df[['number', 'title', 'repo_url', 'search_keyword']].head(10))
            
            return final_df
        else:
            print("\n⚠️  No new PRs fetched")
            return existing_df if not existing_df.empty else pd.DataFrame()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape C# PRs from GitHub')
    parser.add_argument('--max-prs', type=int, default=500,
                       help='Maximum number of PRs to collect (default: 500)')
    parser.add_argument('--output', default='scraped_csharp_prs.csv',
                       help='Output CSV file (default: scraped_csharp_prs.csv)')
    parser.add_argument('--no-resume', action='store_true',
                       help='Start fresh (ignore existing file)')
    
    args = parser.parse_args()
    
    scraper = GitHubCSharpPRScraper()
    results = scraper.scrape_csharp_prs(
        max_prs=args.max_prs,
        output_file=args.output,
        resume=not args.no_resume
    )
    
    print("\n✅ Scraping completed!")
    print(f"\nNext steps:")
    print(f"1. python extract_human_csharp_type_prs.py  # Extract type-related PRs")
    print(f"2. python llm_type_classifier_csharp.py     # LLM classification")


if __name__ == '__main__':
    main()

