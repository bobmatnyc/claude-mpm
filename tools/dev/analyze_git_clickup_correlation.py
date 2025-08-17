#!/usr/bin/env python3
"""
Git Commit and ClickUp Ticket Correlation Analysis

This script analyzes git commits from the last 2 months and correlates them with ClickUp tickets.
It extracts ticket references (EP-XXXX, ISS-XXXX, TSK-XXXX) from commit messages and fetches
corresponding task data from ClickUp API.

Architecture:
- GitCommitExtractor: Extracts commits with ticket references using git log
- ClickUpClient: Fetches task data from ClickUp API with rate limiting
- DataAnalyzer: Correlates commits with tasks and generates time distribution
- Visualizer: Creates charts and summary statistics

Performance considerations:
- ClickUp API rate limit: 2 requests/second
- Batch processing for efficiency
- Caching to avoid redundant API calls
"""

import json
import logging
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GitCommitExtractor:
    """
    Extracts git commits with ticket references from the repository.

    Design decisions:
    - Uses git log with custom format for efficient parsing
    - Extracts multiple ticket patterns to handle various formats
    - Groups commits by ticket for easier correlation
    """

    TICKET_PATTERNS = [
        r"EP-\d{4}",  # Epic tickets
        r"ISS-\d{4}",  # Issue tickets
        r"TSK-\d{4}",  # Task tickets
    ]

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.ticket_regex = re.compile("|".join(self.TICKET_PATTERNS))

    def extract_commits(self, days: int = 60) -> Dict[str, List[Dict]]:
        """
        Extract commits from the last N days with ticket references.

        Returns:
            Dictionary mapping ticket IDs to list of commits
        """
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Git log format: hash|author|date|subject|body
        git_cmd = [
            "git",
            "log",
            f"--since={since_date}",
            "--pretty=format:%H|%an|%ad|%s|%b",
            "--date=iso",
        ]

        try:
            result = subprocess.run(
                git_cmd, cwd=self.repo_path, capture_output=True, text=True, check=True
            )

            commits_by_ticket = defaultdict(list)

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|", 4)
                if len(parts) < 4:
                    continue

                commit_hash, author, date_str, subject = parts[:4]
                body = parts[4] if len(parts) > 4 else ""

                # Extract ticket references from subject and body
                full_message = f"{subject} {body}"
                tickets = self.ticket_regex.findall(full_message)

                if tickets:
                    commit_data = {
                        "hash": commit_hash,
                        "author": author,
                        "date": datetime.fromisoformat(
                            date_str.replace(" +", "+").replace(" -", "-")
                        ),
                        "subject": subject,
                        "tickets": list(set(tickets)),  # Remove duplicates
                    }

                    # Add commit to each referenced ticket
                    for ticket in tickets:
                        commits_by_ticket[ticket].append(commit_data)

            logger.info(
                f"Extracted {sum(len(v) for v in commits_by_ticket.values())} commits referencing {len(commits_by_ticket)} tickets"
            )
            return dict(commits_by_ticket)

        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            return {}


