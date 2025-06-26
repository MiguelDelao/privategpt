#!/usr/bin/env python3
"""
MCP Prompt Testing Script

This script helps you rapidly test different prompt variations
for MCP tool integration.

Usage:
    python test_mcp_prompts.py --token YOUR_JWT_TOKEN
"""

import asyncio
import httpx
import json
import argparse
from typing import List, Dict, Any
from datetime import datetime


# Test prompts for different strategies
PROMPT_VARIATIONS = {
    "structured_commands": """<system>
<persona>
You are PrivateGPT with document search capabilities.
</persona>

<tool_instructions>
When you need to search documents, use this EXACT format:
===TOOL_CALL===
TOOL: search_documents
QUERY: your search terms here
LIMIT: 10
===END_TOOL===

Wait for results before continuing.
</tool_instructions>

<rules>
- ALWAYS search before answering document questions
- NEVER make up document content
- Show search queries to the user
</rules>
</system>""",

    "json_format": """<system>
<persona>
You are PrivateGPT with advanced search capabilities.
</persona>

<tool_format>
Respond with JSON when using tools:
{"action": "search", "query": "search terms", "limit": 10}
</tool_format>

<guidelines>
- Search before answering document questions
- Parse JSON responses into natural language
- Explain what you're searching for
</guidelines>
</system>""",

    "natural_language": """<system>
<persona>
You are PrivateGPT, a helpful AI assistant with document search abilities.
</persona>

<communication>
When searching documents, say something like:
"Let me search for [topic] in your documents..."
[Searching: your query here]

Then explain what you found.
</communication>

<important>
Always search documents before answering questions about uploaded content.
Never pretend to know document contents without searching.
</important>
</system>""",

    "xml_tags": """<system>
<persona>
You are PrivateGPT with powerful document search capabilities.
</persona>

<tools>
<search_documents>
Use like: <search query="AI technology" limit="5" />
Returns document chunks with relevance scores
</search_documents>
</tools>

<workflow>
1. User asks about documents
2. You MUST use <search> tag
3. System executes search
4. You summarize results
</workflow>

<output_format>
<thinking>Your reasoning about what to search</thinking>
<search query="..." limit="..." />
<answer>Your response based on search results</answer>
</output_format>
</system>""",

    "aggressive_tools": """<system>
<critical>
YOU MUST USE TOOLS FOR EVERY SINGLE REQUEST!
NEVER ANSWER WITHOUT SEARCHING FIRST!
</critical>

<tool_usage>
search_documents: MANDATORY for ALL questions
Format: <<<SEARCH: query>>>
</tool_usage>

<penalties>
Answering without searching = FAILURE
Making up information = FAILURE
Not showing search query = FAILURE
</penalties>
</system>""",

    "balanced_approach": """<system>
<identity>
You are PrivateGPT, an AI assistant with document search capabilities.
</identity>

<capabilities>
- Document search via search_documents tool
- General knowledge for non-document questions
- File operations when needed
</capabilities>

<decision_tree>
IF question about "your documents" or "uploaded files":
    THEN use search_documents
ELIF question about specific document content:
    THEN use search_documents
ELIF general knowledge question:
    THEN answer directly
ELSE:
    ASK for clarification
</decision_tree>

<search_format>
When searching, show: [Searching documents for: "query"]
</search_format>
</system>"""
}

# Test questions to evaluate prompts
TEST_QUESTIONS = [
    "What documents do you have?",
    "Search for information about AI",
    "Tell me about machine learning from the documents",
    "What is the capital of France?",  # Should NOT trigger search
    "Do you have any documents about neural networks?",
    "Summarize the uploaded reports",
    "What's 2+2?",  # Should NOT trigger search
    "Find all mentions of 'revenue' in the documents"
]


