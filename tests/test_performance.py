#!/usr/bin/env python3
"""Performance tests for ConfigScreenV2 with various project sizes."""

import sys
import tempfile
import yaml
import time
import psutil
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.manager.screens.config_screen_v2 import ConfigScreenV2, YAMLFormWidget, EnhancedConfigEditor
from claude_mpm.manager.discovery import Installation, InstallationDiscovery


class MockApp:
    """Mock application for testing."""
    def __init__(self):
        self.dialogs = []
        
    def show_dialog(self, title, content):
        self.dialogs.append({"title": title, "content": content})
    
    def close_dialog(self):
        if self.dialogs:
            self.dialogs.pop()


def measure_performance(func, *args, **kwargs):
    """Measure execution time and memory usage of a function."""
    process = psutil.Process(os.getpid())
    
    # Get initial metrics
    start_memory = process.memory_info().rss
    start_time = time.perf_counter()
    
    # Execute function
    result = func(*args, **kwargs)
    
    # Get final metrics
    end_time = time.perf_counter()
    end_memory = process.memory_info().rss
    
    execution_time = end_time - start_time
    memory_delta = end_memory - start_memory
    
    return result, execution_time, memory_delta


def create_test_config(size='small'):
    """Create test configurations of different sizes."""
    configs = {
        'small': {
            "project": {
                "name": "small-project",
                "type": "web",
                "enabled": True
            },
            "database": {
                "host": "localhost",
                "port": 5432
            }
        },
        'medium': {
            "project": {
                "name": "medium-project",
                "type": "enterprise",
                "enabled": True,
                "features": ["auth", "api", "ui", "monitoring", "logging"]
            },
            "services": {
                f"service_{i}": {
                    "enabled": True,
                    "port": 8000 + i,
                    "replicas": 3,
                    "config": {
                        f"setting_{j}": f"value_{i}_{j}"
                        for j in range(10)
                    }
                }
                for i in range(20)
            },
            "database": {
                "primary": {
                    "host": "db-primary.local",
                    "port": 5432,
                    "replicas": ["db-replica1", "db-replica2"]
                },
                "cache": {
                    "host": "redis.local",
                    "port": 6379,
                    "ttl": 3600
                }
            }
        },
        'large': {
            "project": {
                "name": "large-enterprise-project",
                "type": "microservices",
                "enabled": True,
                "version": "3.2.1",
                "features": ["auth", "api", "ui", "monitoring", "logging", "analytics", "reporting"]
            },
            "microservices": {
                f"service_{i}": {
                    "enabled": True,
                    "version": f"1.{i}.0",
                    "port": 8000 + i,
                    "replicas": 3 if i % 2 == 0 else 5,
                    "resources": {
                        "cpu": f"{0.5 + (i * 0.1):.1f}",
                        "memory": f"{512 + (i * 64)}Mi",
                        "storage": f"{1 + i}Gi"
                    },
                    "config": {
                        f"setting_{j}": f"value_{i}_{j}"
                        for j in range(20)
                    },
                    "dependencies": [f"service_{(i-1) % 50}" for _ in range(5)],
                    "environment": {
                        f"ENV_VAR_{k}": f"env_value_{i}_{k}"
                        for k in range(15)
                    }
                }
                for i in range(100)
            },
            "databases": {
                "primary": {
                    "host": "primary-db.internal",
                    "port": 5432,
                    "database": "main",
                    "pool_size": 20,
                    "replicas": [f"replica-{j}.internal" for j in range(3)]
                },
                "analytics": {
                    "host": "analytics-db.internal",
                    "port": 5433,
                    "database": "analytics",
                    "pool_size": 10
                },
                "cache": {
                    "redis": {
                        "host": "redis.internal",
                        "port": 6379,
                        "ttl": 3600,
                        "max_connections": 100
                    },
                    "memcached": {
                        "host": "memcached.internal",
                        "port": 11211,
                        "ttl": 1800
                    }
                }
            },
            "monitoring": {
                "metrics": {
                    f"metric_{i}": {
                        "enabled": True,
                        "interval": 30,
                        "thresholds": {
                            "warning": i * 0.7,
                            "critical": i * 0.9
                        }
                    }
                    for i in range(50)
                },
                "alerts": {
                    f"alert_{i}": {
                        "enabled": True,
                        "channels": ["email", "slack", "pagerduty"],
                        "conditions": [f"condition_{j}" for j in range(3)]
                    }
                    for i in range(30)
                }
            }
        }
    }
    
    return configs[size]


