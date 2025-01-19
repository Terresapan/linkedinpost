import os
import streamlit as st
import logging
from typing import Dict, Any
from langchain_together import ChatTogether
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.constants import Send
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

from state import GraphState, ContentInsight, GeneratedLinkedinPost, SelectedBestPost
from utils import fetch_website_content

logger = logging.getLogger(__name__)

# Set API keys from Streamlit secrets
os.environ["TOGETHER_API_KEY"] = st.secrets["general"]["TOGETHER_API_KEY"]
os.environ["GOOLGE_API_KEY"] = st.secrets["general"]["GOOGLE_API_KEY"]
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]["API_KEY"]
os.environ["LANGCHAIN_ENDPOINT"]="https://api.smith.langchain.com"
os.environ["LANGCHAIN_PROJECT"] = "Linkedin Post Generator"

# Initialize the language model
def create_workflow() -> StateGraph:
    """Create and configure the workflow graph"""
    # Initialize LLM
    llm_together = ChatTogether(
        model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        api_key = os.environ["TOGETHER_API_KEY"],
        temperature=0.7,
        timeout=120,
        max_retries=2
    )

    llm_gemini = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key = os.environ["GOOLGE_API_KEY"],  
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
                structured_llm = llm_gemini.with_structured_output(ContentInsight)
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

        # Use Send to create parallel branches for generating LinkedIn posts
        return [
            Send("generate_single_post", {
                "insight": insight,
                "tone": tone,
                "target_audience": target_audience,
                "value_proposition": value_proposition,
                "brand_persona": brand_persona
            }) 
            for insight in content_insights
        ]

    def generate_single_post(state: GraphState) -> GraphState:
        """Node: Generate a single LinkedIn post"""
        insight = state['insight']
        tone = state['tone']
        target_audience = state['target_audience']
        value_proposition = state['value_proposition']
        brand_persona = state['brand_persona']

        # Construct the prompt
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
            return {"linkedin_posts": [post]}
        except Exception as e:
            logger.error(f"Error generating LinkedIn post: {str(e)}")
            raise
        
    def select_best_post(state: GraphState):
        """Reducer node: Select the best LinkedIn post"""
        linkedin_posts = state.get('linkedin_posts', [])
        
        if not linkedin_posts:
            logger.warning("No LinkedIn posts generated")
            return state

        # Use an LLM to select the best post based on specific criteria
        selection_prompt = f"""
        From the following generated LinkedIn posts, select the BEST post based on:
        1. Engagement potential
        2. Alignment with target audience
        3. Clarity of message
        4. Uniqueness of insight

        Generated Posts:
        {chr(10).join([f"Post {i+1}: {post.title} {post.hook} {post.body} {post.call_to_action}Hashtags: {', '.join(post.hashtags) if post.hashtags else 'None'}" for i, post in enumerate(linkedin_posts)])}

        Provide a detailed explanation for your selection, explaining why the chosen post is the best in terms of the criteria mentioned above.
        """

        try:
            # Use a structured output to select the best post
            best_post_selector = llm_together.with_structured_output(SelectedBestPost)
            best_post = best_post_selector.invoke([
                HumanMessage(content=selection_prompt),
                *[AIMessage(content=f"Post {i+1}:\nTitle: {post.title}\nHook: {post.hook}\nBody: {post.body}\nCall to Action: {post.call_to_action}\nHashtags: {', '.join(post.hashtags) if post.hashtags else 'None'}") for i, post in enumerate(linkedin_posts)]
            ])

            # Update the state with the best selected post
            return {
                "best_selected": best_post,
                "linkedin_posts": linkedin_posts  # Keep all posts for reference
            }
        except Exception as e:
            logger.error(f"Error selecting best post: {str(e)}")
            # Fallback to selecting the first post if there's an error
            return {
                "best_selected": SelectedBestPost(
                    id=1,
                    Title=linkedin_posts[[0]].title if linkedin_posts else "No Title",
                    reason="Default selection due to error in best post selection"
                    ),
                "linkedin_posts": linkedin_posts
            }
    
    
    # Create workflow graph
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("get_website_content", get_website_content)
    workflow.add_node("generate_content_insights", generate_content_insights)
    workflow.add_node("generate_single_post", generate_single_post)
    workflow.add_node("select_best_post", select_best_post)

    # Define edges
    workflow.add_edge(START, "get_website_content")
    workflow.add_edge("get_website_content", "generate_content_insights")
    workflow.add_conditional_edges("generate_content_insights", generate_linkedin_posts, ["generate_single_post"])
    workflow.add_edge("generate_single_post", "select_best_post")
    workflow.add_edge("select_best_post", END)

    return workflow.compile()

def run_workflow(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run the workflow with the given inputs"""
    try:
        workflow = create_workflow()
        return workflow.invoke(inputs)
    except Exception as e:
        logger.error(f"Error running workflow: {str(e)}")
        raise