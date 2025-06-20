from __future__ import annotations

"""
XML parser for handling thinking brackets and UI tags in AI responses.

Handles tags like:
- <thinking>...</thinking> - Internal reasoning (hidden from user)
- <status>...</status> - Progress indicators
- <error>...</error> - Error messages needing special UI treatment
"""

import re
import logging
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedContent:
    """Result of parsing AI response content"""
    processed_content: str  # Content with thinking removed, ready for UI
    thinking_content: Optional[str]  # Extracted thinking content
    ui_tags: Dict[str, List[str]]  # Parsed UI tags for rendering
    raw_content: str  # Original unparsed content


class XMLContentParser:
    """Parser for AI response content with XML tags"""
    
    # Supported XML tags for UI rendering
    UI_TAGS = {
        'thinking', 'status', 'error', 'warning', 'info', 'debug',
        'code', 'tool_call', 'result', 'citation'
    }
    
    def __init__(self, enable_thinking: bool = True):
        self.enable_thinking = enable_thinking
        
        # Compile regex patterns for performance
        self.thinking_pattern = re.compile(
            r'<thinking>(.*?)</thinking>', 
            re.DOTALL | re.IGNORECASE
        )
        
        # Pattern for all supported UI tags
        tag_pattern = '|'.join(self.UI_TAGS)
        self.ui_tag_pattern = re.compile(
            rf'<({tag_pattern})(?:\s+[^>]*)?>(.*?)</\1>', 
            re.DOTALL | re.IGNORECASE
        )
    
    def parse(self, content: str) -> ParsedContent:
        """
        Parse AI response content, extracting thinking and UI tags.
        
        Args:
            content: Raw AI response content
            
        Returns:
            ParsedContent with processed content and extracted elements
        """
        if not content:
            return ParsedContent(
                processed_content="",
                thinking_content=None,
                ui_tags={},
                raw_content=""
            )
        
        raw_content = content
        processed_content = content
        thinking_content = None
        ui_tags: Dict[str, List[str]] = {}
        
        try:
            # Extract thinking content if enabled
            if self.enable_thinking:
                thinking_matches = self.thinking_pattern.findall(content)
                if thinking_matches:
                    # Combine multiple thinking blocks
                    thinking_content = '\n\n'.join(match.strip() for match in thinking_matches)
                    # Remove thinking tags from processed content
                    processed_content = self.thinking_pattern.sub('', processed_content)
            
            # Extract UI tags
            ui_tag_matches = self.ui_tag_pattern.findall(processed_content)
            for tag_name, tag_content in ui_tag_matches:
                tag_name = tag_name.lower()
                if tag_name not in ui_tags:
                    ui_tags[tag_name] = []
                ui_tags[tag_name].append(tag_content.strip())
            
            # Clean up processed content - remove extra whitespace
            processed_content = re.sub(r'\n\s*\n\s*\n', '\n\n', processed_content)
            processed_content = processed_content.strip()
            
        except Exception as e:
            logger.error(f"Error parsing XML content: {e}")
            # Fallback to original content if parsing fails
            processed_content = content
        
        return ParsedContent(
            processed_content=processed_content,
            thinking_content=thinking_content,
            ui_tags=ui_tags,
            raw_content=raw_content
        )
    
    def extract_status_messages(self, ui_tags: Dict[str, List[str]]) -> List[str]:
        """Extract status messages for real-time UI updates"""
        return ui_tags.get('status', [])
    
    def extract_error_messages(self, ui_tags: Dict[str, List[str]]) -> List[str]:
        """Extract error messages for error handling"""
        return ui_tags.get('error', [])
    
    def has_thinking(self, content: str) -> bool:
        """Check if content contains thinking tags"""
        return bool(self.thinking_pattern.search(content))
    
    def strip_thinking(self, content: str) -> str:
        """Quickly strip thinking tags from content"""
        return self.thinking_pattern.sub('', content).strip()
    
    def render_for_ui(self, parsed: ParsedContent, show_thinking: bool = False) -> Dict[str, Any]:
        """
        Render parsed content for UI consumption.
        
        Args:
            parsed: ParsedContent object
            show_thinking: Whether to include thinking content
            
        Returns:
            Dictionary suitable for JSON serialization to UI
        """
        result = {
            'content': parsed.processed_content,
            'ui_tags': parsed.ui_tags,
            'has_thinking': parsed.thinking_content is not None
        }
        
        if show_thinking and parsed.thinking_content:
            result['thinking'] = parsed.thinking_content
        
        # Add convenience flags for UI
        result['has_status'] = 'status' in parsed.ui_tags
        result['has_errors'] = 'error' in parsed.ui_tags
        result['has_warnings'] = 'warning' in parsed.ui_tags
        
        return result


# Global parser instance
_parser: Optional[XMLContentParser] = None


def get_xml_parser(enable_thinking: bool = True) -> XMLContentParser:
    """Get or create global XML parser instance"""
    global _parser
    if _parser is None or _parser.enable_thinking != enable_thinking:
        _parser = XMLContentParser(enable_thinking=enable_thinking)
    return _parser


def parse_ai_content(content: str, enable_thinking: bool = True) -> ParsedContent:
    """Convenience function to parse AI content"""
    parser = get_xml_parser(enable_thinking)
    return parser.parse(content)


def quick_strip_thinking(content: str) -> str:
    """Convenience function to quickly strip thinking tags"""
    parser = get_xml_parser()
    return parser.strip_thinking(content)