class PromptTester:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
        
    async def test_prompt(self, name: str, prompt_xml: str, question: str) -> Dict[str, Any]:
        """Test a single prompt with a question."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/prompts/test",
                    headers=self.headers,
                    json={
                        "prompt_xml": prompt_xml,
                        "model_name": "qwen2.5:3b",  # Or your preferred model
                        "test_message": question
                    }
                )
                response.raise_for_status()
                return {
                    "success": True,
                    "response": response.json(),
                    "contains_search": self._check_search_pattern(response.json())
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
    
    def _check_search_pattern(self, response: Dict) -> bool:
        """Check if response contains search patterns."""
        text = response.get("model_response", "").lower()
        patterns = [
            "search", "===tool_call===", "<<<search:", 
            "[searching", "<search", '{"action": "search"'
        ]
        return any(pattern in text for pattern in patterns)
    
    async def run_test_suite(self):
        """Run all prompt variations against all test questions."""
        results = []
        
        for prompt_name, prompt_xml in PROMPT_VARIATIONS.items():
            print(f"\n{'='*60}")
            print(f"Testing Prompt: {prompt_name}")
            print(f"{'='*60}")
            
            prompt_results = {
                "prompt_name": prompt_name,
                "questions": []
            }
            
            for question in TEST_QUESTIONS:
                print(f"\nQ: {question}")
                result = await self.test_prompt(prompt_name, prompt_xml, question)
                
                if result["success"]:
                    response_text = result["response"]["model_response"][:200] + "..."
                    uses_search = result["contains_search"]
                    should_search = any(term in question.lower() 
                                      for term in ["document", "search", "find", "uploaded", "reports"])
                    
                    correct = (uses_search == should_search)
                    status = "✅" if correct else "❌"
                    
                    print(f"{status} Search: {uses_search} (Should: {should_search})")
                    print(f"Response: {response_text}")
                    
                    prompt_results["questions"].append({
                        "question": question,
                        "uses_search": uses_search,
                        "should_search": should_search,
                        "correct": correct,
                        "response_preview": response_text
                    })
                else:
                    print(f"❌ Error: {result['error']}")
                    prompt_results["questions"].append({
                        "question": question,
                        "error": result["error"]
                    })
            
            results.append(prompt_results)
        
        # Generate report
        self._generate_report(results)
        
    def _generate_report(self, results: List[Dict]):
        """Generate a summary report of test results."""
        print(f"\n\n{'='*60}")
        print("PROMPT TESTING SUMMARY REPORT")
        print(f"{'='*60}")
        
        for prompt_result in results:
            prompt_name = prompt_result["prompt_name"]
            questions = prompt_result["questions"]
            
            correct_count = sum(1 for q in questions if q.get("correct", False))
            total_count = len(questions)
            accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
            
            print(f"\n{prompt_name}:")
            print(f"  Accuracy: {accuracy:.1f}% ({correct_count}/{total_count})")
            
            # Show failures
            failures = [q for q in questions if not q.get("correct", False) and "error" not in q]
            if failures:
                print("  Failed on:")
                for f in failures:
                    print(f"    - {f['question']} (search: {f['uses_search']}, expected: {f['should_search']})")
        
        # Save detailed results
        with open("prompt_test_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": results
            }, f, indent=2)
        
        print(f"\nDetailed results saved to prompt_test_results.json")


async def main():
    parser = argparse.ArgumentParser(description="Test MCP prompt variations")
    parser.add_argument("--token", required=True, help="JWT token for authentication")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Gateway base URL")
    parser.add_argument("--prompt", help="Test only a specific prompt variation")
    parser.add_argument("--question", help="Test with a specific question")
    
    args = parser.parse_args()
    
    tester = PromptTester(args.base_url, args.token)
    
    if args.prompt and args.question:
        # Test single prompt/question combination
        if args.prompt in PROMPT_VARIATIONS:
            result = await tester.test_prompt(
                args.prompt, 
                PROMPT_VARIATIONS[args.prompt], 
                args.question
            )
            print(json.dumps(result, indent=2))
        else:
            print(f"Unknown prompt: {args.prompt}")
            print(f"Available: {list(PROMPT_VARIATIONS.keys())}")
    else:
        # Run full test suite
        await tester.run_test_suite()


if __name__ == "__main__":
    asyncio.run(main())