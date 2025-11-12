"""
QNWIS Chainlit Application - Real Multi-Agent System with LLM Integration

This application uses:
- OpenAI GPT-4 for intelligent query understanding
- Anthropic Claude for deep analysis
- Multi-agent council for comprehensive answers
- Real data from Qatar Open Data, World Bank, and synthetic LMIS
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import chainlit as cl
from openai import OpenAI
from anthropic import Anthropic
import httpx

from qnwis.agents.base import DataClient
from qnwis.orchestration.council import default_agents, _run_agents
from qnwis.orchestration.synthesis import synthesize

# Initialize API clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Initialize QNWIS data client
data_client = DataClient(ttl_s=300)

# Brave Search API
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")


def search_brave(query: str, count: int = 5) -> list[dict]:
    """Search using Brave Search API for real-time web data."""
    if not BRAVE_API_KEY:
        return []
    
    try:
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": BRAVE_API_KEY
        }
        
        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": count},
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("web", {}).get("results", [])[:count]:
                results.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", "")
                })
            return results
    except Exception as e:
        print(f"Brave search error: {e}")
    
    return []


@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    welcome_message = """# 🇶🇦 Qatar National Workforce Intelligence System (QNWIS)

Welcome! I'm powered by a multi-agent AI system with access to:

**Data Sources:**
- 📊 Qatar Open Data Portal (1,152 datasets)
- 🌍 World Bank API (GCC labour indicators)
- 📈 Synthetic LMIS data (employment, wages, qatarization)

**AI Models:**
- 🤖 OpenAI GPT-4 (query understanding)
- 🧠 Anthropic Claude Sonnet 4.5 (deep analysis & synthesis)
- 🔍 Brave Search API (real-time web research)
- 👥 5 Specialized Agents (Labour Economist, Nationalization, Skills, Pattern Detective, Strategy)

**Ask me anything about:**
- Qatar's labour market trends
- GCC unemployment comparisons
- Qatarization progress
- Sector employment analysis
- Wage trends and forecasts

Try asking: "What are the current unemployment trends in the GCC region?"
"""
    
    await cl.Message(content=welcome_message).send()
    
    # Store agents in session
    agents = default_agents(data_client)
    cl.user_session.set("agents", agents)
    cl.user_session.set("data_client", data_client)


@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages with real LLM and multi-agent processing."""
    
    user_question = message.content
    
    # Step 1: Use GPT-4 to understand the query
    status_msg = cl.Message(content="🤔 Understanding your question...")
    await status_msg.send()
    
    try:
        # Use OpenAI to analyze the question
        gpt_response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a Qatar labour market expert. Analyze the user's question and identify what data they need. Be concise."},
                {"role": "user", "content": user_question}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        query_analysis = gpt_response.choices[0].message.content
        
        await status_msg.stream_token(f"\n\n**Query Analysis:** {query_analysis}\n\n")
        
    except Exception as e:
        await status_msg.stream_token(f"\n\n⚠️ GPT-4 unavailable: {str(e)}\n\n")
        query_analysis = user_question
    
    # Step 2: Web research for topics not in our data
    await status_msg.stream_token("🌐 Searching web for latest information...\n")
    
    # Search for digital industry, future of work, etc.
    search_queries = [
        f"digital industry Qatar {user_question}",
        f"future of work Qatar KSA UAE comparison",
        f"digital transformation Qatar Saudi Arabia UAE"
    ]
    
    web_results = []
    for search_query in search_queries[:2]:  # Limit to 2 searches
        results = search_brave(search_query, count=3)
        web_results.extend(results)
        if results:
            await status_msg.stream_token(f"  Found {len(results)} articles on: {search_query[:50]}...\n")
    
    # Step 3: Execute multi-agent analysis
    await status_msg.stream_token("\n🔍 Executing multi-agent analysis...\n")
    
    agents = cl.user_session.get("agents")
    
    try:
        # Run all agents
        reports = _run_agents(agents)
        
        await status_msg.stream_token(f"✅ Collected {len(reports)} agent reports\n\n")
        
        # Show agent findings
        for report in reports:
            await status_msg.stream_token(f"**{report.agent}**: {len(report.findings)} findings\n")
        
        # Step 3: Synthesize results
        await status_msg.stream_token("\n📊 Synthesizing council report...\n")
        council = synthesize(reports)
        
        # Step 4: Use Claude to generate final answer
        await status_msg.stream_token("\n🧠 Generating comprehensive answer with Claude...\n\n")
        
        # Prepare context for Claude
        findings_text = "\n\n".join([
            f"**{finding.title}**\n{finding.summary}\nMetrics: {finding.metrics}\nConfidence: {finding.confidence_score}"
            for finding in council.findings
        ])
        
        data_sources = set()
        for report in reports:
            for finding in report.findings:
                for evidence in finding.evidence:
                    data_sources.add(evidence.dataset_id)
        
        sources_text = "\n".join([f"- {source}" for source in sorted(data_sources)])
        
        # Format web research results
        web_context = ""
        if web_results:
            web_context = "\n\nWeb Research Results:\n"
            for i, result in enumerate(web_results[:5], 1):
                web_context += f"\n{i}. **{result['title']}**\n"
                web_context += f"   {result['description']}\n"
                web_context += f"   Source: {result['url']}\n"
        
        try:
            # Use Claude Sonnet 4.5 - the latest and most capable model
            claude_response = anthropic_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": f"""You are an expert analyst on Gulf labour markets and digital transformation. Provide a comprehensive, insightful answer to the user's question using ALL available information.

