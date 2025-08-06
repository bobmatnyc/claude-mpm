#!/usr/bin/env python3
"""
Test suite for Git-ClickUp correlation analysis.

Tests each component of the analysis pipeline:
- Git commit extraction with various ticket formats
- ClickUp API integration with rate limiting
- Data analysis and aggregation logic
- Visualization generation
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import shutil
from pathlib import Path
import pandas as pd

# Import our analysis modules
from analyze_git_clickup_correlation import (
    GitCommitExtractor,
    ClickUpClient,
    DataAnalyzer,
    Visualizer
)


class TestGitCommitExtractor(unittest.TestCase):
    """Test Git commit extraction functionality."""
    
    def setUp(self):
        """Create a temporary git repository for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.extractor = GitCommitExtractor(self.temp_dir)
        
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
        
    @patch('subprocess.run')
    def test_extract_commits_with_tickets(self, mock_run):
        """Test extraction of commits with ticket references."""
        # Mock git log output
        git_output = """abc123|John Doe|2024-01-15 10:00:00 +0000|Fix bug in EP-0001|Details about the fix
def456|Jane Smith|2024-01-16 11:00:00 +0000|Implement ISS-0002 and TSK-0003|Implementation details
ghi789|Bob Johnson|2024-01-17 12:00:00 +0000|No ticket reference|Just a regular commit"""
        
        mock_run.return_value = Mock(
            stdout=git_output,
            returncode=0
        )
        
        commits = self.extractor.extract_commits(days=30)
        
        # Verify ticket extraction
        self.assertIn('EP-0001', commits)
        self.assertIn('ISS-0002', commits)
        self.assertIn('TSK-0003', commits)
        self.assertEqual(len(commits['EP-0001']), 1)
        self.assertEqual(commits['EP-0001'][0]['author'], 'John Doe')
        
    def test_ticket_pattern_matching(self):
        """Test regex patterns for ticket extraction."""
        test_strings = [
            ("Fix EP-0001", ["EP-0001"]),
            ("Implement ISS-1234 and TSK-5678", ["ISS-1234", "TSK-5678"]),
            ("No tickets here", []),
            ("Multiple EP-0001 EP-0001 references", ["EP-0001"]),  # Should dedupe
        ]
        
        for text, expected in test_strings:
            matches = self.extractor.ticket_regex.findall(text)
            self.assertEqual(sorted(list(set(matches))), sorted(expected))


class TestClickUpClient(unittest.TestCase):
    """Test ClickUp API client functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = ClickUpClient("test_api_key", "test_workspace")
        
    @patch('requests.get')
    def test_search_tasks_successful(self, mock_get):
        """Test successful task search."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tasks': [{
                'id': '12345',
                'name': 'Test Task EP-0001',
                'custom_id': 'EP-0001',
                'status': {'status': 'in progress'},
                'assignees': [{'username': 'john.doe'}],
                'list': {'name': 'Development'},
                'folder': {'name': 'Backend'},
                'space': {'name': 'Engineering'},
                'date_created': '1705320000000',  # Timestamp in milliseconds
                'date_updated': '1705406400000',
                'time_estimate': 7200000,  # 2 hours in milliseconds
                'time_spent': 3600000,     # 1 hour in milliseconds
                'tags': [{'name': 'bug'}, {'name': 'high-priority'}],
                'priority': {'priority': 'high'}
            }]
        }
        mock_get.return_value = mock_response
        
        tasks = self.client.search_tasks_by_ids(['EP-0001'])
        
        self.assertIn('EP-0001', tasks)
        self.assertEqual(tasks['EP-0001']['name'], 'Test Task EP-0001')
        self.assertEqual(tasks['EP-0001']['space'], 'Engineering')
        self.assertEqual(tasks['EP-0001']['time_estimate'], 7200000)
        
    @patch('requests.get')
    @patch('time.sleep')
    def test_rate_limiting(self, mock_sleep, mock_get):
        """Test rate limit handling."""
        # First request returns rate limit error
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        # Second request succeeds
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {'tasks': []}
        
        mock_get.side_effect = [mock_response_429, mock_response_200]
        
        tasks = self.client.search_tasks_by_ids(['EP-0001'])
        
        # Verify sleep was called for rate limiting
        mock_sleep.assert_called_with(60)
        
    def test_caching(self):
        """Test task caching functionality."""
        # Add task to cache
        self.client.task_cache['EP-0001'] = {'name': 'Cached Task'}
        
        # Should return from cache without API call
        with patch('requests.get') as mock_get:
            tasks = self.client.search_tasks_by_ids(['EP-0001'])
            mock_get.assert_not_called()
            
        self.assertEqual(tasks['EP-0001']['name'], 'Cached Task')


