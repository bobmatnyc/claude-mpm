# Super simple, direct directory listing - no complexity
import os
from pathlib import Path
from aiohttp import web
import json
import datetime

async def list_directory(request):
    """Dead simple directory listing - just return what's there"""
    path = request.query.get('path', '.')
    
    # Convert to absolute path
    abs_path = os.path.abspath(os.path.expanduser(path))
    
    result = {
        'path': abs_path,
        'exists': os.path.exists(abs_path),
        'is_directory': os.path.isdir(abs_path),
        'contents': []
    }
    
    if result['exists'] and result['is_directory']:
        try:
            # Just list everything, no filtering
            items = os.listdir(abs_path)
            for item in items:
                item_path = os.path.join(abs_path, item)
                result['contents'].append({
                    'name': item,
                    'path': item_path,
                    'is_directory': os.path.isdir(item_path),
                    'is_file': os.path.isfile(item_path)
                })
            # Sort directories first, then files, both alphabetically
            result['contents'].sort(key=lambda x: (not x['is_directory'], x['name'].lower()))
        except Exception as e:
            result['error'] = str(e)
    
    return web.json_response(result)

def register_routes(app):
    """Register simple directory routes with the aiohttp app"""
    app.router.add_get('/api/directory/list', list_directory)