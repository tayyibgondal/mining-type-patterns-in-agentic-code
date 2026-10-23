"""
AI-Powered Type-Related PR Classification Pipeline (OpenAI GPT-4o-mini / Google Gemini)
FIXED VERSION with proper progress tracking and error handling

Major fixes:
1. Real-time progress with timestamps and detailed status
2. Batch processing to avoid memory explosion
3. Proper timeout handling
4. Better error reporting
5. Queue depth monitoring
6. Unbuffered output with sys.stderr
"""

import pandas as pd
import json
import os
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import asyncio
from asyncio import TimeoutError

# OpenAI imports
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Gemini imports
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Load environment variables
load_dotenv()


def log_progress(message: str, error: bool = False):
    """Log progress to stderr for unbuffered output"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = "❌" if error else "📊"
    # Use stderr for unbuffered output
    print(f"[{timestamp}] {prefix} {message}", file=sys.stderr, flush=True)
    # Also print to stdout for recording
    print(f"[{timestamp}] {prefix} {message}", flush=True)


class OpenAITypePRClassifier:
    """AI-powered TypeScript type-related PR classifier with validation (OpenAI/Gemini)"""
    
    def __init__(self, model: str = "gemini-1.5-flash", max_concurrent: int = 30, 
                 provider: str = "openai", timeout: int = 30, batch_size: int = 100):
        """
        Initialize the classifier with AI API
        
        Args:
            model: Model to use 
            max_concurrent: Maximum concurrent API calls
            provider: API provider - "openai" or "gemini"
            timeout: Timeout for each API call in seconds
            batch_size: Process PRs in batches to avoid memory issues
        """
        self.model = model
        self.max_concurrent = max_concurrent
        self.provider = provider.lower()
        self.timeout = timeout
        self.batch_size = batch_size
        
        log_progress(f"Initializing classifier: provider={provider}, model={model}, concurrent={max_concurrent}")
        
        # Initialize the appropriate client
        if self.provider == "openai":
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not found in environment variables.\n"
                    "Please create a .env file with: OPENAI_API_KEY=your_key_here"
                )
            self.client = AsyncOpenAI(api_key=api_key)
            log_progress("OpenAI client initialized")
            
        elif self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ValueError(
                    "Gemini support not available. Install with: pip install google-generativeai"
                )
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY not found in environment variables.\n"
                    "Please create a .env file with: GEMINI_API_KEY=your_key_here"
                )
            genai.configure(api_key=api_key)
            # Use latest fast model if default OpenAI model was specified
            if model == "gpt-4o-mini":
                self.model = "gemini-2.0-flash-exp"
            self.client = None
            log_progress(f"Gemini client initialized with model: {self.model}")
            
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'gemini'")
        
        # Semaphore for rate limiting
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Statistics
        self.total_api_calls = 0
        self.total_tokens_used = 0
        self.api_errors = 0
        self.successful_calls = 0
        self.classifications = []
        self.start_time = None
        self.tasks_queued = 0
        self.tasks_active = 0
        
    def safe_str_slice(self, value, max_length: int, default: str = '') -> str:
        """Safely slice a string, handling NaN and None values"""
        if pd.isna(value) or value is None:
            return default
        if not isinstance(value, str):
            return default
        return value[:max_length] if value else default
    
    def create_classifier_prompt(self, pr_data: Dict) -> str:
        """Create prompt for the classifier agent"""
        
        title = self.safe_str_slice(pr_data.get('title'), 500, 'No title')
        body = self.safe_str_slice(pr_data.get('body'), 1000, 'No description')
        commit_messages = self.safe_str_slice(pr_data.get('commit_messages'), 800, 'No commit messages')
        patch_text = self.safe_str_slice(pr_data.get('patch_text'), 2000, 'No patches available')
        
        prompt = f"""You are an expert TypeScript and software engineering analyst. Your task is to determine if a pull request is related to TypeScript type changes, fixes, or improvements.