class TestDataAnalyzer(unittest.TestCase):
    """Test data analysis functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.commits_by_ticket = {
            'EP-0001': [{
                'hash': 'abc123',
                'author': 'John Doe',
                'date': datetime(2024, 1, 15, 10, 0),
                'subject': 'Fix bug',
                'tickets': ['EP-0001']
            }],
            'ISS-0002': [{
                'hash': 'def456',
                'author': 'Jane Smith',
                'date': datetime(2024, 1, 16, 11, 0),
                'subject': 'New feature',
                'tickets': ['ISS-0002']
            }]
        }
        
        self.tasks = {
            'EP-0001': {
                'space': 'Engineering',
                'folder': 'Backend',
                'name': 'Bug Fix',
                'status': 'completed',
                'assignees': ['john.doe'],
                'time_estimate': 7200000,
                'time_spent': 3600000,
                'priority': 'high',
                'tags': ['bug']
            },
            'ISS-0002': {
                'space': 'Product',
                'folder': 'Features',
                'name': 'New Feature',
                'status': 'in progress',
                'assignees': ['jane.smith'],
                'time_estimate': 14400000,
                'time_spent': 7200000,
                'priority': 'medium',
                'tags': ['feature']
            }
        }
        
        self.analyzer = DataAnalyzer(self.commits_by_ticket, self.tasks)
        
    def test_prepare_analysis_data(self):
        """Test data preparation for analysis."""
        df = self.analyzer.prepare_analysis_data()
        
        self.assertEqual(len(df), 2)
        self.assertIn('ticket_id', df.columns)
        self.assertIn('project', df.columns)
        self.assertIn('author', df.columns)
        self.assertEqual(df.iloc[0]['project'], 'Engineering')
        
    def test_calculate_weekly_distribution(self):
        """Test weekly distribution calculation."""
        weekly_dist = self.analyzer.calculate_weekly_distribution()
        
        self.assertIn('percentage', weekly_dist.columns)
        self.assertIn('commit_count', weekly_dist.columns)
        # Percentages should sum to 100 for each week
        for (year, week), group in weekly_dist.groupby(['commit_year', 'commit_week']):
            self.assertAlmostEqual(group['percentage'].sum(), 100.0)
            
    def test_calculate_developer_contributions(self):
        """Test developer contribution calculation."""
        dev_contrib = self.analyzer.calculate_developer_contributions()
        
        self.assertIn('John Doe', dev_contrib['author'].values)
        self.assertIn('Jane Smith', dev_contrib['author'].values)
        
        # Each developer's percentages should sum to 100
        for author, group in dev_contrib.groupby('author'):
            self.assertAlmostEqual(group['percentage'].sum(), 100.0)
            
    def test_generate_summary_statistics(self):
        """Test summary statistics generation."""
        stats = self.analyzer.generate_summary_statistics()
        
        self.assertEqual(stats['total_commits'], 2)
        self.assertEqual(stats['unique_tickets'], 2)
        self.assertEqual(stats['unique_developers'], 2)
        self.assertIn('Engineering', stats['projects'])
        self.assertIn('Product', stats['projects'])


class TestVisualizer(unittest.TestCase):
    """Test visualization functionality."""
    
    def setUp(self):
        """Set up test visualizer with temp directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.visualizer = Visualizer(self.temp_dir)
        
    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
        
    def test_output_directory_creation(self):
        """Test that output directory is created."""
        self.assertTrue(Path(self.temp_dir).exists())
        
    @patch('matplotlib.pyplot.savefig')
    def test_plot_generation(self, mock_savefig):
        """Test that plots are generated without errors."""
        # Create sample data
        analysis_data = pd.DataFrame({
            'commit_date': [datetime.now() - timedelta(days=i) for i in range(10)],
            'project': ['Project A'] * 5 + ['Project B'] * 5,
            'author': ['Dev 1'] * 3 + ['Dev 2'] * 7,
            'commit_week': [1, 1, 1, 2, 2, 2, 2, 3, 3, 3],
            'commit_year': [2024] * 10
        })
        
        weekly_dist = pd.DataFrame({
            'commit_year': [2024, 2024, 2024],
            'commit_week': [1, 2, 3],
            'project': ['Project A', 'Project B', 'Project A'],
            'commit_count': [3, 4, 3],
            'percentage': [60, 80, 60]
        })
        
        dev_contrib = pd.DataFrame({
            'author': ['Dev 1', 'Dev 2'],
            'project': ['Project A', 'Project B'],
            'commit_count': [3, 7],
            'percentage': [30, 70]
        })
        
        # Test each plot method
        self.visualizer.plot_weekly_time_distribution(weekly_dist)
        self.visualizer.plot_developer_contributions(dev_contrib)
        self.visualizer.plot_project_distribution_pie(analysis_data)
        self.visualizer.plot_commit_timeline(analysis_data)
        
        # Verify plots were saved
        self.assertEqual(mock_savefig.call_count, 4)
        
    def test_summary_report_creation(self):
        """Test summary report file creation."""
        stats = {
            'total_commits': 100,
            'unique_tickets': 50,
            'unique_developers': 10,
            'date_range': {'start': '2024-01-01', 'end': '2024-02-29'},
            'tickets_without_clickup_data': 5,
            'projects': {'Project A': 60, 'Project B': 40},
            'top_contributors': {'Dev 1': 50, 'Dev 2': 30},
            'priority_distribution': {'high': 20, 'medium': 60, 'low': 20},
            'status_distribution': {'completed': 70, 'in progress': 30}
        }
        
        analysis_data = pd.DataFrame({
            'commit_year': [2024] * 5,
            'commit_week': [1, 1, 2, 2, 3]
        })
        
        self.visualizer.create_summary_report(stats, analysis_data)
        
        report_path = Path(self.temp_dir) / 'analysis_summary.txt'
        self.assertTrue(report_path.exists())
        
        # Verify content
        with open(report_path, 'r') as f:
            content = f.read()
            self.assertIn('Total Commits Analyzed: 100', content)
            self.assertIn('Project A: 60 commits', content)


if __name__ == '__main__':
    unittest.main()