def test_form_widget_performance():
    """Test YAMLFormWidget performance with different config sizes."""
    print("Testing YAMLFormWidget Performance...")
    
    results = {}
    
    for size in ['small', 'medium', 'large']:
        print(f"\n--- Testing {size} configuration ---")
        
        config = create_test_config(size)
        yaml_text = yaml.dump(config)
        
        print(f"YAML size: {len(yaml_text):,} characters")
        
        # Test form creation and loading
        form = YAMLFormWidget()
        
        _, load_time, load_memory = measure_performance(form.load_yaml, yaml_text)
        
        print(f"Load time: {load_time:.3f}s")
        print(f"Load memory: {load_memory / 1024 / 1024:.1f}MB")
        print(f"Form fields generated: {len(form.widgets_map)}")
        
        # Test YAML generation
        _, generate_time, generate_memory = measure_performance(form.get_yaml)
        
        print(f"Generate time: {generate_time:.3f}s")
        print(f"Generate memory: {generate_memory / 1024 / 1024:.1f}MB")
        
        # Test change detection
        _, change_time, change_memory = measure_performance(form.has_changes)
        
        print(f"Change detection time: {change_time:.6f}s")
        print(f"Change detection memory: {change_memory / 1024:.1f}KB")
        
        results[size] = {
            'yaml_size': len(yaml_text),
            'field_count': len(form.widgets_map),
            'load_time': load_time,
            'load_memory': load_memory,
            'generate_time': generate_time,
            'generate_memory': generate_memory,
            'change_time': change_time,
            'change_memory': change_memory
        }
    
    print(f"\n--- Performance Summary ---")
    for size, metrics in results.items():
        print(f"{size.upper()}:")
        print(f"  Fields: {metrics['field_count']}")
        print(f"  Load: {metrics['load_time']:.3f}s ({metrics['load_memory']/1024/1024:.1f}MB)")
        print(f"  Generate: {metrics['generate_time']:.3f}s")
    
    print("YAMLFormWidget performance test completed!\n")
    return results


def test_config_screen_performance():
    """Test ConfigScreenV2 performance with multiple installations."""
    print("Testing ConfigScreenV2 Performance...")
    
    app = MockApp()
    
    # Test screen initialization
    _, init_time, init_memory = measure_performance(ConfigScreenV2, app)
    
    print(f"Screen initialization time: {init_time:.3f}s")
    print(f"Screen initialization memory: {init_memory / 1024 / 1024:.1f}MB")
    
    config_screen = ConfigScreenV2(app)
    
    # Test widget building
    _, build_time, build_memory = measure_performance(config_screen.build_widget)
    
    print(f"Widget building time: {build_time:.3f}s")
    print(f"Widget building memory: {build_memory / 1024 / 1024:.1f}MB")
    
    # Test installation refresh with multiple temporary projects
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        
        # Create multiple test installations
        installations = []
        for i in range(10):
            project_path = base_path / f"project_{i}"
            project_path.mkdir()
            
            config_dir = project_path / '.claude-mpm'
            config_dir.mkdir()
            
            config = create_test_config('medium')
            config['project']['name'] = f"test-project-{i}"
            
            config_file = config_dir / 'config.yaml'
            with open(config_file, 'w') as f:
                yaml.dump(config, f)
            
            installation = Installation(
                path=project_path,
                config=config,
                name=f"project_{i}"
            )
            installations.append(installation)
        
        # Test installation loading
        config_screen.installations = installations
        
        _, update_time, update_memory = measure_performance(config_screen._update_instance_list)
        
        print(f"Instance list update time: {update_time:.3f}s")
        print(f"Instance list update memory: {update_memory / 1024 / 1024:.1f}MB")
        
        # Test installation selection
        first_installation = installations[0]
        _, select_time, select_memory = measure_performance(
            config_screen._select_installation, first_installation
        )
        
        print(f"Installation selection time: {select_time:.3f}s")
        print(f"Installation selection memory: {select_memory / 1024 / 1024:.1f}MB")
    
    print("ConfigScreenV2 performance test completed!\n")


