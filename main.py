import os
import logging
from typing import Dict, Any
from langchain_together import ChatTogether
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

from state import GraphState, ContentInsight, GeneratedLinkedinPost
from utils import fetch_website_content

logger = logging.getLogger(__name__)

# Initialize the language model

def create_workflow(api_key: str = None) -> StateGraph:
    """Create and configure the workflow graph"""
    # Initialize LLM
    llm_together = ChatTogether(
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        temperature=0.7,
        timeout=120,
        max_retries=2
    )

    def get_website_content(state: GraphState) -> GraphState:
        """Node: Fetch website content"""
        website_url = state.get('website_url')
        given_content = state.get('given_content')
        
        content = []
        
        if website_url:
            web_content = fetch_website_content(website_url)
            if web_content:
                content.append(web_content)
                
        if given_content:
            content.append(given_content)
            
        state["website_content"] = "\n\n".join(content) if content else ""
        return state

    def generate_content_insights(state: GraphState) -> GraphState:
        """Node: Generate content insights"""
        content = state.get('website_content', '')
        target_audience = state['target_audience']
        value_proposition = state['value_proposition']

        insights = []
        
        for i in range(3):  # Generate 3 distinct insights
            prompt = f"""You are a creative content strategist. Generate three unique content insights from different angle for creating LinkedIn post, based on:

            Content Source:
            {content}

            Target Audience: {target_audience}
            Value Proposition: {value_proposition}

            Format your response as a single insight with:
            1. A creative TITLE (max 10 words)
            2. A DESCRIPTION (1-2 sentences explaining the insight)
            3. AUDIENCE RELEVANCE (1-2 sentences explaining how this insight specifically connects with the target audience)
            4. VALUE ALIGNMENT (1-2 sentences explaining how this insight aligns with value proposition)

            This should be insight #{i+1} of 3, make sure it's from unique angle and different from other insights, and do not repeat any previous insights.
            """

            try:
                structured_llm = llm_together.with_structured_output(ContentInsight)
                insight = structured_llm.invoke([HumanMessage(content=prompt)])
                insights.append(insight)
            except Exception as e:
                logger.error(f"Error generating insight {i+1}: {str(e)}")
                # Create a fallback insight
                fallback_insight = ContentInsight(
                    title=f"Insight {i+1}",
                    description="Unable to generate insight. Please try again.",
                    audience_relevance="N/A",
                    value_alignment="N/A"
                )
                insights.append(fallback_insight)

        state["content_insights"] = insights
        return state

    def generate_linkedin_posts(state: GraphState) -> GraphState:
        """Node: Generate LinkedIn posts"""
        content_insights = state.get('content_insights', [])
        tone = state['tone']
        target_audience = state['target_audience']
        value_proposition = state['value_proposition']
        brand_persona = state['brand_persona']

        linkedin_posts = []
        
        for insight in content_insights:
            prompt = f"""Generate a compelling LinkedIn post based on the following insight:

            Insight Title: {insight.title}
            Insight Description: {insight.description}
            Audience Relevance: {insight.audience_relevance}
            Value Alignment: {insight.value_alignment}

            Post Generation Guidelines:
            - Tone: {tone}
            - Target Audience: {target_audience}
            - Value Proposition: {value_proposition}
            - Brand Persona: {brand_persona}

            Craft a LinkedIn post with:
            1. An attention-grabbing TITLE
            2. A strong HOOK that immediately engages the reader
            3. A substantive BODY that provides real value
            4. A clear CALL TO ACTION
            5. Relevant HASHTAGS to increase post visibility
            """

            try:
                structured_llm = llm_together.with_structured_output(GeneratedLinkedinPost)
                post = structured_llm.invoke([HumanMessage(content=prompt)])
                linkedin_posts.append(post)
            except Exception as e:
                logger.error(f"Error generating LinkedIn post: {str(e)}")
                raise

        state['linkedin_posts'] = linkedin_posts
        return state

    # Create workflow graph
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("get_website_content", get_website_content)
    workflow.add_node("generate_content_insights", generate_content_insights)
    workflow.add_node("generate_linkedin_posts", generate_linkedin_posts)

    # Define edges
    workflow.add_edge(START, "get_website_content")
    workflow.add_edge("get_website_content", "generate_content_insights")
    workflow.add_edge("generate_content_insights", "generate_linkedin_posts")
    workflow.add_edge("generate_linkedin_posts", END)

    return workflow.compile()

def run_workflow(inputs: Dict[str, Any], api_key: str = None) -> Dict[str, Any]:
    """Run the workflow with the given inputs"""
    try:
        workflow = create_workflow(api_key)
        return workflow.invoke(inputs)
    except Exception as e:
        logger.error(f"Error running workflow: {str(e)}")
        raise