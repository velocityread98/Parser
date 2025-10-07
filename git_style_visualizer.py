#!/usr/bin/env python3
"""
Git-style Graph Visualization for Document Hierarchy
Creates a visual tree representation similar to git history with branching lines.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class VisualizationNode:
    """Node for visualization with git-style branching info."""
    id: str
    label: str
    text: str
    level: int
    page: int
    children: List['VisualizationNode']
    content_elements: List['VisualizationNode']
    is_merged: bool = False
    merged_count: int = 0


def create_git_style_visualization(hierarchy_file: str) -> str:
    """Create a git-style branching visualization of the document hierarchy."""
    
    with open(hierarchy_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert JSON to visualization nodes
    root = convert_to_viz_node(data)
    
    # Generate the git-style visualization
    lines = []
    generate_git_lines(root, lines, [], True, is_root=True)
    
    return '\n'.join(lines)


def convert_to_viz_node(json_node: Dict[str, Any]) -> VisualizationNode:
    """Convert JSON node to visualization node."""
    children = [convert_to_viz_node(child) for child in json_node.get('children', [])]
    content = [convert_to_viz_node(content) for content in json_node.get('content_elements', [])]
    
    return VisualizationNode(
        id=json_node.get('id', ''),
        label=json_node.get('label', ''),
        text=json_node.get('text', ''),
        level=json_node.get('level', -1),
        page=json_node.get('page', 0),
        children=children,
        content_elements=content,
        is_merged=json_node.get('is_merged', False),
        merged_count=len(json_node.get('merged_elements', []))
    )


def generate_git_lines(node: VisualizationNode, lines: List[str], prefix: List[str], 
                      is_last: bool, is_root: bool = False, show_content: bool = True):
    """Generate git-style lines with branching."""
    
    # Determine the icon and styling
    icon_map = {
        'title': '📖',
        'document': '📚', 
        'sec': '📑',
        'sub_sec': '📝',
        'sub_sub_sec': '•',
        'para': '¶',
        'figure': '🖼️',
        'table': '📊',
        'list_group': '📋',
        'author': '👤',
        'fnote': '📌',
        'foot': '👇'
    }
    
    # Handle dynamic sub-section icons
    if node.label.startswith('sub_'):
        sub_count = node.label.count('sub_')
        icons = ['📝', '•', '◦', '‣', '▪', '▫']
        icon = icons[min(sub_count - 1, len(icons) - 1)]
    else:
        icon = icon_map.get(node.label, '?')
    
    # Create the current line
    if is_root:
        branch_chars = ""
    else:
        branch_chars = ''.join(prefix)
        if is_last:
            branch_chars += "└─ "
        else:
            branch_chars += "├─ "
    
    # Format node text
    text = node.text[:60] + ('...' if len(node.text) > 60 else '')
    merge_info = f" [MERGED×{node.merged_count}]" if node.is_merged else ""
    page_info = f" (p.{node.page})" if node.page > 0 else ""
    
    # Add the line
    if node.label in ['title', 'document', 'sec'] or node.label.startswith('sub_'):
        # Structural nodes in bold/highlighted style
        line = f"{branch_chars}{icon} {text}{page_info}{merge_info}"
        lines.append(line)
    else:
        # Content nodes in lighter style
        line = f"{branch_chars}  {icon} {text}{merge_info}"
        lines.append(line)
    
    # Process children (structural elements)
    total_children = len(node.children)
    for i, child in enumerate(node.children):
        is_child_last = (i == total_children - 1) and (not show_content or len(node.content_elements) == 0)
        
        # Update prefix for child
        new_prefix = prefix.copy()
        if not is_root:
            if is_last:
                new_prefix.append("   ")  # Empty space under last item
            else:
                new_prefix.append("│  ")  # Continuation line
        
        generate_git_lines(child, lines, new_prefix, is_child_last)
    
    # Process content elements (leaf nodes) - but limit them to avoid clutter
    if show_content and node.content_elements:
        content_to_show = node.content_elements[:8]  # Limit to first 8 content elements
        total_content = len(content_to_show)
        
        for i, content in enumerate(content_to_show):
            is_content_last = (i == total_content - 1)
            
            # Update prefix for content
            new_prefix = prefix.copy()
            if not is_root:
                if is_last and len(node.children) == 0:
                    new_prefix.append("   ")  # Empty space under last item
                else:
                    new_prefix.append("│  ")  # Continuation line
            
            generate_git_lines(content, lines, new_prefix, is_content_last, show_content=False)
        
        # Show summary if there are more content elements
        if len(node.content_elements) > 8:
            remaining = len(node.content_elements) - 8
            branch_chars = ''.join(new_prefix) + "└─ "
            lines.append(f"{branch_chars}  📄 ... and {remaining} more content elements")


def create_compact_git_visualization(hierarchy_file: str) -> str:
    """Create a compact git-style visualization showing only structural elements."""
    
    with open(hierarchy_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    root = convert_to_viz_node(data)
    
    lines = []
    generate_compact_git_lines(root, lines, [], True, is_root=True)
    
    return '\n'.join(lines)


def generate_compact_git_lines(node: VisualizationNode, lines: List[str], prefix: List[str], 
                             is_last: bool, is_root: bool = False):
    """Generate compact git-style lines showing only structure + content count."""
    
    # Only show structural nodes
    if not (node.label in ['title', 'document', 'sec'] or node.label.startswith('sub_')):
        return
    
    icon_map = {
        'title': '📖',
        'document': '📚', 
        'sec': '📑',
        'sub_sec': '📝',
        'sub_sub_sec': '•',
    }
    
    if node.label.startswith('sub_'):
        sub_count = node.label.count('sub_')
        icons = ['📝', '•', '◦', '‣', '▪', '▫']
        icon = icons[min(sub_count - 1, len(icons) - 1)]
    else:
        icon = icon_map.get(node.label, '?')
    
    # Create the current line
    if is_root:
        branch_chars = ""
    else:
        branch_chars = ''.join(prefix)
        if is_last:
            branch_chars += "└─ "
        else:
            branch_chars += "├─ "
    
    # Format node info
    text = node.text[:50] + ('...' if len(node.text) > 50 else '')
    content_count = len(node.content_elements)
    content_info = f" [{content_count} items]" if content_count > 0 else ""
    page_info = f" (p.{node.page})" if node.page > 0 else ""
    
    line = f"{branch_chars}{icon} {text}{page_info}{content_info}"
    lines.append(line)
    
    # Process children
    structural_children = [child for child in node.children 
                          if child.label in ['title', 'document', 'sec'] or child.label.startswith('sub_')]
    
    total_children = len(structural_children)
    for i, child in enumerate(structural_children):
        is_child_last = (i == total_children - 1)
        
        # Update prefix for child
        new_prefix = prefix.copy()
        if not is_root:
            if is_last:
                new_prefix.append("   ")
            else:
                new_prefix.append("│  ")
        
        generate_compact_git_lines(child, lines, new_prefix, is_child_last)


def create_horizontal_flow_visualization(hierarchy_file: str) -> str:
    """Create a horizontal flow visualization showing the document flow."""
    
    with open(hierarchy_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    root = convert_to_viz_node(data)
    
    lines = []
    lines.append("DOCUMENT FLOW VISUALIZATION")
    lines.append("=" * 80)
    lines.append("")
    
    # Show the flow horizontally
    generate_flow_lines(root, lines, 0)
    
    return '\n'.join(lines)


def generate_flow_lines(node: VisualizationNode, lines: List[str], depth: int):
    """Generate horizontal flow lines."""
    
    indent = "  " * depth
    arrow = "→ " if depth > 0 else ""
    
    # Icon mapping
    icon_map = {
        'title': '📖',
        'sec': '📑',
        'sub_sec': '📝',
        'sub_sub_sec': '•',
        'para': '¶',
        'figure': '🖼️',
        'table': '📊',
        'list_group': '📋',
    }
    
    if node.label.startswith('sub_'):
        sub_count = node.label.count('sub_')
        icons = ['📝', '•', '◦', '‣']
        icon = icons[min(sub_count - 1, len(icons) - 1)]
    else:
        icon = icon_map.get(node.label, '?')
    
    # Only show structural elements in flow
    if node.label in ['title', 'document', 'sec'] or node.label.startswith('sub_'):
        text = node.text[:40] + ('...' if len(node.text) > 40 else '')
        content_count = len(node.content_elements)
        content_info = f" ({content_count} items)" if content_count > 0 else ""
        
        lines.append(f"{indent}{arrow}{icon} {text}{content_info}")
        
        # Show children
        for child in node.children:
            generate_flow_lines(child, lines, depth + 1)


def main():
    """Main function to create git-style visualizations."""
    hierarchy_file = "enhanced_document_hierarchy.json"
    
    try:
        print("Creating git-style document hierarchy visualizations...")
        print("\n" + "=" * 80)
        print("GIT-STYLE DOCUMENT HIERARCHY (Full Detail)")
        print("=" * 80)
        
        # Full detailed visualization
        full_viz = create_git_style_visualization(hierarchy_file)
        print(full_viz)
        
        print("\n" + "=" * 80)
        print("GIT-STYLE DOCUMENT HIERARCHY (Compact - Structure Only)")
        print("=" * 80)
        
        # Compact visualization
        compact_viz = create_compact_git_visualization(hierarchy_file)
        print(compact_viz)
        
        print("\n" + "=" * 80)
        print("HORIZONTAL FLOW VISUALIZATION")
        print("=" * 80)
        
        # Flow visualization
        flow_viz = create_horizontal_flow_visualization(hierarchy_file)
        print(flow_viz)
        
        # Save visualizations to files
        with open('git_style_hierarchy_full.txt', 'w', encoding='utf-8') as f:
            f.write("GIT-STYLE DOCUMENT HIERARCHY (Full Detail)\n")
            f.write("=" * 50 + "\n\n")
            f.write(full_viz)
        
        with open('git_style_hierarchy_compact.txt', 'w', encoding='utf-8') as f:
            f.write("GIT-STYLE DOCUMENT HIERARCHY (Compact)\n")
            f.write("=" * 50 + "\n\n")
            f.write(compact_viz)
        
        with open('document_flow_visualization.txt', 'w', encoding='utf-8') as f:
            f.write(flow_viz)
        
        print(f"\n💾 Visualizations saved to:")
        print(f"   - git_style_hierarchy_full.txt")
        print(f"   - git_style_hierarchy_compact.txt")
        print(f"   - document_flow_visualization.txt")
        
    except FileNotFoundError:
        print(f"❌ Error: {hierarchy_file} not found.")
        print("Please run enhanced_hierarchy_builder.py first.")
    except Exception as e:
        print(f"❌ Error creating visualization: {e}")


if __name__ == "__main__":
    main()