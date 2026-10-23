#!/usr/bin/env python3
"""
Scrape Rust PRs from GitHub to build the human baseline dataset.

This mirrors `scrape_csharp_prs_from_github.py`: searches GitHub for merged
Rust PRs (especially type-related ones) using a curated keyword list and
outputs in the same shape as the existing AIDev human PR detail CSVs so the
downstream extractor and LLM classifier can consume it without changes.
"""

import pandas as pd
import requests
import time
import os
from typing import Optional, Dict, List
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

if not GITHUB_TOKEN:
    print("ERROR: No GITHUB_TOKEN found.")
    print("Set GITHUB_TOKEN in a .env file or export it before running.")
    print("Get a token: https://github.com/settings/tokens (scope: public_repo)")
    exit(1)
else:
    token_preview = (
        f"{GITHUB_TOKEN[:4]}...{GITHUB_TOKEN[-4:]}" if len(GITHUB_TOKEN) > 8 else "***"
    )
    print(f"GitHub token loaded: {token_preview}")


class GitHubRustPRScraper:
    """Scrape Rust PRs from GitHub with focus on type-related changes."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or GITHUB_TOKEN
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        })
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = None

    def check_rate_limit(self):
        try:
            response = self.session.get('https://api.github.com/rate_limit', timeout=10)

            if response.status_code == 401:
                print("\nERROR: GitHub token is invalid or expired.")
                exit(1)

            if response.status_code == 200:
                data = response.json()
                self.rate_limit_remaining = data['resources']['core']['remaining']
                self.rate_limit_reset = data['resources']['core']['reset']
                print(f"Token valid. Rate limit: {self.rate_limit_remaining} remaining")
                return self.rate_limit_remaining
            else:
                print(f"Unexpected response: {response.status_code}")
        except Exception as e:
            print(f"Error checking rate limit: {e}")
        return self.rate_limit_remaining

    def wait_for_rate_limit(self):
        if self.rate_limit_remaining < 10:
            if self.rate_limit_reset:
                wait_time = max(0, self.rate_limit_reset - time.time()) + 5
                print(f"\nRate limit low. Waiting {wait_time:.0f} seconds...")
                time.sleep(wait_time)
                self.check_rate_limit()

    def search_rust_prs(self,
                        query_keywords: List[str],
                        max_results: int = 100,
                        min_stars: int = 50) -> List[Dict]:
        print(f"\n{'='*80}")
        print(f"Searching for Rust PRs with keywords: {', '.join(query_keywords)}")
        print(f"{'='*80}\n")

        all_prs = []
        seen_pr_urls = set()

        for keyword in query_keywords:
            print(f"\nSearching for: '{keyword}'")
            query = f"{keyword} language:rust type:pr is:merged stars:>{min_stars}"

            page = 1
            prs_for_keyword = 0
            target_per_keyword = max(1, max_results // len(query_keywords))

            while prs_for_keyword < target_per_keyword and page <= 10:
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
                        print("\nAuthentication failed. Check GITHUB_TOKEN.")
                        exit(1)

                    if response.status_code == 403:
                        print("Rate limit hit. Waiting 60s...")
                        time.sleep(60)
                        continue

                    if response.status_code != 200:
                        print(f"Error: {response.status_code}")
                        break

                    data = response.json()
                    items = data.get('items', [])
                    if not items:
                        print(f"   No more results for '{keyword}'")
                        break

                    print(f"   Page {page}: Found {len(items)} PRs")

                    for item in items:
                        pr_url = item.get('html_url', '')
                        if pr_url in seen_pr_urls:
                            continue
                        seen_pr_urls.add(pr_url)

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
                            'search_keyword': keyword,
                        }
                        all_prs.append(pr_info)
                        prs_for_keyword += 1

                    page += 1
                    time.sleep(1)

                except Exception as e:
                    print(f"Error searching: {e}")
                    break

            print(f"   Collected {prs_for_keyword} PRs for '{keyword}'")

        print(f"\nTotal unique PRs found: {len(all_prs)}")
        return all_prs

    def fetch_pr_details(self, pr_info: Dict) -> Optional[Dict]:
        self.wait_for_rate_limit()

        try:
            html_url = pr_info['html_url']
            parts = html_url.replace('https://github.com/', '').split('/')
            owner = parts[0]
            repo = parts[1]
            pr_number = pr_info['number']

            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            response = self.session.get(url, timeout=30)
            self.rate_limit_remaining -= 1

            if response.status_code == 403:
                print(f"Rate limit hit for PR #{pr_number}, waiting 60s...")
                time.sleep(60)
                return None

            if response.status_code != 200:
                return None

            pr_data = response.json()

            patch_url = pr_data.get('patch_url')
            patch_text = ''
            if patch_url:
                time.sleep(0.5)
                patch_response = self.session.get(patch_url, timeout=30)
                if patch_response.status_code == 200:
                    patch_text = patch_response.text

            return {
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
                'merged_by': (
                    pr_data.get('merged_by', {}).get('login', '')
                    if pr_data.get('merged_by') else ''
                ),
                'patch_text': patch_text,
                'search_keyword': pr_info.get('search_keyword', ''),
            }

        except Exception as e:
            print(f"Error fetching PR details: {e}")
            return None

    def scrape_rust_prs(self,
                        max_prs: int = 500,
                        output_file: str = 'scraped_rust_prs.csv',
                        resume: bool = True) -> pd.DataFrame:
        print("=" * 80)
        print("Rust PR Scraper - GitHub Search")
        print("=" * 80)

        self.check_rate_limit()

        existing_df = pd.DataFrame()
        if resume and os.path.exists(output_file):
            print(f"\nFound existing file: {output_file}")
            existing_df = pd.read_csv(output_file)
            print(f"Loaded {len(existing_df)} existing PRs")

        # Rust-specific type-related search keywords
        type_keywords = [
            'unsafe rust',
            'lifetime annotation',
            'trait bound',
            'type alias',
            'generic constraint',
            'pattern matching',
            'borrow checker',
            'type safety rust',
            'impl trait',
            'derive macro',
            'ownership rust',
            'type system rust',
        ]

        pr_list = self.search_rust_prs(
            query_keywords=type_keywords,
            max_results=max_prs * 2,
            min_stars=50,
        )

        if not existing_df.empty:
            existing_urls = set(existing_df['html_url'].tolist())
            pr_list = [pr for pr in pr_list if pr['html_url'] not in existing_urls]
            print(f"\nAfter dedup: {len(pr_list)} new PRs to fetch")

        print(f"\nFetching detailed information for {len(pr_list)} PRs...")
        detailed_prs = []

        for i, pr_info in enumerate(tqdm(pr_list[:max_prs], desc="Fetching PR details")):
            details = self.fetch_pr_details(pr_info)
            if details:
                detailed_prs.append(details)

                if (i + 1) % 10 == 0:
                    temp_df = pd.DataFrame(detailed_prs)
                    if not existing_df.empty:
                        combined_df = pd.concat([existing_df, temp_df], ignore_index=True)
                    else:
                        combined_df = temp_df
                    combined_df.to_csv(output_file, index=False)
                    print(f"\nProgress saved: {len(combined_df)} total PRs")

            time.sleep(1)

        if detailed_prs:
            new_df = pd.DataFrame(detailed_prs)
            if not existing_df.empty:
                final_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                final_df = new_df

            final_df = final_df.drop_duplicates(subset=['html_url'], keep='first')
            final_df.to_csv(output_file, index=False)

            print(f"\n{'='*80}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*80}")
            print(f"Total PRs collected: {len(final_df)}")
            print(f"New PRs added: {len(new_df)}")
            print(f"Output file: {output_file}")
            return final_df

        print("\nNo new PRs fetched")
        return existing_df if not existing_df.empty else pd.DataFrame()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Scrape Rust PRs from GitHub')
    parser.add_argument('--max-prs', type=int, default=500,
                        help='Maximum number of PRs to collect (default: 500)')
    parser.add_argument('--output', default='datasets/rust_data/scraped_rust_prs.csv',
                        help='Output CSV file')
    parser.add_argument('--no-resume', action='store_true',
                        help='Start fresh, ignore existing file')

    args = parser.parse_args()

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    scraper = GitHubRustPRScraper()
    scraper.scrape_rust_prs(
        max_prs=args.max_prs,
        output_file=args.output,
        resume=not args.no_resume
    )

    print("\nNext steps:")
    print("1. python extract_human_rust_type_prs.py "
          f"--input {args.output} "
          "--output datasets/rust_data/human_rust_prs_for_llm.csv")
    print("2. python llm_type_classifier_rust.py "
          "--input datasets/rust_data/human_rust_prs_for_llm.csv "
          "--output datasets/rust_data/human_rust_classified_type_prs.csv")


if __name__ == '__main__':
    main()
