from typing import TypedDict, Annotated, Sequence, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages
from operator import add

class ContentInsight(BaseModel):
    """Structured representation of a content insight"""
    title: str = Field(..., description="Creative title of the insight (max 10 words)")
    description: str = Field(..., description="Detailed explanation of the insight (2-3 sentences)")
    audience_relevance: str = Field(..., description="How the insight relates to the target audience")
    value_alignment: str = Field(..., description="How the insight aligns with the value proposition")

class GeneratedLinkedinPost(BaseModel):
    """Structured representation of a generated LinkedIn post"""
    title: str = Field(..., description="Attention-grabbing title for the LinkedIn post")
    hook: str = Field(..., description="Strong, engaging opening line to capture reader's attention")
    body: str = Field(..., description="Substantive content that provides value and elaborates on the insight")
    call_to_action: str = Field(..., description="Compelling call to action that encourages reader engagement")
    hashtags: Optional[list[str]] = Field(default=None, description="Relevant hashtags to increase post visibility")

class GraphState(TypedDict):
    """Graph state for the LinkedIn post generator workflow"""
    messages: Annotated[Sequence[HumanMessage | AIMessage], add_messages]
    website_url: str
    given_content: str
    tone: str
    target_audience: str
    value_proposition: str
    brand_persona: str
    website_content: List[str]
    content_insights: List[ContentInsight]
    linkedin_posts: List[GeneratedLinkedinPost]