import os
import streamlit as st
from typing import Dict, Any
from main import run_workflow
from utils import check_password, save_feedback

# Set the page configuration
st.set_page_config(page_title="SmartMatch Staffing Platform", layout="wide", page_icon="✍️")

def setup_sidebar():
    st.sidebar.header("✍️ InstaLinkPost")
    st.sidebar.markdown(
        "This app helps you transform any web link into a powerful LinkedIn post "
    )
    
    st.sidebar.write("### Instructions")
    st.sidebar.write(
        "1. :key: Enter password to access the app\n"
        "2. :pencil: Fill out the form with your details\n"
        "3. :mag: Get your LinkedIn post generated\n"
        "4. :speech_balloon: Send us your feedback"
    )

    if 'feedback' not in st.session_state:
        st.session_state.feedback = ""

    st.sidebar.markdown("---")
    st.sidebar.subheader("💭 Feedback")

    feedback = st.sidebar.text_area(
        "Share your thoughts",
        value=st.session_state.feedback,
        placeholder="Your feedback helps us improve..."
    )

    if st.sidebar.button("📤 Submit Feedback", ):
        if feedback:
            try:
                save_feedback(feedback)
                st.session_state.feedback = ""
                st.sidebar.success("✨ Thank you for your feedback!")
            except Exception as e:
                st.sidebar.error(f"❌ Error saving feedback: {str(e)}")
        else:
            st.sidebar.warning("⚠️ Please enter feedback before submitting")

    st.sidebar.image("assets/logo01.jpg", use_container_width=True)


def initialize_session_state():
    """Initialize session state variables"""
    if 'generated_content' not in st.session_state:
        st.session_state.generated_content = None
    if 'is_generating' not in st.session_state:
        st.session_state.is_generating = False

      
def main():
    setup_sidebar()
    
    if not check_password():
        st.stop()

    initialize_session_state()    

    st.title("✍️ Linkedin Post Generator")
    st.markdown("Generate engaging LinkedIn content from your website or custom input.")
   
    # Input Section
    with st.container():
        st.subheader("Input Parameters")
        col1, col2 = st.columns(2)
        
        with col1:
            website_url = st.text_input(
                "Website URL",
                placeholder="https://example.com",
                help="Enter the website URL to generate content from"
            )
            
            given_content = st.text_area(
                "Custom Content",
                placeholder="Or paste your content here...",
                help="Enter custom content if not using a website URL",

                height=150
            )
            
            tone = st.selectbox(
                "Content Tone",
                options=["Educational", "Inspiring", "heartfelt with a touch of humor and emojis"],
                help="Select the tone for your LinkedIn posts"
            )

        with col2:
            target_audience = st.text_area(
                "Target Audience",
                placeholder="Describe your target audience...",
                help="Describe who your content is meant for",
                height=80
            )
            
            value_proposition = st.text_area(
                "Value Proposition",
                placeholder="What value does your content provide?",
                help="Describe the main value your content offers",
                height=80
            )
            
            brand_persona = st.text_area(
                "Brand Persona",
                placeholder="Describe your brand's personality...",
                help="Describe your brand's voice and personality",
                height=80
            )

    # Generate Button
    if st.button("Generate Content", type="primary", disabled=st.session_state.is_generating):
        if not (website_url or given_content):
            st.warning("Please provide either a website URL or custom content.")
            return
        
        if not all([tone, target_audience, value_proposition, brand_persona]):
            st.warning("Please fill in all required fields.")
            return

        try:
            st.session_state.is_generating = True
            
            # Show progress
            with st.spinner("Generating content..."):
                # Prepare inputs
                inputs = {
                    "website_url": website_url,
                    "given_content": given_content,
                    "tone": tone,
                    "target_audience": target_audience,
                    "value_proposition": value_proposition,
                    "brand_persona": brand_persona
                }
                
                # Run workflow
                result = run_workflow(inputs)

                if result:
                    st.session_state.generated_content = result
                    st.success("Content generated successfully!")
                    st.rerun()

        except Exception as e:
            st.error(f"Error: {str(e)}")
        finally:
            st.session_state.is_generating = False

    # Display Results in Tabs
    if st.session_state.generated_content:
        st.subheader("Generated Content")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Angle 1", "Angle 2", "Angle 3", "Best Version"])
        
        for idx, (tab, insight, post) in enumerate(zip(
            [tab1, tab2, tab3],
            st.session_state.generated_content["content_insights"],
            st.session_state.generated_content["linkedin_posts"]
        )):
            with tab:
                # Display Content Insight
                st.markdown("### Content Insight")
                st.markdown(f"**Title:** {insight.title}")
                st.markdown(f"**Description:** {insight.description}")
                st.markdown(f"**Audience Relevance:** {insight.audience_relevance}")
                st.markdown(f"**Value Alignment:** {insight.value_alignment}")
                
                st.markdown("---")
                
                # Display LinkedIn Post
                st.markdown("### LinkedIn Post")
                st.markdown(f"**Title:** {post.title}")
                st.markdown(f"**Hook:** {post.hook}")
                st.markdown(f"**Body:** {post.body}")
                st.markdown(f"**Call to Action:** {post.call_to_action}")
                if post.hashtags:
                    st.markdown(f"**Hashtags:** {' '.join(post.hashtags)}")
                
                # Add copy button for the LinkedIn post
                full_post = f"{post.title}\n\n{post.hook}\n\n{post.body}\n\n{post.call_to_action}\n\n{' '.join(post.hashtags) if post.hashtags else ''}"
                st.button(
                    "Copy Post",
                    key=f"copy_button_{idx}",
                    on_click=lambda text=full_post: st.write(text) or st.toast("Copied to clipboard!")
                )

        # Display the Best Version tab
        with tab4:
            best_selected = st.session_state.generated_content.get("best_selected")
            if best_selected:
                st.markdown("### The Best Version Selected")
                st.markdown(f"**Selected Version:** Version {best_selected.id}")
                st.markdown(f"**Selection Reasoning:** {best_selected.reason}")
                
                st.markdown("---")
                
                # Display the best post's content
                best_post = st.session_state.generated_content["linkedin_posts"][best_selected.id - 1]
                st.markdown("### The Best LinkedIn Post")
                st.markdown(f"**Title:** {best_post.title}")
                st.markdown(f"**Hook:** {best_post.hook}")
                st.markdown(f"**Body:** {best_post.body}")
                st.markdown(f"**Call to Action:** {best_post.call_to_action}")
                st.markdown(f"**Hashtags:** {' '.join(best_post.hashtags)}")                            

if __name__ == "__main__":
    main()