#!/bin/bash
# Load environment variables and run comprehensive tests

# Load environment from MCPs/.env file
set -a
source /Users/youdar/Documents/PKM/MCPs/.env
set +a

# Export critical variables
export OPENAI_API_KEY
export TAVILY_API_KEY
export DOC_PATH
export RETRIEVER

# Display loaded configuration
echo "Loaded environment configuration:"
echo "RETRIEVER=$RETRIEVER"
echo "DOC_PATH=$DOC_PATH"
echo "OPENAI_API_KEY=${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4}"
echo "TAVILY_API_KEY=${TAVILY_API_KEY:0:10}...${TAVILY_API_KEY: -4}"
echo ""

# Run the comprehensive test suite
cd /Users/youdar/Documents/PKM/MCPs/tools/gptr-mcp
uv run python test_comprehensive.py