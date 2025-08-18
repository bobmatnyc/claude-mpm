#!/usr/bin/env python3
"""
Detailed debug script to test ChromaDB query directly.
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

async def debug_chroma_query():
    """Debug ChromaDB query directly."""
    try:
        from mcp_vector_search.core.factory import ComponentFactory, DatabaseContext
        from mcp_vector_search.core.project import ProjectManager
        
        print("🔍 Starting detailed ChromaDB debug...")
        
        # Load project
        project_root = Path("/Users/masa/Projects/claude-mpm")
        print(f"📁 Project root: {project_root}")
        
        # Create components
        components = await ComponentFactory.create_standard_components(
            project_root=project_root,
            use_pooling=False,
            include_search_engine=False,
            include_auto_indexer=False,
        )
        
        async with DatabaseContext(components.database) as db:
            print("✅ Database initialized")
            
            # Get the ChromaDB collection directly
            collection = db._collection
            print(f"🔧 Collection: {collection}")
            print(f"🔧 Collection name: {collection.name}")
            
            # Test direct ChromaDB query
            print("🔍 Testing direct ChromaDB query...")
            test_query = "function"
            
            try:
                # Direct ChromaDB query
                raw_results = collection.query(
                    query_texts=[test_query],
                    n_results=10,
                    include=["documents", "metadatas", "distances"],
                )
                
                print(f"📊 Raw ChromaDB results:")
                print(f"  Documents: {len(raw_results.get('documents', [[]])[0]) if raw_results.get('documents') else 0}")
                print(f"  Metadatas: {len(raw_results.get('metadatas', [[]])[0]) if raw_results.get('metadatas') else 0}")
                print(f"  Distances: {len(raw_results.get('distances', [[]])[0]) if raw_results.get('distances') else 0}")
                
                if raw_results.get('documents') and raw_results['documents'][0]:
                    print(f"📋 First few results:")
                    for i, (doc, metadata, distance) in enumerate(zip(
                        raw_results['documents'][0][:3],
                        raw_results['metadatas'][0][:3],
                        raw_results['distances'][0][:3]
                    )):
                        similarity = 1.0 - distance
                        print(f"  {i+1}. Distance: {distance:.4f}, Similarity: {similarity:.4f}")
                        print(f"      File: {metadata.get('file_path', 'unknown')}")
                        print(f"      Content: {doc[:100]}...")
                        print()
                else:
                    print("❌ No documents returned from ChromaDB query")
                
                # Test with different similarity thresholds
                print("🔍 Testing with different similarity thresholds...")
                for threshold in [0.0, 0.1, 0.3, 0.5, 0.7, 0.9]:
                    results = await db.search(
                        query=test_query,
                        limit=5,
                        similarity_threshold=threshold
                    )
                    print(f"  Threshold {threshold:.1f}: {len(results)} results")
                
                # Test with different queries
                print("🔍 Testing with different queries...")
                test_queries = ["def", "class", "import", "python", "code", "test"]
                for query in test_queries:
                    results = await db.search(
                        query=query,
                        limit=3,
                        similarity_threshold=0.0
                    )
                    print(f"  Query '{query}': {len(results)} results")
                
            except Exception as e:
                print(f"❌ Direct ChromaDB query failed: {e}")
                import traceback
                traceback.print_exc()
        
        print("✅ Detailed debug completed!")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_chroma_query())