Analyze the following PR data and determine if it's TYPE-RELATED:

**PR Title:**
{title}

**PR Description:**
{body}

**Commit Messages:**
{commit_messages}

**Code Changes (Patch Preview):**
{patch_text}

**Statistics:**
- Lines added: {pr_data.get('additions', 0)}
- Lines deleted: {pr_data.get('deletions', 0)}
- TypeScript files changed: {pr_data.get('ts_files_changed', 0)}

**Definition of TYPE-RELATED:**
A PR is type-related if it involves:
- Adding, modifying, or removing type annotations
- Fixing type errors or TypeScript compilation issues
- Converting from 'any' to specific types
- Refactoring types or interfaces
- Improving type safety or strictness
- Type-related configuration changes (tsconfig.json)
- Generic type improvements
- Type assertions or type guards

**Your Task:**
1. Carefully analyze all provided information
2. Look for type-related keywords, patterns, and actual type changes
3. Provide a clear YES or NO decision 
4. Explain your reasoning with specific evidence

**Response Format (JSON):**
{{
    "is_type_related": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation with specific evidence",
    "evidence": [
        "Evidence point 1",
        "Evidence point 2"
    ],
    "detected_in": {{
        "title": true/false,
        "body": true/false,
        "commits": true/false,
        "patches": true/false
    }}
}}

