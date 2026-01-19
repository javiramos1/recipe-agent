#!/usr/bin/env python3
"""Fix async tests to use pytest-asyncio and new_callable=AsyncMock."""

import re

def fix_test_ingredients():
    with open('tests/unit/test_ingredients.py', 'r') as f:
        content = f.read()
    
    # Import AsyncMock if not already present
    if 'from unittest.mock import AsyncMock' not in content:
        content = content.replace(
            'from unittest.mock import MagicMock, Mock, patch',
            'from unittest.mock import AsyncMock, MagicMock, Mock, patch'
        )
    
    # Fix test methods in TestExtractIngredientsPreHook
    # Add @pytest.mark.asyncio and convert to async, fix patches
    
    # Pattern 1: test_successful_extraction
    content = re.sub(
        r'(@patch\("src\.mcp_tools\.ingredients\.extract_ingredients_from_image"\))\s*'
        r'(@patch\("src\.mcp_tools\.ingredients\.fetch_image_bytes"\))\s*'
        r'(def test_successful_extraction\(self, mock_fetch, mock_extract\):)',
        r'@pytest.mark.asyncio\n    @patch("src.mcp_tools.ingredients.fetch_image_bytes", new_callable=AsyncMock)\n    '
        r'@patch("src.mcp_tools.ingredients.extract_ingredients_from_image", new_callable=AsyncMock)\n    '
        r'async def test_successful_extraction(self, mock_extract, mock_fetch):',
        content
    )
    
    # Add await calls
    content = re.sub(
        r'extract_ingredients_pre_hook\(run_input\)(?!\s*await)',
        r'await extract_ingredients_pre_hook(run_input)',
        content
    )
    
    with open('tests/unit/test_ingredients.py', 'w') as f:
        f.write(content)
    
    print("Fixed test_ingredients.py")

def fix_test_mcp():
    with open('tests/unit/test_mcp.py', 'r') as f:
        content = f.read()
    
    # Import AsyncMock if not already present
    if 'from unittest.mock import AsyncMock' not in content:
        content = content.replace(
            'from unittest.mock import Mock, patch, MagicMock',
            'from unittest.mock import AsyncMock, Mock, patch, MagicMock'
        )
    
    # Add @pytest.mark.asyncio to async test functions
    content = re.sub(
        r'(    )(async def test_initialize)',
        r'\1@pytest.mark.asyncio\n\1\2',
        content
    )
    
    # Fix patch decorators with new_callable
    content = re.sub(
        r'@patch\("src\.mcp_tools\.spoonacular\.asyncio\.to_thread"\)(\s*@patch\("src\.mcp_tools\.spoonacular\.asyncio\.sleep"\))?\s*'
        r'async def test_initialize_success\(self, mock_to_thread, mock_mcp: Mock\)',
        r'@patch("src.mcp_tools.spoonacular.MCPTools")\n    @patch("src.mcp_tools.spoonacular.asyncio.to_thread", new_callable=AsyncMock)\n    '
        r'async def test_initialize_success(self, mock_to_thread, mock_mcp: Mock)',
        content
    )
    
    content = re.sub(
        r'@patch\("src\.mcp_tools\.spoonacular\.asyncio\.sleep"\)\s*'
        r'@patch\("src\.mcp_tools\.spoonacular\.asyncio\.to_thread"\)\s*'
        r'async def test_initialize_with_retries\(self, mock_to_thread: Mock, mock_sleep: Mock\)',
        r'@patch("src.mcp_tools.spoonacular.asyncio.sleep", new_callable=AsyncMock)\n    @patch("src.mcp_tools.spoonacular.asyncio.to_thread", new_callable=AsyncMock)\n    '
        r'async def test_initialize_with_retries(self, mock_to_thread: Mock, mock_sleep: Mock)',
        content
    )
    
    with open('tests/unit/test_mcp.py', 'w') as f:
        f.write(content)
    
    print("Fixed test_mcp.py")

if __name__ == '__main__':
    fix_test_ingredients()
    fix_test_mcp()