User Question: {user_question}

Internal Data Analysis (from QNWIS agents):
{findings_text}

Council Consensus:
{council.consensus}

Data Sources Used:
{sources_text}
{web_context}

Instructions:
1. Provide a detailed, professional answer that directly addresses the question
2. For digital industry/future of work questions, use the web research results extensively
3. Compare Qatar, KSA, and UAE when relevant using both data and web sources
4. Cite specific metrics, initiatives, and trends
5. Provide strategic insights and recommendations
6. Structure with clear sections: Overview, Qatar Analysis, Regional Comparison, Future Outlook, Key Recommendations
7. Be specific - mention actual programs, initiatives, GDP contributions, growth rates
8. Format in markdown with headers, bullet points, and emphasis

Make this a high-quality, actionable intelligence report worthy of government decision-makers."""
                }]
            )
            
            final_answer = claude_response.content[0].text
            
        except Exception as e:
            # Fallback if Claude fails
            final_answer = f"""## Analysis Results

**Council Consensus:**
{council.consensus}

**Key Findings:**

{findings_text}

**Data Sources:**
{sources_text}

**Warnings:** {len(council.warnings)} data quality notes
"""
            await status_msg.stream_token(f"\n⚠️ Claude unavailable: {str(e)}\n\n")
        
        # Send final answer
        await status_msg.stream_token("\n" + "="*80 + "\n\n")
        await status_msg.stream_token(final_answer)
        
        # Add metadata
        await status_msg.stream_token(f"\n\n---\n\n**System Info:**\n")
        await status_msg.stream_token(f"- Agents: {len(reports)}\n")
        await status_msg.stream_token(f"- Findings: {len(council.findings)}\n")
        await status_msg.stream_token(f"- Data Sources: {len(data_sources)}\n")
        await status_msg.stream_token(f"- Warnings: {len(council.warnings)}\n")
        
        await status_msg.update()
        
    except Exception as e:
        error_msg = f"""## ❌ Error During Analysis

{str(e)}

**Debug Info:**
- Question: {user_question}
- Agents initialized: {len(agents)}

Please try rephrasing your question or contact support."""
        
        await status_msg.stream_token(f"\n\n{error_msg}")
        await status_msg.update()
        
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    # This will be run by: chainlit run chainlit_app.py
    pass