class ClickUpClient:
    """
    ClickUp API client with rate limiting and caching.

    Design decisions:
    - Implements exponential backoff for rate limit handling
    - Caches task data to minimize API calls
    - Batch fetches tasks when possible
    """

    def __init__(self, api_key: str, workspace_id: str):
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.base_url = "https://api.clickup.com/api/v2"
        self.headers = {"Authorization": api_key}
        self.task_cache = {}
        self.last_request_time = 0
        self.rate_limit_delay = 0.5  # 2 requests per second

    def _rate_limit(self):
        """Implement rate limiting to respect API limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)

        self.last_request_time = time.time()

    def search_tasks_by_ids(self, task_ids: List[str]) -> Dict[str, Dict]:
        """
        Search for tasks by their custom IDs (EP-XXXX, ISS-XXXX, TSK-XXXX).

        Returns:
            Dictionary mapping task IDs to task data
        """
        tasks = {}

        # Filter out already cached tasks
        uncached_ids = [tid for tid in task_ids if tid not in self.task_cache]

        if not uncached_ids:
            return {
                tid: self.task_cache[tid] for tid in task_ids if tid in self.task_cache
            }

        # Search for tasks using custom field search
        for task_id in uncached_ids:
            self._rate_limit()

            try:
                # Search in all accessible lists
                search_url = f"{self.base_url}/team/{self.workspace_id}/task"
                params = {
                    "custom_task_ids": "true",
                    "team_id": self.workspace_id,
                    "include_closed": "true",
                }

                response = requests.get(search_url, headers=self.headers, params=params)

                if response.status_code == 200:
                    data = response.json()

                    # Search through tasks for matching custom ID
                    for task in data.get("tasks", []):
                        if task.get("custom_id") == task_id or task_id in task.get(
                            "name", ""
                        ):
                            task_data = {
                                "id": task["id"],
                                "name": task["name"],
                                "status": task["status"]["status"],
                                "assignees": [
                                    a["username"] for a in task.get("assignees", [])
                                ],
                                "list": task.get("list", {}).get("name", "Unknown"),
                                "folder": task.get("folder", {}).get("name", "Unknown"),
                                "space": task.get("space", {}).get("name", "Unknown"),
                                "date_created": datetime.fromtimestamp(
                                    int(task["date_created"]) / 1000
                                ),
                                "date_updated": datetime.fromtimestamp(
                                    int(task["date_updated"]) / 1000
                                ),
                                "time_estimate": task.get("time_estimate", 0),
                                "time_spent": task.get("time_spent", 0),
                                "tags": [t["name"] for t in task.get("tags", [])],
                                "priority": task.get("priority", {}).get(
                                    "priority", "none"
                                ),
                            }

                            self.task_cache[task_id] = task_data
                            tasks[task_id] = task_data
                            break

                elif response.status_code == 429:  # Rate limited
                    logger.warning("Rate limited by ClickUp API, waiting...")
                    time.sleep(60)  # Wait 1 minute

                else:
                    logger.error(
                        f"Failed to fetch task {task_id}: {response.status_code}"
                    )

            except Exception as e:
                logger.error(f"Error fetching task {task_id}: {e}")

        # Return all requested tasks (cached + newly fetched)
        return {tid: self.task_cache[tid] for tid in task_ids if tid in self.task_cache}


class DataAnalyzer:
    """
    Analyzes correlation between git commits and ClickUp tasks.

    Design decisions:
    - Aggregates data by week for trend analysis
    - Calculates time distribution by project (space/folder)
    - Tracks developer contributions across projects
    """

    def __init__(
        self, commits_by_ticket: Dict[str, List[Dict]], tasks: Dict[str, Dict]
    ):
        self.commits_by_ticket = commits_by_ticket
        self.tasks = tasks
        self.analysis_data = None

    def prepare_analysis_data(self) -> pd.DataFrame:
        """
        Prepare data for analysis by combining commit and task information.

        Returns:
            DataFrame with combined commit and task data
        """
        records = []

        for ticket_id, commits in self.commits_by_ticket.items():
            task_data = self.tasks.get(ticket_id, {})

            for commit in commits:
                record = {
                    "ticket_id": ticket_id,
                    "commit_hash": commit["hash"],
                    "author": commit["author"],
                    "commit_date": commit["date"],
                    "commit_week": commit["date"].isocalendar()[1],
                    "commit_year": commit["date"].year,
                    "subject": commit["subject"],
                    "project": task_data.get("space", "Unknown"),
                    "folder": task_data.get("folder", "Unknown"),
                    "task_name": task_data.get("name", "Unknown"),
                    "task_status": task_data.get("status", "Unknown"),
                    "assignees": ", ".join(task_data.get("assignees", [])),
                    "time_estimate_hours": task_data.get("time_estimate", 0) / 3600000
                    if task_data
                    else 0,
                    "time_spent_hours": task_data.get("time_spent", 0) / 3600000
                    if task_data
                    else 0,
                    "priority": task_data.get("priority", "none"),
                    "tags": ", ".join(task_data.get("tags", [])),
                }
                records.append(record)

        self.analysis_data = pd.DataFrame(records)
        return self.analysis_data

    def calculate_weekly_distribution(self) -> pd.DataFrame:
        """
        Calculate time distribution by project on a weekly basis.

        Returns:
            DataFrame with weekly project distribution
        """
        if self.analysis_data is None:
            self.prepare_analysis_data()

        # Group by year-week and project
        weekly_dist = (
            self.analysis_data.groupby(["commit_year", "commit_week", "project"])
            .size()
            .reset_index(name="commit_count")
        )

        # Calculate percentage within each week
        weekly_totals = weekly_dist.groupby(["commit_year", "commit_week"])[
            "commit_count"
        ].sum()
        weekly_dist["percentage"] = weekly_dist.apply(
            lambda row: row["commit_count"]
            / weekly_totals[(row["commit_year"], row["commit_week"])]
            * 100,
            axis=1,
        )

        return weekly_dist

    def calculate_developer_contributions(self) -> pd.DataFrame:
        """
        Calculate developer contributions by project.

        Returns:
            DataFrame with developer contribution breakdown
        """
        if self.analysis_data is None:
            self.prepare_analysis_data()

        # Group by author and project
        dev_contrib = (
            self.analysis_data.groupby(["author", "project"])
            .size()
            .reset_index(name="commit_count")
        )

        # Calculate percentage for each developer
        dev_totals = dev_contrib.groupby("author")["commit_count"].sum()
        dev_contrib["percentage"] = dev_contrib.apply(
            lambda row: row["commit_count"] / dev_totals[row["author"]] * 100, axis=1
        )

        return dev_contrib

    def generate_summary_statistics(self) -> Dict:
        """
        Generate summary statistics for the analysis.

        Returns:
            Dictionary with summary statistics
        """
        if self.analysis_data is None:
            self.prepare_analysis_data()

        stats = {
            "total_commits": len(self.analysis_data),
            "unique_tickets": self.analysis_data["ticket_id"].nunique(),
            "unique_developers": self.analysis_data["author"].nunique(),
            "projects": self.analysis_data["project"].value_counts().to_dict(),
            "date_range": {
                "start": self.analysis_data["commit_date"].min().strftime("%Y-%m-%d"),
                "end": self.analysis_data["commit_date"].max().strftime("%Y-%m-%d"),
            },
            "tickets_without_clickup_data": len(
                [t for t in self.commits_by_ticket.keys() if t not in self.tasks]
            ),
            "top_contributors": self.analysis_data["author"]
            .value_counts()
            .head(5)
            .to_dict(),
            "priority_distribution": self.analysis_data["priority"]
            .value_counts()
            .to_dict(),
            "status_distribution": self.analysis_data["task_status"]
            .value_counts()
            .to_dict(),
        }

        return stats


class Visualizer:
    """
    Creates visualizations for the analysis results.

    Design decisions:
    - Uses seaborn for consistent, professional styling
    - Generates multiple chart types for comprehensive view
    - Saves charts as high-resolution images
    """

    def __init__(self, output_dir: str = "analysis_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Set style
        sns.set_style("whitegrid")
        plt.rcParams["figure.figsize"] = (12, 8)

    def plot_weekly_time_distribution(self, weekly_dist: pd.DataFrame):
        """Create stacked area chart for weekly time distribution by project."""
        # Pivot data for stacked area chart
        pivot_data = weekly_dist.pivot_table(
            index=["commit_year", "commit_week"],
            columns="project",
            values="percentage",
            fill_value=0,
        )

        # Create week labels
        week_labels = [f"{y}-W{w}" for y, w in pivot_data.index]

        # Create stacked area chart
        fig, ax = plt.subplots(figsize=(14, 8))
        pivot_data.plot.area(ax=ax, stacked=True, alpha=0.7)

        ax.set_xlabel("Week", fontsize=12)
        ax.set_ylabel("Percentage of Commits (%)", fontsize=12)
        ax.set_title(
            "Weekly Time Distribution by Project", fontsize=16, fontweight="bold"
        )
        ax.set_xticklabels(week_labels, rotation=45, ha="right")
        ax.legend(title="Project", bbox_to_anchor=(1.05, 1), loc="upper left")

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "weekly_time_distribution.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    def plot_developer_contributions(self, dev_contrib: pd.DataFrame):
        """Create grouped bar chart for developer contributions by project."""
        # Pivot data for grouped bars
        pivot_data = dev_contrib.pivot_table(
            index="author", columns="project", values="commit_count", fill_value=0
        )

        # Create grouped bar chart
        fig, ax = plt.subplots(figsize=(14, 8))
        pivot_data.plot(kind="bar", ax=ax, width=0.8)

        ax.set_xlabel("Developer", fontsize=12)
        ax.set_ylabel("Number of Commits", fontsize=12)
        ax.set_title(
            "Developer Contributions by Project", fontsize=16, fontweight="bold"
        )
        ax.legend(title="Project", bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.xticks(rotation=45, ha="right")

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "developer_contributions.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    def plot_project_distribution_pie(self, analysis_data: pd.DataFrame):
        """Create pie chart for overall project distribution."""
        project_counts = analysis_data["project"].value_counts()

        fig, ax = plt.subplots(figsize=(10, 10))
        colors = sns.color_palette("husl", len(project_counts))

        wedges, texts, autotexts = ax.pie(
            project_counts.values,
            labels=project_counts.index,
            autopct="%1.1f%%",
            colors=colors,
            startangle=90,
        )

        ax.set_title("Overall Project Distribution", fontsize=16, fontweight="bold")

        # Improve text readability
        for text in texts:
            text.set_fontsize(12)
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontsize(12)
            autotext.set_fontweight("bold")

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "project_distribution_pie.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    def plot_commit_timeline(self, analysis_data: pd.DataFrame):
        """Create timeline chart showing commit activity over time."""
        # Group by date and project
        timeline_data = (
            analysis_data.groupby([pd.Grouper(key="commit_date", freq="D"), "project"])
            .size()
            .reset_index(name="commit_count")
        )

        fig, ax = plt.subplots(figsize=(16, 8))

        # Plot each project separately
        for project in timeline_data["project"].unique():
            project_data = timeline_data[timeline_data["project"] == project]
            ax.plot(
                project_data["commit_date"],
                project_data["commit_count"],
                marker="o",
                label=project,
                alpha=0.7,
            )

        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Number of Commits", fontsize=12)
        ax.set_title(
            "Commit Activity Timeline by Project", fontsize=16, fontweight="bold"
        )
        ax.legend(title="Project", bbox_to_anchor=(1.05, 1), loc="upper left")
        ax.grid(True, alpha=0.3)

        # Format x-axis
        plt.xticks(rotation=45, ha="right")

        plt.tight_layout()
        plt.savefig(
            self.output_dir / "commit_timeline.png", dpi=300, bbox_inches="tight"
        )
        plt.close()

    def create_summary_report(self, stats: Dict, analysis_data: pd.DataFrame):
        """Create a text summary report."""
        report_path = self.output_dir / "analysis_summary.txt"

        with open(report_path, "w") as f:
            f.write("Git Commit and ClickUp Correlation Analysis\n")
            f.write("=" * 50 + "\n\n")

            f.write(
                f"Analysis Period: {stats['date_range']['start']} to {stats['date_range']['end']}\n"
            )
            f.write(f"Total Commits Analyzed: {stats['total_commits']}\n")
            f.write(f"Unique Tickets Referenced: {stats['unique_tickets']}\n")
            f.write(f"Unique Developers: {stats['unique_developers']}\n")
            f.write(
                f"Tickets without ClickUp data: {stats['tickets_without_clickup_data']}\n\n"
            )

            f.write("Project Distribution:\n")
            f.write("-" * 30 + "\n")
            for project, count in stats["projects"].items():
                percentage = (count / stats["total_commits"]) * 100
                f.write(f"  {project}: {count} commits ({percentage:.1f}%)\n")

            f.write("\nTop Contributors:\n")
            f.write("-" * 30 + "\n")
            for developer, count in stats["top_contributors"].items():
                f.write(f"  {developer}: {count} commits\n")

            f.write("\nTask Priority Distribution:\n")
            f.write("-" * 30 + "\n")
            for priority, count in stats["priority_distribution"].items():
                f.write(f"  {priority}: {count} tasks\n")

            f.write("\nTask Status Distribution:\n")
            f.write("-" * 30 + "\n")
            for status, count in stats["status_distribution"].items():
                f.write(f"  {status}: {count} tasks\n")

            # Add weekly summary
            f.write("\nWeekly Commit Summary:\n")
            f.write("-" * 30 + "\n")
            weekly_summary = (
                analysis_data.groupby(["commit_year", "commit_week"])
                .size()
                .reset_index(name="commits")
            )

            for _, row in weekly_summary.iterrows():
                f.write(
                    f"  {row['commit_year']}-W{row['commit_week']:02d}: {row['commits']} commits\n"
                )


def main():
    """Main execution function."""
    # Configuration
    REPO_PATH = "/Users/masa/Projects/claude-mpm"
    API_KEY = "pk_88362330_0PLR81BFHW965IMG69LUX4KAVLU1E9MC"
    WORKSPACE_ID = "9014422905"
    ANALYSIS_DAYS = 60  # Last 2 months

    logger.info("Starting Git-ClickUp correlation analysis...")

    # Step 1: Extract git commits
    logger.info("Extracting git commits...")
    extractor = GitCommitExtractor(REPO_PATH)
    commits_by_ticket = extractor.extract_commits(ANALYSIS_DAYS)

    if not commits_by_ticket:
        logger.error("No commits with ticket references found")
        return

    # Step 2: Fetch ClickUp tasks
    logger.info(f"Fetching ClickUp data for {len(commits_by_ticket)} tickets...")
    client = ClickUpClient(API_KEY, WORKSPACE_ID)
    tasks = client.search_tasks_by_ids(list(commits_by_ticket.keys()))

    logger.info(f"Successfully fetched data for {len(tasks)} tasks")

    # Step 3: Analyze data
    logger.info("Analyzing correlation data...")
    analyzer = DataAnalyzer(commits_by_ticket, tasks)
    analysis_data = analyzer.prepare_analysis_data()
    weekly_dist = analyzer.calculate_weekly_distribution()
    dev_contrib = analyzer.calculate_developer_contributions()
    stats = analyzer.generate_summary_statistics()

    # Step 4: Generate visualizations
    logger.info("Generating visualizations...")
    visualizer = Visualizer()
    visualizer.plot_weekly_time_distribution(weekly_dist)
    visualizer.plot_developer_contributions(dev_contrib)
    visualizer.plot_project_distribution_pie(analysis_data)
    visualizer.plot_commit_timeline(analysis_data)
    visualizer.create_summary_report(stats, analysis_data)

    # Step 5: Save raw data
    logger.info("Saving analysis data...")
    analysis_data.to_csv(visualizer.output_dir / "analysis_data.csv", index=False)
    weekly_dist.to_csv(visualizer.output_dir / "weekly_distribution.csv", index=False)
    dev_contrib.to_csv(
        visualizer.output_dir / "developer_contributions.csv", index=False
    )

    with open(visualizer.output_dir / "summary_statistics.json", "w") as f:
        json.dump(stats, f, indent=2, default=str)

    logger.info(f"Analysis complete! Results saved to {visualizer.output_dir}")


if __name__ == "__main__":
    main()
