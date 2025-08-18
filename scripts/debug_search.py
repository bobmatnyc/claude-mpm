#!/usr/bin/env python3
"""
Debug script to test MCP Vector Search functionality.
"""

import sys
import os
from pathlib import Path

# Add the mcp-vector-search source to Python path
MCP_VECTOR_SEARCH_ROOT = "/Users/masa/Projects/managed/mcp-vector-search"
sys.path.insert(0, os.path.join(MCP_VECTOR_SEARCH_ROOT, "src"))

# Set up environment
os.environ["VIRTUAL_ENV"] = os.path.join(MCP_VECTOR_SEARCH_ROOT, ".venv")
os.environ["PATH"] = f"{os.path.join(MCP_VECTOR_SEARCH_ROOT, '.venv', 'bin')}:{os.environ.get('PATH', '')}"

async def debug_search():
    """Debug the search functionality step by step."""
    try:
        from mcp_vector_search.core.factory import ComponentFactory
        from mcp_vector_search.core.project import ProjectManager
        
        print("🔍 Starting search debug...")
        
        # Load project
        project_root = Path("/Users/masa/Projects/claude-mpm")
        print(f"📁 Project root: {project_root}")
        
        # Check if project is initialized
        project_manager = ProjectManager(project_root)
        if not project_manager.is_initialized():
            print("❌ Project not initialized!")
            return
        
        print("✅ Project is initialized")
        
        # Load configuration
        config = project_manager.load_config()
        print(f"⚙️  Config loaded: {config.embedding_model}")
        
        # Create components
        print("🔧 Creating components...")
        components = await ComponentFactory.create_standard_components(
            project_root=project_root,
            use_pooling=False,
            include_search_engine=True,
            include_auto_indexer=False,
        )
        
        search_engine = components.search_engine
        database = components.database
        
        print("✅ Components created")
        
        # Test database connection
        print("🔌 Testing database connection...")
        stats = await database.get_stats()
        print(f"📊 Database stats: {stats}")
        
        # Test embedding generation
        print("🧠 Testing embedding generation...")
        test_query = "function"
        
        # Get embedding function
        embedding_function = components.embedding_function
        print(f"🔧 Embedding function: {type(embedding_function)}")
        
        # Generate embedding for test query
        try:
            query_embedding = embedding_function([test_query])
            print(f"✅ Generated embedding for '{test_query}': shape={len(query_embedding[0]) if query_embedding else 'None'}")
        except Exception as e:
            print(f"❌ Failed to generate embedding: {e}")
            return
        
        # Test direct database search
        print("🔍 Testing direct database search...")
        try:
            results = await database.search(
                query_text=test_query,
                limit=5,
                threshold=0.0
            )
            print(f"📊 Direct database search results: {len(results)} results")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. {result.file_path}:{result.start_line} (score: {result.similarity_score:.3f})")
        except Exception as e:
            print(f"❌ Direct database search failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Test search engine
        print("🔍 Testing search engine...")
        try:
            search_results = await search_engine.search(
                query=test_query,
                limit=5,
                threshold=0.0
            )
            print(f"📊 Search engine results: {len(search_results)} results")
            for i, result in enumerate(search_results[:3]):
                print(f"  {i+1}. {result.file_path}:{result.start_line} (score: {result.similarity_score:.3f})")
        except Exception as e:
            print(f"❌ Search engine failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Clean up
        await database.close()
        print("✅ Debug completed")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_search())