def test_discovery_performance():
    """Test InstallationDiscovery performance."""
    print("Testing InstallationDiscovery Performance...")
    
    # Create temporary workspace with multiple projects
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        
        # Create nested project structure
        for i in range(20):
            project_path = base_path / f"workspace_{i // 5}" / f"project_{i}"
            project_path.mkdir(parents=True, exist_ok=True)
            
            # Some with .claude-mpm, some without
            if i % 3 == 0:
                config_dir = project_path / '.claude-mpm'
                config_dir.mkdir()
                
                config = create_test_config('small')
                config['project']['name'] = f"discovered-project-{i}"
                
                with open(config_dir / 'config.yaml', 'w') as f:
                    yaml.dump(config, f)
            
            # Some with git repos
            if i % 4 == 0:
                git_dir = project_path / '.git'
                git_dir.mkdir()
        
        discovery = InstallationDiscovery()
        
        # Test discovery performance
        _, discover_time, discover_memory = measure_performance(
            discovery.find_installations, 
            paths=[base_path], 
            use_cache=False
        )
        
        print(f"Discovery time: {discover_time:.3f}s")
        print(f"Discovery memory: {discover_memory / 1024 / 1024:.1f}MB")
        
        # Test with caching
        _, cached_time, cached_memory = measure_performance(
            discovery.find_installations,
            paths=[base_path],
            use_cache=True
        )
        
        print(f"Cached discovery time: {cached_time:.3f}s")
        print(f"Cached discovery memory: {cached_memory / 1024 / 1024:.1f}MB")
        print(f"Cache speedup: {discover_time / cached_time:.1f}x")
    
    print("InstallationDiscovery performance test completed!\n")


def test_memory_scaling():
    """Test memory usage scaling with multiple configurations."""
    print("Testing Memory Scaling...")
    
    process = psutil.Process(os.getpid())
    baseline_memory = process.memory_info().rss
    
    print(f"Baseline memory: {baseline_memory / 1024 / 1024:.1f}MB")
    
    # Test scaling with multiple form widgets
    forms = []
    memory_points = []
    
    for i in range(0, 51, 10):  # 0, 10, 20, 30, 40, 50
        # Add 10 more forms
        for j in range(10):
            form = YAMLFormWidget()
            config = create_test_config('medium')
            config['project']['name'] = f"scaling-test-{i}-{j}"
            form.load_yaml(yaml.dump(config))
            forms.append(form)
        
        current_memory = process.memory_info().rss
        memory_usage = current_memory - baseline_memory
        memory_points.append((len(forms), memory_usage))
        
        print(f"Forms: {len(forms):2d}, Memory: {memory_usage / 1024 / 1024:.1f}MB")
    
    # Calculate memory per form
    if len(memory_points) > 1:
        total_forms = memory_points[-1][0]
        total_memory = memory_points[-1][1]
        memory_per_form = total_memory / total_forms
        
        print(f"\nMemory per form: {memory_per_form / 1024 / 1024:.2f}MB")
        
        # Check if memory scaling is linear (within reasonable bounds)
        memory_efficiency = memory_per_form / (1024 * 1024)  # MB per form
        assert memory_efficiency < 5.0, f"Memory per form too high: {memory_efficiency:.2f}MB"
        print("✓ Memory scaling is reasonable")
    
    # Clean up
    forms.clear()
    
    print("Memory scaling test completed!\n")


def main():
    """Run all performance tests."""
    print("=== ConfigScreenV2 Performance Tests ===\n")
    
    try:
        form_results = test_form_widget_performance()
        test_config_screen_performance()
        test_discovery_performance()
        test_memory_scaling()
        
        print("=== PERFORMANCE TESTS COMPLETED ===")
        
        # Performance summary
        print(f"\nPerformance Summary:")
        print(f"  Small config load time: {form_results['small']['load_time']:.3f}s")
        print(f"  Medium config load time: {form_results['medium']['load_time']:.3f}s")
        print(f"  Large config load time: {form_results['large']['load_time']:.3f}s")
        
        # Performance assertions
        assert form_results['small']['load_time'] < 0.1, "Small config should load quickly"
        assert form_results['medium']['load_time'] < 1.0, "Medium config should load reasonably fast"
        assert form_results['large']['load_time'] < 5.0, "Large config should load within acceptable time"
        
        print(f"  ✓ All performance requirements met")
        
        return 0
        
    except Exception as e:
        print(f"=== PERFORMANCE TESTS FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())