import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from googleapiclient.discovery import build
import json
import os

# --- 0. Page Configuration ---
st.set_page_config(layout="wide", page_title="AI Perfume Description Generator")

# --- RTL CSS Injection ---
st.markdown(
    """
    <style>
    /* Force RTL layout for the entire app */
    div[data-testid="stApp"] {
        direction: rtl;
    }
    /* Align all text to the right */
    div[data-testid="stApp"] * {
        text-align: right;
    }
    /* Fix for multiselect chips (X button) */
    div[data-testid="stMultiSelect"] div[data-testid="stFileUploaderClearAll"] {
        margin-left: 0.5rem;
        margin-right: 0;
        user-select: none; /* Prevent 'x' from being selected */
    }
    /* Fix alignment of text inputs */
    div[data-testid="stTextInput"] input {
        direction: rtl !important;
    }
    /* Fix alignment of text area */
    div[data-testid="stTextArea"] textarea {
        text-align: right !important;
        direction: rtl !important;
    }
    /* Fix sidebar content alignment */
    div[data-testid="stSidebarUserContent"] * {
        text-align: right !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
# --- End of CSS ---

st.title("🖋️ מחולל תיאורי מוצר (גרסה 5.0)")
st.info("מנוע החיפוש מחפש אוטומטית בכל האתרים שהוגדרו בלוח הבקרה של Google (Jovoy, Essenza וכו')")


# --- 1. Load API Keys from Secrets ---
try:
    # Load Google Search API credentials
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    SEARCH_ENGINE_ID = st.secrets["SEARCH_ENGINE_ID"]
    
    # Configure Gemini
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    API_KEYS_LOADED = True
except KeyError:
    st.error("Error: API keys (GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY) not found in Streamlit Secrets.")
    st.caption("Please add these keys to your Streamlit Cloud app's Secrets.")
    API_KEYS_LOADED = False
except Exception as e:
    st.error(f"An error occurred loading keys: {e}")
    API_KEYS_LOADED = False

# --- 2. Helper Functions (The "Engine") ---

@st.cache_data(ttl=3600) # Cache search results for 1 hour
def search_google_for_url(brand, model):
    """
    Searches Google Custom Search for the product URL.
    The CX ID automatically restricts the search to the trusted sites.
    """
    st.write(f"Searching for '{brand} \"{model}\"' on all configured sites...")
    try:
        # --- [!!!] MAJOR FIX ---
        # The query no longer needs 'site:' operators.
        # The SEARCH_ENGINE_ID (cx) automatically handles filtering.
        # We just send the search term.
        query = f'{brand} "{model}"' 
        
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        res = service.cse().list(
            q=query,
            cx=SEARCH_ENGINE_ID,
            num=1 # We only want the top result
        ).execute()
        
        if 'items' in res and len(res['items']) > 0:
            first_result = res['items'][0]
            return first_result['link'], first_result['snippet']
        else:
            return None, "No results found."
            
    except Exception as e:
        return None, f"Error during Google Search: {e}"

@st.cache_data(ttl=600) # Cache scraped data for 10 minutes
def scrape_page_text(url):
    """
    Scrapes all visible text from a given URL.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise error for bad responses (404, 500)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script/style tags
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        # Limit text size to avoid huge API calls
        return text[:15000]
        
    except Exception as e:
        st.error(f"Error scraping URL {url}: {e}")
        return None

def call_gemini(prompt_text, use_json_mode=False):
    """
    Generic function to call the Gemini API.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        generation_config = {}
        if use_json_mode:
            # Enable JSON mode
            generation_config = {"response_mime_type": "application/json"}
            
        response = model.generate_content(prompt_text, generation_config=generation_config)
        return response.text
    except Exception as e:
        st.error(f"Gemini API Error: {e}")
        return None

# --- 3. Streamlit UI Layout ---

if not API_KEYS_LOADED:
    st.warning("Application is not configured. Please check API keys.")
    st.stop() # Stop execution if keys are missing

# --- PHASE 1: INPUT AND SEARCH ---
st.header("שלב 1: מצא את הבושם")

# Use session state to store data between button presses
if 'found_url' not in st.session_state:
    st.session_state.found_url = None
if 'scraped_text' not in st.session_state:
    st.session_state.scraped_text = None
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None

col1, col2 = st.columns(2)
with col1:
    brand_input = st.text_input("שם המותג", placeholder="לדוגמה: Xerjoff")
with col2:
    model_input = st.text_input("שם הדגם", placeholder="לדוגמה: Naxos")

# --- [!!!] REMOVED the st.multiselect for sites. It's no longer needed.

# Optional inputs for the AI writer
st.subheader("הגדרות לכתיבה (אופציונלי)")
col1, col2, col3 = st.columns(3)
vibe_input = col1.selectbox("בחר 'אווירה'", ["ערב ומסתורי", "רענן ויומיומי", "חושני וסקסי", "יוקרתי ורשמי"])
audience_input = col2.selectbox("בחר קהל יעד", ["יוניסקס", "גבר", "אישה"])
seo_keywords_input = col3.text_input("מילות מפתח נוספות ל-SEO", placeholder="בושם נישה, בושם וניל")


if st.button("1. מצא URL ונתונים", type="primary"):
    if not brand_input or not model_input:
        st.warning("אנא מלא שם מותג ושם דגם.")
    else:
        with st.spinner("מחפש בגוגל את ה-URL המתאים..."):
            # --- [!!!] SIMPLIFIED FUNCTION CALL ---
            # Pass only brand and model. The CX ID handles the site list.
            url, snippet = search_google_for_url(brand_input, model_input)
            
            if url:
                st.session_state.found_url = url
                st.success(f"נמצא URL! {url}")
                st.caption(f"תקציר מגוגל: {snippet}")
                
                with st.spinner(f"מגרד נתונים גולמיים מ-{url}..."):
                    text = scrape_page_text(url)
                    if text:
                        st.session_state.scraped_text = text
                        st.info(f"הצלחתי לגרד {len(text)} תווים מהעמוד.")
                    else:
                        st.error("לא הצלחתי לגרד נתונים מהעמוד.")
            else:
                st.error(f"לא מצאתי תוצאות עבור '{brand_input} \"{model_input}\"' באתרים שהגדרת ב-Google.")

# --- PHASE 2: GENERATION (if URL was found) ---
if st.session_state.found_url and st.session_state.scraped_text:
    
    st.markdown("---")
    st.header("שלב 2: הפק תיאורים")
    
    if st.button("2. צור תיאור! (מפעיל 3 קריאות API)"):
        
        # --- Step 1: Extract Data ---
        with st.spinner("שלב א': שולח ל-Gemini לחילוץ תווים..."):
            prompt_extract = f"""
            You are a data extraction bot. Your task is to parse the following raw text from a perfume website.
            Extract ONLY the following information in a clean JSON format.
            If you can't find information, return null for that field. Do not add any commentary.
            Respond *only* with JSON.
            
            JSON Structure:
            {{
              "perfume_name": "...",
              "brand_name": "...",
              "top_notes": ["...", "..."],
              "heart_notes": ["...", "..."],
              "base_notes": ["...", "..."]
            }}
            
            RAW TEXT:
            {st.session_state.scraped_text}
            """
            
            extracted_json_str = call_gemini(prompt_extract, use_json_mode=True)
            
            if not extracted_json_str:
                st.error("שלב א' נכשל: Gemini לא החזיר נתונים.")
                st.stop()
                
            try:
                # Clean the response in case Gemini added markdown
                extracted_json_str = extracted_json_str.replace("```json", "").replace("```", "").strip()
                st.session_state.extracted_data = json.loads(extracted_json_str)
                st.subheader("תווים שחולצו:")
                st.json(st.session_state.extracted_data)
            except Exception as e:
                st.error(f"שלב א' נכשל: לא הצלחתי לפענח את ה-JSON שחזר מ-Gemini. {e}")
                st.text(extracted_json_str) # Show the raw text for debugging
                st.stop()

        # --- Step 2: Creative Writing ---
        with st.spinner("שלב ב': שולח ל-Gemini לכתיבה יצירתית..."):
            extracted_data = st.session_state.extracted_data
            prompt_write = f"""
            אתה קופירייטר מומחה לבשמי נישה עבור בוטיק יוקרתי (כמו 'Velour' או 'Libero'). 
            הטון שלך מתוחכם, מעורר חושים ומסתורי.
            
            משימה: כתוב תיאור מוצר שיווקי ומרגש באורך 150-200 מילה. 
            אל תציין רק את התווים, אלא תשזור אותם בתוך סיפור או חוויה.
            
            נתונים:
            - שם: {extracted_data.get('perfume_name') or model_input}
            - מותג: {extracted_data.get('brand_name') or brand_input}
            - תווים עליונים: {', '.join(extracted_data.get('top_notes', []))}
            - תווים אמצעיים: {', '.join(extracted_data.get('heart_notes', []))}
            - תווים בסיסיים: {', '.join(extracted_data.get('base_notes', []))}
            - קהל: {audience_input}
            - אווירה: {vibe_input}
            
            כתוב בעברית. התחל עם כותרת מרתקת.
            """
            
            creative_draft = call_gemini(prompt_write)
            if not creative_draft:
                st.error("שלב ב' נכשל: Gemini לא החזיר טיוטה.")
                st.stop()
                
            st.subheader("טיוטה יצירתית:")
            st.markdown(creative_draft)

        # --- Step 3: SEO Optimization ---
        with st.spinner("שלב ג': שולח ל-Gemini לאופטימיזציית SEO..."):
            prompt_seo = f"""
            אתה מומחה SEO לאתרי איקומרס בתחום הבישום.
            
            משימה 1: נתח את תיאור המוצר הבא.
            משימה 2: ספק ב-3-5 נקודות הצעות לשיפור ה-SEO (התמקד בצפיפות מילות מפתח, קריאות וייחודיות).
            משימה 3: ספק את הגרסה הסופית, המשוכתבת והמוכנה (בעברית), שמשלבת את ההצעות שלך.
            
            מילות מפתח לשילוב: '{model_input}', '{brand_input}', 'בושם יוקרה', 'בושם נישה', {seo_keywords_input}.
            
            תיאור לניתוח:
            {creative_draft}
            
            החזר את התשובה בפורמט Markdown.
            """
            
            final_output = call_gemini(prompt_seo)
            if not final_output:
                st.error("שלב ג' נכשל: Gemini לא החזיר ניתוח SEO.")
                st.stop()

            st.markdown("---")
            st.subheader("✅ תוצר סופי: ניתוח SEO ותיאור מוכן")
            st.markdown(final_output)
            
            # Try to extract just the final version for easy copy-paste
            if "גרסה סופית" in final_output.lower():
                try:
                    # Find the final version text
                    final_text = final_output.split("רסה הסופית")[1].split(":", 1)[1].strip()
                    st.subheader("העתק-הדבק (טקסט נקי)")
                    st.text_area("תיאור סופי נקי", final_text, height=300)
                except Exception:
                    # It's okay if this fails, the full markdown is still there
                    pass
