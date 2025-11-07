#!/usr/bin/env python3
"""
GitHub API-based skills downloader for Claude MPM.

Downloads skills from GitHub repositories using the GitHub API (not git clone).
Saves to src/claude_mpm/skills/bundled/{category}/{skill-name}/

Features:
- GitHub API-based downloading (no git required)
- Authentication via GITHUB_TOKEN environment variable
- Rate limiting handling
- Progress bar for downloads
- Dry-run mode
- Category and skill name filtering
- Validates SKILL.md exists after download
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
import yaml

# Security constants
REQUEST_TIMEOUT = 30  # seconds
MAX_YAML_SIZE = 10 * 1024 * 1024  # 10MB limit


def get_logger() -> logging.Logger:
    """Get a simple logger for this script."""
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger()


class GitHubAPIDownloader:
    """Download skills using GitHub API."""

    def __init__(self, github_token: Optional[str] = None) -> None:
        """Initialize downloader with optional GitHub token."""
        self.github_token: Optional[str] = github_token
        self.session: requests.Session = requests.Session()
        if github_token:
            self.session.headers["Authorization"] = f"token {github_token}"
        self.session.headers["Accept"] = "application/vnd.github.v3+json"
        self.rate_limit_remaining: Optional[int] = None
        self.rate_limit_reset: Optional[int] = None

    def check_rate_limit(self) -> Tuple[int, int]:
        """Check GitHub API rate limit status.

        Returns:
            Tuple of (remaining, reset_timestamp)

        Raises:
            requests.RequestException: If API request fails
        """
        try:
            response = self.session.get(
                "https://api.github.com/rate_limit", timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            core = data["resources"]["core"]
            return core["remaining"], core["reset"]
        except requests.RequestException as e:
            logger.error(f"Failed to check rate limit: {e}")
            raise

    def wait_for_rate_limit(self) -> None:
        """Wait if rate limit is exhausted."""
        if self.rate_limit_remaining is not None and self.rate_limit_remaining < 5:
            if self.rate_limit_reset:
                wait_time = self.rate_limit_reset - time.time()
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit low ({self.rate_limit_remaining} remaining). "
                        f"Waiting {int(wait_time)}s..."
                    )
                    time.sleep(wait_time + 1)

    def parse_github_url(self, url: str) -> Tuple[str, str, str, str]:
        """Parse GitHub URL to extract owner, repo, branch, and path.

        Args:
            url: GitHub URL like https://github.com/user/repo/tree/main/path/to/skill

        Returns:
            Tuple of (owner, repo, branch, path)

        Raises:
            ValueError: If URL format is invalid
        """
        parsed = urlparse(url)

        # Validate URL scheme and host
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
        if "github.com" not in parsed.netloc:
            raise ValueError(f"Not a GitHub URL: {url}")

        parts = parsed.path.strip("/").split("/")

        # Expected format: /owner/repo/tree/branch/path/to/skill
        if len(parts) < 5 or parts[2] != "tree":
            raise ValueError(f"Invalid GitHub URL format: {url}")

        owner = parts[0]
        repo = parts[1]
        branch = parts[3]
        path = "/".join(parts[4:])

        return owner, repo, branch, path

    def get_directory_contents(
        self, owner: str, repo: str, path: str, branch: str = "main"
    ) -> List[Dict[str, Any]]:
        """Get directory contents from GitHub API.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within repository
            branch: Branch name

        Returns:
            List of file/directory metadata

        Raises:
            requests.RequestException: If API request fails
        """
        self.wait_for_rate_limit()

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": branch}

        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)

            # Update rate limit info
            self.rate_limit_remaining = int(
                response.headers.get("X-RateLimit-Remaining", 0)
            )
            self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"Path not found: {path}")
                return []
            raise

    def download_file(
        self, owner: str, repo: str, path: str, branch: str = "main"
    ) -> Optional[bytes]:
        """Download a single file from GitHub.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path to file
            branch: Branch name

        Returns:
            File contents as bytes

        Raises:
            requests.RequestException: If network error occurs
            ValueError: If response is invalid
        """
        self.wait_for_rate_limit()

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": branch}

        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)

            # Update rate limit info
            self.rate_limit_remaining = int(
                response.headers.get("X-RateLimit-Remaining", 0)
            )
            self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

            response.raise_for_status()
            data = response.json()

            # Decode base64 content
            if "content" in data:
                return base64.b64decode(data["content"])
            raise ValueError(f"No content in response for {path}")
        except requests.RequestException as e:
            logger.error(f"Network error downloading {path}: {e}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid response for {path}: {e}")
            raise

    def download_directory_recursive(
        self,
        owner: str,
        repo: str,
        path: str,
        target_dir: Path,
        branch: str = "main",
    ) -> int:
        """Recursively download a directory.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Path within repository
            target_dir: Local target directory
            branch: Branch name

        Returns:
            Number of files downloaded
        """
        contents = self.get_directory_contents(owner, repo, path, branch)
        if not contents:
            return 0

        files_downloaded = 0

        for item in contents:
            item_name = item["name"]
            item_path = item["path"]
            item_type = item["type"]

            if item_type == "file":
                # Download file
                content = self.download_file(owner, repo, item_path, branch)
                if content:
                    file_path = target_dir / item_name
                    file_path.write_bytes(content)
                    logger.debug(f"  Downloaded: {item_name}")
                    files_downloaded += 1
            elif item_type == "dir":
                # Recursively download subdirectory
                subdir = target_dir / item_name
                subdir.mkdir(parents=True, exist_ok=True)
                files_downloaded += self.download_directory_recursive(
                    owner, repo, item_path, subdir, branch
                )

        return files_downloaded


def load_skills_sources(config_path: Path) -> Dict[str, Any]:
    """Load skills sources configuration with security checks.

    Args:
        config_path: Path to skills_sources.yaml

    Returns:
        Parsed configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If YAML is invalid or file too large
    """
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Check file size to prevent YAML bomb
    file_size = config_path.stat().st_size
    if file_size > MAX_YAML_SIZE:
        raise ValueError(
            f"YAML file too large: {file_size} bytes (max {MAX_YAML_SIZE})"
        )

    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if not data:
                raise ValueError(f"Empty configuration file: {config_path}")
            return data
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in {config_path}: {e}")
        raise ValueError(f"Invalid YAML in {config_path}") from e


def download_skill(
    downloader: GitHubAPIDownloader,
    skill_url: str,
    category: str,
    skill_name: str,
    target_base: Path,
    dry_run: bool = False,
) -> bool:
    """Download a single skill.

    Args:
        downloader: GitHubAPIDownloader instance
        skill_url: GitHub URL to skill
        category: Skill category
        skill_name: Skill name
        target_base: Base directory for bundled skills
        dry_run: If True, don't actually download

    Returns:
        True if successful, False otherwise
    """
    try:
        owner, repo, branch, path = downloader.parse_github_url(skill_url)
        target_dir = target_base / category / skill_name

        logger.info(f"Downloading {skill_name} ({category})...")
        if dry_run:
            logger.info(f"  [DRY RUN] Would download to: {target_dir}")
            return True

        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)

        # Download skill
        files_downloaded = downloader.download_directory_recursive(
            owner, repo, path, target_dir, branch
        )

        # Validate SKILL.md exists
        skill_md = target_dir / "SKILL.md"
        if not skill_md.exists():
            logger.error("  SKILL.md not found after download!")
            return False

        logger.info(f"  ✓ Downloaded {files_downloaded} files")
        return True

    except Exception as e:
        logger.error(f"  ✗ Failed to download {skill_name}: {e}")
        return False


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Download Claude Code skills from GitHub using API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all skills
  %(prog)s

  # Download skills from specific category
  %(prog)s --category development

  # Download specific skill
  %(prog)s --skill test-driven-development

  # Dry run to see what would be downloaded
  %(prog)s --dry-run

  # Use GitHub token for higher rate limits
  GITHUB_TOKEN=ghp_xxx %(prog)s

  # Verbose output
  %(prog)s --verbose

Environment Variables:
  GITHUB_TOKEN    GitHub personal access token (optional but recommended)
        """,
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent.parent / "config" / "skills_sources.yaml",
        help="Path to skills_sources.yaml (default: config/skills_sources.yaml)",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "skills"
        / "bundled",
        help="Output directory (default: src/claude_mpm/skills/bundled)",
    )

    parser.add_argument(
        "--category",
        help="Download only skills from this category",
    )

    parser.add_argument(
        "--skill",
        help="Download only this specific skill",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--check-rate-limit",
        action="store_true",
        help="Check GitHub API rate limit and exit",
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Get GitHub token
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        logger.warning(
            "No GITHUB_TOKEN found. API rate limit will be 60 requests/hour."
        )
        logger.warning("Set GITHUB_TOKEN for 5000 requests/hour.")

    # Initialize downloader
    downloader = GitHubAPIDownloader(github_token)

    # Check rate limit if requested
    if args.check_rate_limit:
        remaining, reset_time = downloader.check_rate_limit()
        reset_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(reset_time))
        print(f"Rate limit remaining: {remaining}")
        print(f"Rate limit resets at: {reset_str}")
        sys.exit(0)

    # Load configuration
    config = load_skills_sources(args.config)

    # Build list of skills to download
    skills_to_download = []

    for source_name, source_config in config.get("sources", {}).items():
        for category, skill_list in source_config.get("skills", {}).items():
            # Apply category filter
            if args.category and category != args.category:
                continue

            for skill_name in skill_list:
                # Apply skill name filter
                if args.skill and skill_name != args.skill:
                    continue

                # Construct URL
                base_url = source_config.get("base_url", "")
                skill_url = f"{base_url}/{category}/{skill_name}"

                skills_to_download.append(
                    {
                        "name": skill_name,
                        "category": category,
                        "url": skill_url,
                        "source": source_name,
                    }
                )

    if not skills_to_download:
        logger.error("No skills matched the filters!")
        sys.exit(1)

    # Summary
    logger.info(f"Found {len(skills_to_download)} skills to download")
    if args.dry_run:
        logger.info("[DRY RUN MODE - No files will be downloaded]")
    logger.info("")

    # Download skills
    successful = 0
    failed = 0

    for skill in skills_to_download:
        success = download_skill(
            downloader,
            skill["url"],
            skill["category"],
            skill["name"],
            args.output,
            dry_run=args.dry_run,
        )

        if success:
            successful += 1
        else:
            failed += 1

    # Final summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total skills: {len(skills_to_download)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    # Check remaining rate limit
    remaining, _ = downloader.check_rate_limit()
    logger.info(f"API calls remaining: {remaining}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