Be thorough and accurate. Only classify as type-related if there's clear evidence."""

        return prompt
    
    def create_validator_prompt(self, pr_data: Dict, classification: Dict) -> str:
        """Create prompt for the validator agent"""
        
        title = self.safe_str_slice(pr_data.get('title'), 200, 'No title')
        body = self.safe_str_slice(pr_data.get('body'), 500, 'No description')
        reasoning = self.safe_str_slice(classification.get('reasoning'), 500, 'No reasoning provided')
        
        prompt = f"""You are a senior code reviewer validating type-related PR classifications. 

Review this classification decision:

**Original PR Data:**
- Title: {title}
- Description: {body}
- Files changed: {pr_data.get('ts_files_changed', 0)} TypeScript files
- Lines: +{pr_data.get('additions', 0)}/-{pr_data.get('deletions', 0)}

**Classifier Decision:**
- Classification: {"TYPE-RELATED" if classification.get('is_type_related') else "NOT TYPE-RELATED"}
- Confidence: {classification.get('confidence', 0):.2f}
- Reasoning: {reasoning}

**Your Task:**
Validate this classification decision. Consider:
1. Does the reasoning match the evidence?
2. Are there false positives (classified as type-related but isn't)?
3. Are there false negatives (not classified but should be)?
4. Is the confidence level appropriate?

**Response Format (JSON):**
{{
    "validation_result": "APPROVED" / "REJECTED" / "UNCERTAIN",
    "agreed_classification": true/false,
    "validator_confidence": 0.0-1.0,
    "validator_reasoning": "Detailed validation reasoning",
    "suggested_changes": "Any corrections or clarifications"
}}

Be critical and thorough in your validation."""

        return prompt
    
    async def call_api_with_timeout(self, prompt: str, temperature: float = 0.1) -> Tuple[Dict, int]:
        """Call API with timeout protection"""
        try:
            return await asyncio.wait_for(
                self.call_api(prompt, temperature),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            self.api_errors += 1
            log_progress(f"API call timed out after {self.timeout}s", error=True)
            return {
                "is_type_related": False,
                "confidence": 0.0,
                "reasoning": f"Timeout after {self.timeout} seconds",
                "evidence": [],
                "detected_in": {"title": False, "body": False, "commits": False, "patches": False}
            }, 0
    
    async def call_api(self, prompt: str, temperature: float = 0.1) -> Tuple[Dict, int]:
        """
        Call AI API (OpenAI or Gemini) with the given prompt (async with rate limiting)
        """
        # Track queue depth
        self.tasks_queued += 1
        
        async with self.semaphore:  # Limit concurrent requests
            self.tasks_queued -= 1
            self.tasks_active += 1
            
            try:
                if self.provider == "openai":
                    result = await self._call_openai(prompt, temperature)
                elif self.provider == "gemini":
                    result = await self._call_gemini(prompt, temperature)
                
                self.successful_calls += 1
                return result
                    
            except Exception as e:
                self.api_errors += 1
                error_msg = str(e)[:200]  # Truncate long errors
                log_progress(f"API Error: {error_msg}", error=True)
                
                # Return error result instead of silently failing
                return {
                    "is_type_related": False,
                    "confidence": 0.0,
                    "reasoning": f"API Error: {error_msg}",
                    "evidence": [],
                    "detected_in": {"title": False, "body": False, "commits": False, "patches": False},
                    "error": True
                }, 0
            finally:
                self.tasks_active -= 1
    
    async def _call_openai(self, prompt: str, temperature: float) -> Tuple[Dict, int]:
        """Call OpenAI API"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a precise TypeScript and software engineering expert. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        
        self.total_api_calls += 1
        tokens_used = response.usage.total_tokens
        self.total_tokens_used += tokens_used
        
        result = json.loads(response.choices[0].message.content)
        return result, tokens_used
    
    async def _call_gemini(self, prompt: str, temperature: float) -> Tuple[Dict, int]:
        """Call Gemini API with better async handling"""
        loop = asyncio.get_event_loop()
        
        def _sync_call():
            model = genai.GenerativeModel(
                self.model,
                generation_config={
                    "temperature": temperature,
                    "response_mime_type": "application/json"
                }
            )
            
            full_prompt = f"""You are a precise TypeScript and software engineering expert. Always respond with valid JSON.

{prompt}

Respond ONLY with valid JSON matching the requested format."""
            
            response = model.generate_content(full_prompt)
            return response.text
        
        # Use ThreadPoolExecutor with timeout
        response_text = await loop.run_in_executor(None, _sync_call)
        
        self.total_api_calls += 1
        tokens_used = len(response_text) // 4  # Rough estimate
        self.total_tokens_used += tokens_used
        
        result = json.loads(response_text)
        return result, tokens_used
    
    async def classify_pr(self, pr_row: pd.Series, pr_index: int, total: int) -> Dict:
        """
        Classify a single PR using the two-agent system (async)
        """
        start_time = time.time()
        
        # Log start
        pr_number = pr_row.get('number', 'Unknown')
        log_progress(f"[{pr_index}/{total}] Starting PR #{pr_number}")
        
        # Prepare PR data
        def safe_get(key, default=''):
            val = pr_row.get(key, default)
            return default if pd.isna(val) else val
        
        pr_data = {
            'id': pr_row.get('id'),
            'number': pr_row.get('number'),
            'title': safe_get('title', ''),
            'body': safe_get('body', ''),
            'commit_messages': self.get_commit_messages(pr_row.get('id')),
            'patch_text': safe_get('patch_text', ''),
            'additions': safe_get('additions', 0),
            'deletions': safe_get('deletions', 0),
            'ts_files_changed': safe_get('ts_files_changed', 0),
        }
        
        # Step 1: Classifier Agent
        classifier_prompt = self.create_classifier_prompt(pr_data)
        classification, classifier_tokens = await self.call_api_with_timeout(classifier_prompt, temperature=0.1)
        
        # Check for error
        if classification.get('error'):
            log_progress(f"[{pr_index}/{total}] PR #{pr_number} - Classifier failed", error=True)
            return self._create_error_result(pr_row, "Classifier API error")
        
        # Step 2: Validator Agent
        validator_prompt = self.create_validator_prompt(pr_data, classification)
        validation, validator_tokens = await self.call_api_with_timeout(validator_prompt, temperature=0.1)
        
        # Check for error
        if validation.get('error'):
            log_progress(f"[{pr_index}/{total}] PR #{pr_number} - Validator failed", error=True)
            # Still return classifier result even if validator fails
        
        elapsed = time.time() - start_time
        
        # Log completion with details
        is_type = classification.get('is_type_related', False) and validation.get('validation_result') == 'APPROVED'
        log_progress(
            f"[{pr_index}/{total}] PR #{pr_number} completed in {elapsed:.1f}s - "
            f"Type: {is_type} | Conf: {classification.get('confidence', 0):.2f} | "
            f"Queue: {self.tasks_queued} | Active: {self.tasks_active}"
        )
        
        # Combine results
        result = {
            'pr_id': pr_row.get('id'),
            'pr_number': pr_row.get('number'),
            
            # Classifier results
            'classifier_is_type_related': classification.get('is_type_related', False),
            'classifier_confidence': classification.get('confidence', 0.0),
            'classifier_reasoning': classification.get('reasoning', ''),
            'classifier_evidence': json.dumps(classification.get('evidence', [])),
            
            # Detection flags from classifier
            'detected_in_title': classification.get('detected_in', {}).get('title', False),
            'detected_in_body': classification.get('detected_in', {}).get('body', False),
            'detected_in_commits': classification.get('detected_in', {}).get('commits', False),
            'detected_in_patches': classification.get('detected_in', {}).get('patches', False),
            
            # Validator results
            'validation_result': validation.get('validation_result', 'UNCERTAIN'),
            'validator_agreed': validation.get('agreed_classification', False),
            'validator_confidence': validation.get('validator_confidence', 0.0),
            'validator_reasoning': validation.get('validator_reasoning', ''),
            
            # Final decision
            'final_is_type_related': is_type,
            
            # Metadata
            'tokens_used': classifier_tokens + validator_tokens,
            'processing_time_seconds': elapsed,
        }
        
        return result
    
    def _create_error_result(self, pr_row: pd.Series, error_msg: str) -> Dict:
        """Create an error result for failed classifications"""
        return {
            'pr_id': pr_row.get('id'),
            'pr_number': pr_row.get('number'),
            'classifier_is_type_related': False,
            'classifier_confidence': 0.0,
            'classifier_reasoning': error_msg,
            'classifier_evidence': json.dumps([]),
            'detected_in_title': False,
            'detected_in_body': False,
            'detected_in_commits': False,
            'detected_in_patches': False,
            'validation_result': 'ERROR',
            'validator_agreed': False,
            'validator_confidence': 0.0,
            'validator_reasoning': error_msg,
            'final_is_type_related': False,
            'tokens_used': 0,
            'processing_time_seconds': 0,
            'error': True
        }
    
    def get_commit_messages(self, pr_id: int) -> str:
        """Get commit messages for a PR (if available)"""
        try:
            if hasattr(self, 'pr_commits_df'):
                commits = self.pr_commits_df[self.pr_commits_df['pr_id'] == pr_id]
                messages = commits['message'].tolist()
                return '\n'.join(messages[:5])  # Limit to first 5 commits
        except:
            pass
        return "No commit messages available"
    
    def load_pr_data(self, csv_file: str):
        """Load PR data from CSV"""
        log_progress(f"Loading PR data from {csv_file}...")
        self.pr_df = pd.read_csv(csv_file)
        log_progress(f"Loaded {len(self.pr_df):,} PRs")
        
        # Try to load commit data
        try:
            log_progress("Loading commit data...")
            self.pr_commits_df = pd.read_parquet('hf://datasets/hao-li/AIDev/pr_commits.parquet')
            log_progress(f"Loaded commit data ({len(self.pr_commits_df):,} commits)")
        except Exception as e:
            log_progress(f"Could not load commit data: {e}", error=True)
            self.pr_commits_df = None
    
    async def process_batch(self, batch_df: pd.DataFrame, batch_num: int, 
                          total_batches: int, start_index: int) -> List[Dict]:
        """Process a batch of PRs"""
        batch_size = len(batch_df)
        log_progress(f"Starting batch {batch_num}/{total_batches} ({batch_size} PRs)")
        
        # Create tasks for this batch
        tasks = []
        for i, (_, row) in enumerate(batch_df.iterrows()):
            pr_index = start_index + i + 1
            total_prs = start_index + batch_size
            task = self.classify_pr(row, pr_index, len(self.pr_df))
            tasks.append(task)
        
        # Process batch with proper error handling
        results = []
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                log_progress(f"Batch {batch_num} - Task error: {e}", error=True)
                traceback.print_exc()
        
        log_progress(f"Completed batch {batch_num}/{total_batches} - {len(results)} successful")
        return results
    
    async def classify_all_prs_async(self, 
                                    limit: Optional[int] = None,
                                    output_file: str = 'openai_classified_type_prs.csv') -> pd.DataFrame:
        """
        Classify all PRs with improved progress tracking and batch processing
        """
        self.start_time = time.time()
        
        log_progress("="*80)
        log_progress(f"Starting {self.provider.upper()} Type-Related PR Classification")
        log_progress(f"Model: {self.model} | Concurrent: {self.max_concurrent} | Timeout: {self.timeout}s")
        log_progress("="*80)
        
        # Select PRs to classify
        prs_to_classify = self.pr_df.head(limit) if limit else self.pr_df
        total_prs = len(prs_to_classify)
        
        log_progress(f"Processing {total_prs:,} PRs in batches of {self.batch_size}")
        
        # Process in batches to avoid memory explosion
        all_results = []
        num_batches = (total_prs + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(num_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, total_prs)
            batch_df = prs_to_classify.iloc[start_idx:end_idx]
            
            # Process batch
            batch_results = await self.process_batch(
                batch_df, 
                batch_num + 1, 
                num_batches,
                start_idx
            )
            all_results.extend(batch_results)
            
            # Show statistics after each batch
            elapsed = time.time() - self.start_time
            rate = len(all_results) / elapsed if elapsed > 0 else 0
            type_related = sum(1 for r in all_results if r.get('final_is_type_related'))
            error_count = sum(1 for r in all_results if r.get('error'))
            
            log_progress(
                f"Progress: {len(all_results)}/{total_prs} ({100*len(all_results)/total_prs:.1f}%) | "
                f"Type: {type_related} | Errors: {error_count} | "
                f"Rate: {rate:.1f} PR/s | Time: {elapsed:.1f}s"
            )
            log_progress(
                f"API Stats: Calls={self.total_api_calls} | Success={self.successful_calls} | "
                f"Errors={self.api_errors} | Tokens={self.total_tokens_used:,}"
            )
        
        # Final statistics
        elapsed = time.time() - self.start_time
        log_progress("="*80)
        log_progress(f"COMPLETED in {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        log_progress(f"Success rate: {self.successful_calls}/{self.total_api_calls} ({100*self.successful_calls/max(1,self.total_api_calls):.1f}%)")
        log_progress("="*80)
        
        # Create results DataFrame
        results_df = pd.DataFrame(all_results)
        
        # Merge with original PR data
        merged_df = self.pr_df.merge(
            results_df,
            left_on='id',
            right_on='pr_id',
            how='left'
        )
        
        # Export results
        self.export_results(merged_df, output_file)
        
        return merged_df
    
    def classify_all_prs(self, 
                        limit: Optional[int] = None,
                        output_file: str = 'openai_classified_type_prs.csv') -> pd.DataFrame:
        """
        Classify all PRs using OpenAI agents (wrapper for async function)
        """
        return asyncio.run(self.classify_all_prs_async(limit, output_file))
    
    def export_results(self, df: pd.DataFrame, output_file: str):
        """Export classification results"""
        log_progress(f"Exporting results to {output_file}...")
        
        # Select columns for export
        export_columns = [
            # Original PR data
            'id', 'number', 'title', 'body', 'agent', 'state',
            'created_at', 'closed_at', 'merged_at',
            'repo_id', 'repo_url', 'html_url',
            'additions', 'deletions', 'changes', 'ts_files_changed',
            'patch_text',
            
            # Classification results
            'classifier_is_type_related',
            'classifier_confidence',
            'classifier_reasoning',
            'classifier_evidence',
            'detected_in_title',
            'detected_in_body',
            'detected_in_commits',
            'detected_in_patches',
            
            # Validation results
            'validation_result',
            'validator_agreed',
            'validator_confidence',
            'validator_reasoning',
            
            # Final decision and metadata
            'final_is_type_related',
            'tokens_used',
            'processing_time_seconds',
        ]
        
        # Filter to columns that exist
        available_columns = [col for col in export_columns if col in df.columns]
        df[available_columns].to_csv(output_file, index=False)
        
        # Calculate file size
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        log_progress(f"Exported {len(df):,} PRs to {output_file} ({file_size_mb:.1f} MB)")
        
        # Export summary statistics
        self.export_summary(df, output_file)
    
    def export_summary(self, df: pd.DataFrame, output_file: str):
        """Export summary statistics"""
        summary_file = output_file.replace('.csv', '_summary.json')
        
        # Calculate statistics
        total_classified = df['final_is_type_related'].notna().sum()
        type_related = df['final_is_type_related'].sum()
        errors = (df['error'] == True).sum() if 'error' in df.columns else 0
        
        summary = {
            'classification_date': datetime.now().isoformat(),
            'model_used': self.model,
            'provider': self.provider,
            'total_prs_analyzed': int(total_classified),
            'type_related_prs': int(type_related),
            'not_type_related_prs': int(total_classified - type_related),
            'error_prs': int(errors),
            'type_related_percentage': float(type_related / total_classified * 100) if total_classified > 0 else 0,
            
            # Performance statistics
            'total_processing_time_seconds': float(time.time() - self.start_time) if self.start_time else 0,
            'avg_processing_time_per_pr': float(df['processing_time_seconds'].mean()) if 'processing_time_seconds' in df else 0,
            
            # API usage statistics
            'total_api_calls': self.total_api_calls,
            'successful_api_calls': self.successful_calls,
            'failed_api_calls': self.api_errors,
            'total_tokens_used': self.total_tokens_used,
            'avg_tokens_per_pr': float(self.total_tokens_used / total_classified) if total_classified > 0 else 0,
            
            # Confidence statistics
            'avg_classifier_confidence': float(df['classifier_confidence'].mean()) if 'classifier_confidence' in df else 0,
            'avg_validator_confidence': float(df['validator_confidence'].mean()) if 'validator_confidence' in df else 0,
            
            # Validation statistics
            'validation_approved': int((df['validation_result'] == 'APPROVED').sum()) if 'validation_result' in df else 0,
            'validation_rejected': int((df['validation_result'] == 'REJECTED').sum()) if 'validation_result' in df else 0,
            'validation_uncertain': int((df['validation_result'] == 'UNCERTAIN').sum()) if 'validation_result' in df else 0,
            'validation_errors': int((df['validation_result'] == 'ERROR').sum()) if 'validation_result' in df else 0,
            
            # Detection method statistics
            'detected_in_title': int(df['detected_in_title'].sum()) if 'detected_in_title' in df else 0,
            'detected_in_body': int(df['detected_in_body'].sum()) if 'detected_in_body' in df else 0,
            'detected_in_commits': int(df['detected_in_commits'].sum()) if 'detected_in_commits' in df else 0,
            'detected_in_patches': int(df['detected_in_patches'].sum()) if 'detected_in_patches' in df else 0,
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        log_progress(f"Exported summary to {summary_file}")
        
        # Print summary to console
        print(f"\n" + "="*80)
        print("📊 Classification Summary")
        print("="*80)
        print(f"Total PRs analyzed: {summary['total_prs_analyzed']:,}")
        print(f"Type-related PRs: {summary['type_related_prs']:,} ({summary['type_related_percentage']:.1f}%)")
        print(f"Not type-related: {summary['not_type_related_prs']:,}")
        print(f"Errors: {summary['error_prs']:,}")
        print(f"\nPerformance:")
        print(f"  Total time: {summary['total_processing_time_seconds']:.1f}s")
        print(f"  Avg time/PR: {summary['avg_processing_time_per_pr']:.1f}s")
        print(f"\nAPI Usage:")
        print(f"  Total calls: {summary['total_api_calls']:,}")
        print(f"  Successful: {summary['successful_api_calls']:,}")
        print(f"  Failed: {summary['failed_api_calls']:,}")
        print(f"  Total tokens: {summary['total_tokens_used']:,}")
        print(f"  Avg tokens/PR: {summary['avg_tokens_per_pr']:.0f}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-powered type-related PR classifier (FIXED VERSION)')
    parser.add_argument('--input', default='typescript_type_related_agentic_prs.csv',
                       help='Input CSV file with PRs')
    parser.add_argument('--output', default='ai_classified_type_prs.csv',
                       help='Output CSV file')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of PRs to classify (for testing)')
    parser.add_argument('--provider', default='openai', choices=['openai', 'gemini'],
                       help='AI provider to use (default: openai)')
    parser.add_argument('--model', default=None,
                       help='Model to use (default: gpt-4o-mini for OpenAI, gemini-1.5-flash for Gemini)')
    parser.add_argument('--max-concurrent', type=int, default=50,
                       help='Maximum concurrent API requests (default: 50)')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Timeout per API call in seconds (default: 30)')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Process PRs in batches (default: 100)')
    
    args = parser.parse_args()
    
    # Set default model based on provider if not specified
    if args.model is None:
        args.model = 'gpt-4o-mini' if args.provider == 'openai' else 'gemini-2.0-flash-exp'
    
    # Initialize classifier
    try:
        classifier = OpenAITypePRClassifier(
            model=args.model,
            max_concurrent=args.max_concurrent,
            provider=args.provider,
            timeout=args.timeout,
            batch_size=args.batch_size
        )
    except ValueError as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        print("\n📝 Setup Instructions:", file=sys.stderr)
        print("1. Create a .env file in the project root", file=sys.stderr)
        if args.provider == 'openai':
            print("2. Add your OpenAI API key: OPENAI_API_KEY=sk-...", file=sys.stderr)
            print("3. Install: pip install openai python-dotenv", file=sys.stderr)
        else:
            print("2. Add your Gemini API key: GEMINI_API_KEY=your_key...", file=sys.stderr)
            print("3. Install: pip install google-generativeai python-dotenv", file=sys.stderr)
        return
    
    # Load PR data
    classifier.load_pr_data(args.input)
    
    # Classify PRs
    results = classifier.classify_all_prs(
        limit=args.limit,
        output_file=args.output
    )
    
    print("\n" + "="*80)
    print("✅ Classification Complete!")
    print("="*80)
    
    # Show some examples
    if len(results) > 0:
        print("\n📋 Sample Classifications:")
        type_related = results[results['final_is_type_related'] == True].head(3)
        
        for idx, row in type_related.iterrows():
            print(f"\n{'='*80}")
            print(f"PR #{row.get('number')}: {row.get('title', 'No title')[:70]}")
            print(f"Agent: {row.get('agent')} | Confidence: {row.get('classifier_confidence', 0):.2f}")
            print(f"Time: {row.get('processing_time_seconds', 0):.1f}s")
            print(f"Reasoning: {row.get('classifier_reasoning', 'No reasoning')[:200]}...")


if __name__ == '__main__':
    main()
