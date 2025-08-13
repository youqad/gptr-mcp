"""
Search Configuration for GPT-Researcher MCP

This module provides region and language settings for search APIs.
"""

# Search region preferences (in order of priority)
SEARCH_REGIONS = [
    'us-en',    # United States - English
    'gb-en',    # Great Britain - English  
    'ca-en',    # Canada - English
    'au-en',    # Australia - English
    'wt-wt',    # Worldwide (fallback)
]

# Language preferences
SEARCH_LANGUAGES = [
    'en',       # English
    'en-US',    # US English
    'en-GB',    # British English
]

# Domains to exclude from search results
EXCLUDED_DOMAINS = [
    'zhihu.com',           # Chinese Q&A platform
    'baidu.com',           # Chinese search engine
    'bilibili.com',        # Chinese video platform
    'weibo.com',           # Chinese social media
    'csdn.net',            # Chinese tech blog
    'cnblogs.com',         # Chinese blog platform
    'jianshu.com',         # Chinese writing platform
    'segmentfault.com',    # Chinese tech Q&A (when in Chinese)
    'juejin.cn',           # Chinese dev community
    'oschina.net',         # Chinese open source community
]

# Preferred domains for technical content
PREFERRED_DOMAINS = [
    'github.com',
    'stackoverflow.com',
    'arxiv.org',
    'openai.com',
    'anthropic.com',
    'huggingface.co',
    'pytorch.org',
    'tensorflow.org',
    'scikit-learn.org',
    'python.org',
    'medium.com',
    'dev.to',
    'hackernoon.com',
    'nature.com',
    'science.org',
    'ieee.org',
    'acm.org',
]

def get_search_config():
    """Return search configuration for GPT-Researcher."""
    return {
        'region': SEARCH_REGIONS[0],  # Default to US-English
        'language': SEARCH_LANGUAGES[0],
        'excluded_domains': EXCLUDED_DOMAINS,
        'preferred_domains': PREFERRED_DOMAINS,
        'max_results': 10,
    }