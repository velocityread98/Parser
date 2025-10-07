#!/usr/bin/env python3
"""
Enhanced Document Hierarchy Builder
Creates a hierarchical graph structure with unlimited nesting depth and merged elements.
Includes summary generation using OpenAI API and embeddings support.
"""

import json
import re
import os
import sys
import argparse
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
# load_dotenv()

# Initialize OpenAI client
if os.getenv("OPENAI_API_KEY"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@dataclass
class EnhancedDocumentNode:
    """Enhanced node in the document hierarchy with merging capabilities and summary support."""
    id: str
    label: str
    text: str
    level: int
    page: int
    reading_order: int
    bbox: Optional[List[int]] = None
    summary: Optional[str] = None
    embeddings: List[float] = field(default_factory=list)
    merged_elements: List[Dict[str, Any]] = field(default_factory=list)
    parent: Optional['EnhancedDocumentNode'] = None
    children: List['EnhancedDocumentNode'] = field(default_factory=list)
    content_elements: List['EnhancedDocumentNode'] = field(default_factory=list)
    
    def add_child(self, child: 'EnhancedDocumentNode'):
        """Add a child node to this node."""
        child.parent = self
        self.children.append(child)
    
    def add_content(self, content: 'EnhancedDocumentNode'):
        """Add content element to this node."""
        content.parent = self
        self.content_elements.append(content)
    
    def merge_with(self, other: 'EnhancedDocumentNode'):
        """Merge another node into this node."""
        if not self.merged_elements:
            # Add self as first merged element
            self.merged_elements.append({
                'label': self.label,
                'text': self.text,
                'bbox': self.bbox,
                'page': self.page,
                'reading_order': self.reading_order
            })
        
        # Add the other node
        self.merged_elements.append({
            'label': other.label,
            'text': other.text,
            'bbox': other.bbox,
            'page': other.page,
            'reading_order': other.reading_order
        })
        
        # Update combined text
        if self.label == 'fig' and other.label == 'cap':
            self.text = f"{other.text} [IMAGE: {self.text}]"
            self.label = 'figure'
        elif self.label == 'tab' and other.label == 'cap':
            self.text = f"{other.text} [TABLE: {self.text}]"
            self.label = 'table'
        elif self.label == 'list':
            self.text = f"{self.text}\n{other.text}"
            self.label = 'list_group'
    
    def get_section_number(self) -> Optional[str]:
        """Extract section number from text if present."""
        match = re.match(r'^(\d+(?:\.\d+)*)', self.text.strip())
        return match.group(1) if match else None
    
    def determine_nesting_level(self) -> int:
        """Determine nesting level from label dynamically."""
        if self.label == 'title':
            return 0
        elif self.label == 'sec':
            return 1
        elif self.label.startswith('sub_'):
            # Count the number of 'sub_' prefixes for unlimited depth
            sub_count = self.label.count('sub_')
            return sub_count + 1
        else:
            return -1  # Content element
    
    def is_structural(self) -> bool:
        """Check if this node represents document structure."""
        return (self.label in ['title', 'sec'] or 
                self.label.startswith('sub_') or
                self.label == 'document')
    
    def is_content(self) -> bool:
        """Check if this node represents content."""
        return self.label in ['para', 'list', 'list_group', 'figure', 'table', 
                             'cap', 'fig', 'tab', 'fnote', 'foot', 'author']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for JSON serialization."""
        result = {
            'id': self.id,
            'label': self.label,
            'text': self.text,  # Keep full text, no truncation
            'level': self.level,
            'page': self.page,
            'reading_order': self.reading_order,
            'bbox': self.bbox,
            'section_number': self.get_section_number(),
            'summary': self.summary,
            'embeddings': self.embeddings,
            'children': [child.to_dict() for child in self.children],
            'content_elements': [content.to_dict() for content in self.content_elements]
        }
        
        if self.merged_elements:
            result['merged_elements'] = self.merged_elements
            result['is_merged'] = True
        
        return result


class EnhancedDocumentHierarchyBuilder:
    """Enhanced builder with unlimited depth, element merging, and AI-powered summaries."""
    
    def __init__(self):
        self.nodes: List[EnhancedDocumentNode] = []
    
    def generate_leaf_summary(self, node: EnhancedDocumentNode) -> str:
        """Generate summary for leaf nodes (content elements) using OpenAI."""
        try:
            prompt = f"""
            Summarize the following text content from a document. Be comprehensive but concise, 
            capturing all important details as this will be used for answering questions later. 
            
            Content type: {node.label}
            Text: {node.text}
            
            Provide a detailed but brief summary:
            """
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            content = response.choices[0].message.content if response.choices and response.choices[0].message else ""
            return (content or "").strip()
        except Exception as e:
            print(f"Warning: Failed to generate summary for {node.id}: {e}")
            return f"Summary unavailable for {node.label}: {node.text[:100]}..."
    
    def generate_section_summary(self, node: EnhancedDocumentNode) -> str:
        """Generate summary for non-leaf nodes (sections) including children summaries."""
        try:
            # Collect text from node itself
            node_text = node.text if node.text.strip() else ""
            
            # Collect text from content_elements
            content_texts = []
            for content in node.content_elements:
                if content.summary:
                    content_texts.append(f"- {content.label}: {content.summary}")
                else:
                    content_texts.append(f"- {content.label}: {content.text[:200]}...")
            
            # Collect summaries from child sections
            child_summaries = []
            for child in node.children:
                if child.summary:
                    child_summaries.append(f"- Section '{child.text}': {child.summary}")
            
            # Build comprehensive prompt
            prompt_parts = [
                f"Summarize this document section comprehensively. Capture all important information",
                f"as this will be used for answering questions later. Be detailed but concise.",
                f"",
                f"Section: {node.label} - {node_text}" if node_text else f"Section: {node.label}",
            ]
            
            if content_texts:
                prompt_parts.extend([
                    "",
                    "Content elements in this section:",
                    "\n".join(content_texts)
                ])
            
            if child_summaries:
                prompt_parts.extend([
                    "",
                    "Subsections:",
                    "\n".join(child_summaries)
                ])
            
            prompt_parts.extend([
                "",
                "Provide a comprehensive summary that captures:",
                "1. Main concepts and themes",
                "2. Key technical details and findings", 
                "3. Important relationships and context",
                "4. Specific data, numbers, or examples mentioned",
                "",
                "Summary:"
            ])
            
            prompt = "\n".join(prompt_parts)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            content = response.choices[0].message.content if response.choices and response.choices[0].message else ""
            return (content or "").strip()
        except Exception as e:
            print(f"Warning: Failed to generate summary for section {node.id}: {e}")
            return f"Summary unavailable for section {node.label}"
    
    def generate_summaries_recursive(self, node: EnhancedDocumentNode):
        """Recursively generate summaries for all nodes in the hierarchy."""
        print(f"Generating summary for: {node.label} - {node.text[:50]}...")
        
        # First, generate summaries for all children (bottom-up approach)
        for child in node.children:
            self.generate_summaries_recursive(child)
        
        # Generate summaries for content elements (leaf nodes)
        for content in node.content_elements:
            if not content.summary:
                content.summary = self.generate_leaf_summary(content)
        
        # Generate summary for this node if it's structural or has content
        if (node.is_structural() or node.label == 'document') and not node.summary:
            node.summary = self.generate_section_summary(node)
        
    def determine_node_level_dynamic(self, element: Dict[str, Any]) -> int:
        """Dynamically determine hierarchical level for unlimited depth."""
        label = element.get('label', '')
        text = element.get('text', '').strip()
        
        if label == 'title':
            return 0
        elif label == 'sec':
            return 1
        elif label.startswith('sub_'):
            # Handle unlimited depth: sub_sec=2, sub_sub_sec=3, sub_sub_sub_sec=4, etc.
            sub_count = label.count('sub_')
            return sub_count + 1
        else:
            return -1  # Content elements
    
    def create_node_from_element(self, element: Dict[str, Any], page_num: int) -> EnhancedDocumentNode:
        """Create an EnhancedDocumentNode from a JSON element."""
        node_id = f"page_{page_num}_order_{element.get('reading_order', 0)}"
        level = self.determine_node_level_dynamic(element)
        
        return EnhancedDocumentNode(
            id=node_id,
            label=element.get('label', ''),
            text=element.get('text', ''),
            level=level,
            page=page_num,
            reading_order=element.get('reading_order', 0),
            bbox=element.get('bbox')
        )
    
    def merge_figure_caption_pairs(self, elements: List[EnhancedDocumentNode]) -> List[EnhancedDocumentNode]:
        """Merge fig+cap and tab+cap pairs into single nodes."""
        merged_elements = []
        i = 0
        
        while i < len(elements):
            current = elements[i]
            
            # Check if current is fig/tab and next is cap
            if (i + 1 < len(elements) and 
                current.label in ['fig', 'tab'] and 
                elements[i + 1].label == 'cap' and
                current.page == elements[i + 1].page):
                
                # Merge fig/tab with caption
                current.merge_with(elements[i + 1])
                merged_elements.append(current)
                i += 2  # Skip both elements
            else:
                merged_elements.append(current)
                i += 1
        
        return merged_elements
    
    def merge_consecutive_lists(self, elements: List[EnhancedDocumentNode]) -> List[EnhancedDocumentNode]:
        """Merge consecutive list elements into single nodes."""
        merged_elements = []
        i = 0
        
        while i < len(elements):
            current = elements[i]
            
            if current.label == 'list':
                # Start a list group
                list_group = current
                j = i + 1
                
                # Find consecutive lists on same page
                while (j < len(elements) and 
                       elements[j].label == 'list' and
                       elements[j].page == current.page and
                       elements[j].reading_order == elements[j-1].reading_order + 1):
                    list_group.merge_with(elements[j])
                    j += 1
                
                merged_elements.append(list_group)
                i = j
            else:
                merged_elements.append(current)
                i += 1
        
        return merged_elements
    
    def build_enhanced_hierarchy(self, json_data: Dict[str, Any], enable_summaries: bool = True) -> EnhancedDocumentNode:
        """Build the complete enhanced document hierarchy."""
        # Create all nodes first
        all_elements = []
        for page in json_data.get('pages', []):
            page_num = page.get('page_number', 0)
            for element in page.get('elements', []):
                node = self.create_node_from_element(element, page_num)
                all_elements.append(node)
        
        # Sort by page and reading order
        all_elements.sort(key=lambda x: (x.page, x.reading_order))
        
        # Separate structural and content nodes
        structural_nodes = [node for node in all_elements if node.is_structural()]
        content_nodes = [node for node in all_elements if node.is_content()]
        
        # Apply merging strategies to content nodes
        print("Merging figure-caption pairs...")
        content_nodes = self.merge_figure_caption_pairs(content_nodes)
        
        print("Merging consecutive lists...")
        content_nodes = self.merge_consecutive_lists(content_nodes)
        
        # Create document root
        doc_title = next((node for node in structural_nodes if node.label == 'title'), None)
        if doc_title:
            root = doc_title
            structural_nodes.remove(doc_title)
        else:
            root = EnhancedDocumentNode(
                id="document_root",
                label="document",
                text="Document Root",
                level=-1,
                page=0,
                reading_order=-1
            )
        
        # Build structural hierarchy with unlimited depth
        print("Building structural hierarchy...")
        self._build_unlimited_depth_hierarchy(root, structural_nodes)
        
        # Assign content to appropriate structural nodes (as leaf nodes)
        print("Assigning content as leaf nodes...")
        self._assign_content_as_leaf_nodes(root, content_nodes)
        
        # Generate summaries for the entire hierarchy
        if enable_summaries:
            print("Generating AI summaries for all nodes...")
            self.generate_summaries_recursive(root)
        else:
            print("Skipping AI summaries (disabled).")
        
        return root
    
    def _build_unlimited_depth_hierarchy(self, root: EnhancedDocumentNode, structural_nodes: List[EnhancedDocumentNode]):
        """Build hierarchy with unlimited depth support."""
        # Use a dictionary to track the current parent at each level
        level_parents = {0: root}  # level -> current parent node at that level
        
        for node in structural_nodes:
            if node.level <= 0:
                continue
            
            # Find the parent for this level
            parent_level = node.level - 1
            
            # Find the most recent parent at the appropriate level
            while parent_level >= 0 and parent_level not in level_parents:
                parent_level -= 1
            
            if parent_level >= 0:
                parent = level_parents[parent_level]
            else:
                parent = root
            
            parent.add_child(node)
            
            # Update the level_parents dictionary
            level_parents[node.level] = node
            
            # Clear deeper levels as they're no longer valid
            keys_to_remove = [k for k in level_parents.keys() if k > node.level]
            for k in keys_to_remove:
                del level_parents[k]
    
    def _assign_content_as_leaf_nodes(self, root: EnhancedDocumentNode, content_nodes: List[EnhancedDocumentNode]):
        """Assign all content elements as leaf nodes to their appropriate structural parents."""
        # Get all structural nodes in order
        all_structural = []
        self._collect_structural_nodes(root, all_structural)
        all_structural.sort(key=lambda x: (x.page, x.reading_order))
        
        for content_node in content_nodes:
            # Find the most recent structural node before this content
            best_parent = root
            for structural_node in all_structural:
                if (structural_node.page < content_node.page or 
                    (structural_node.page == content_node.page and 
                     structural_node.reading_order < content_node.reading_order)):
                    best_parent = structural_node
                else:
                    break
            
            best_parent.add_content(content_node)
    
    def _collect_structural_nodes(self, node: EnhancedDocumentNode, collection: List[EnhancedDocumentNode]):
        """Recursively collect all structural nodes."""
        if node.is_structural() or node.label == 'document':
            collection.append(node)
        for child in node.children:
            self._collect_structural_nodes(child, collection)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Enhanced Document Hierarchy Builder with AI summaries",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--no-summaries",
        action="store_true",
        help="Skip AI summary generation using OpenAI API"
    )
    
    parser.add_argument(
        "--json-file",
        type=str,
        help="Path to JSON file to process (auto-detected if not specified)"
    )
    
    return parser.parse_args()


def visualize_enhanced_hierarchy(node: EnhancedDocumentNode, indent: int = 0, max_text_length: int = 80) -> str:
    """Create a text visualization of the enhanced document hierarchy."""
    result = []
    indent_str = "  " * indent
    
    # Enhanced icon mapping
    icon_map = {
        'title': '📖',
        'document': '📚',
        'sec': '📑',
        'sub_sec': '📝',
        'sub_sub_sec': '•',
        'sub_sub_sub_sec': '◦',
        'sub_sub_sub_sub_sec': '‣',
        'para': '¶',
        'figure': '🖼️',  # merged fig+cap
        'table': '📊',   # merged tab+cap
        'list_group': '📋', # merged consecutive lists
        'fig': '🖼️',
        'tab': '📊',
        'cap': '💬',
        'list': '•',
        'fnote': '📌',
        'foot': '👇',
        'author': '👤'
    }
    
    # Determine icon
    if node.label.startswith('sub_'):
        # Dynamic icons for unlimited sub levels
        sub_count = node.label.count('sub_')
        icons = ['📝', '•', '◦', '‣', '▪', '▫', '‣', '◊']
        icon = icons[min(sub_count - 1, len(icons) - 1)]
    else:
        icon = icon_map.get(node.label, '?')
    
    text = node.text[:max_text_length] + ('...' if len(node.text) > max_text_length else '')
    
    if node.is_structural() or node.label == 'document':
        # Show structural node
        merge_info = f" [MERGED: {len(node.merged_elements)} elements]" if node.merged_elements else ""
        result.append(f"{indent_str}{icon} [{node.label}] {text} (Page {node.page}){merge_info}")
        
        # Show children (structural elements)
        for child in node.children:
            result.append(visualize_enhanced_hierarchy(child, indent + 1, max_text_length))
        
        # Show content elements (leaf nodes)
        if node.content_elements:
            content_indent = indent + 1
            content_indent_str = "  " * content_indent
            for content in node.content_elements:
                content_icon = icon_map.get(content.label, '?')
                content_text = content.text[:50] + ('...' if len(content.text) > 50 else '')
                merge_info = f" [MERGED: {len(content.merged_elements)}]" if content.merged_elements else ""
                result.append(f"{content_indent_str}  {content_icon} {content_text}{merge_info}")
    
    return "\n".join(result)


def main():
    """Main function to build and display the enhanced hierarchy with AI summaries."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Auto-detect a single JSON file from the recognition_json directory (or current dir as fallback)
    def find_single_json_file(search_dir: str) -> Optional[str]:
        try:
            if not os.path.isdir(search_dir):
                return None
            candidates = [
                os.path.join(search_dir, f)
                for f in os.listdir(search_dir)
                if f.lower().endswith(".json") and os.path.isfile(os.path.join(search_dir, f))
            ]
            return candidates[0] if len(candidates) == 1 else None
        except Exception:
            return None

    # Determine JSON file path
    if args.json_file:
        json_file_path = args.json_file
        if not os.path.isfile(json_file_path):
            print(f"❌ Error: Specified JSON file not found: {json_file_path}")
            sys.exit(1)
    else:
        # Priority: single file in recognition_json > single file in CWD
        json_file_path = find_single_json_file("./recognition_json")
        if not json_file_path:
            print("❌ Error: No JSON file found. Please specify one with --json-file")
            sys.exit(1)
    
    # Determine if summaries should be enabled
    summaries_enabled = True
    
    # Check command line argument first
    if args.no_summaries:
        print("🚫 Summaries disabled via command line argument.")
        summaries_enabled = False
    # Then check if OpenAI API key is set (only if summaries weren't explicitly disabled)
    elif not os.getenv("OPENAI_API_KEY"):
        print("⚠️ Warning: OPENAI_API_KEY not found! Summaries will be skipped.")
        summaries_enabled = False
    else:
        print("🤖 AI summaries enabled (use --no-summaries to disable).")
    
    print("Loading JSON data...")
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if summaries_enabled:
        print("Building enhanced document hierarchy with unlimited depth and AI summaries...")
    else:
        print("Building enhanced document hierarchy with unlimited depth (summaries disabled)...")
    builder = EnhancedDocumentHierarchyBuilder()
    # Build hierarchy
    document_root = builder.build_enhanced_hierarchy(data, enable_summaries=summaries_enabled)
    
    print("\n" + "=" * 80)
    if summaries_enabled:
        print("ENHANCED DOCUMENT HIERARCHY (Unlimited Depth + Merged Elements + AI Summaries)")
    else:
        print("ENHANCED DOCUMENT HIERARCHY (Unlimited Depth + Merged Elements)")
    print("=" * 80)
    print(visualize_enhanced_hierarchy(document_root))
    
    # Save enhanced hierarchy to JSON
    hierarchy_output = "enhanced_document_hierarchy.json"
    with open(hierarchy_output, 'w', encoding='utf-8') as f:
        json.dump(document_root.to_dict(), f, indent=2, ensure_ascii=False)
    
    if summaries_enabled:
        print(f"\n💾 Enhanced document hierarchy with summaries saved to: {hierarchy_output}")
    else:
        print(f"\n💾 Enhanced document hierarchy (no summaries) saved to: {hierarchy_output}")
    
    # Generate enhanced statistics
    stats = generate_enhanced_hierarchy_stats(document_root)
    print(f"\n📊 Enhanced Hierarchy Statistics:")
    print(f"   Total structural nodes: {stats['structural_nodes']}")
    print(f"   Total content elements (leaf nodes): {stats['content_elements']}")
    print(f"   Nodes with AI summaries: {stats['nodes_with_summaries']}")
    print(f"   Merged figure-caption pairs: {stats['merged_figures']}")
    print(f"   Merged table-caption pairs: {stats['merged_tables']}")
    print(f"   Merged list groups: {stats['merged_lists']}")
    print(f"   Max depth: {stats['max_depth']}")
    print(f"   Sections with content: {stats['sections_with_content']}")


def generate_enhanced_hierarchy_stats(root: EnhancedDocumentNode) -> Dict[str, int]:
    """Generate statistics about the enhanced document hierarchy."""
    stats = {
        'structural_nodes': 0,
        'content_elements': 0,
        'nodes_with_summaries': 0,
        'merged_figures': 0,
        'merged_tables': 0,
        'merged_lists': 0,
        'max_depth': 0,
        'sections_with_content': 0
    }
    
    def count_nodes(node: EnhancedDocumentNode, depth: int = 0):
        stats['max_depth'] = max(stats['max_depth'], depth)
        
        if node.summary:
            stats['nodes_with_summaries'] += 1
        
        if node.is_structural() or node.label == 'document':
            stats['structural_nodes'] += 1
            if node.content_elements:
                stats['sections_with_content'] += 1
        
        # Count content elements and merged types
        for content in node.content_elements:
            stats['content_elements'] += 1
            if content.summary:
                stats['nodes_with_summaries'] += 1
            if content.label == 'figure':
                stats['merged_figures'] += 1
            elif content.label == 'table':
                stats['merged_tables'] += 1
            elif content.label == 'list_group':
                stats['merged_lists'] += 1
        
        for child in node.children:
            count_nodes(child, depth + 1)
    
    count_nodes(root)
    return stats


if __name__ == "__main__":
    main()