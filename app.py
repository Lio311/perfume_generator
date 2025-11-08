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
    /* Import Open Sans Hebrew font */
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans+Hebrew:wght@300;400;500;600;700;800&display=swap');
    
    /* Force RTL layout for the entire app */
    div[data-testid="stApp"] {
        direction: rtl;
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    
    /* Apply font to all elements */
    div[data-testid="stApp"] *, 
    .stMarkdown, 
    .stText, 
    h1, h2, h3, h4, h5, h6, 
    p, span, div, 
    input, textarea, select, button,
    .stTextInput, .stTextArea, .stSelectbox {
        font-family: 'Open Sans Hebrew', sans-serif !important;
        text-align: right;
    }
    
    /* Fix for multiselect chips (X button) */
    div[data-testid="stMultiSelect"] div[data-testid="stFileUploaderClearAll"] {
        margin-left: 0.5rem;
        margin-right: 0;
        user-select: none;
    }
    
    /* Fix alignment of text inputs */
    div[data-testid="stTextInput"] input {
        direction: rtl !important;
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    
    /* Fix alignment of text area */
    div[data-testid="stTextArea"] textarea {
        text-align: right !important;
        direction: rtl !important;
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    
    /* Fix sidebar content alignment */
    div[data-testid="stSidebarUserContent"] * {
        text-align: right !important;
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }

    
    /* --- התיקון היסודי לבעיית ה-"keyl" --- */
    
    /* ודא שהכותרת (summary) היא ב-RTL */
    div[data-testid="stExpander"] summary {
        direction: rtl !important;
        display: flex !important;
        flex-direction: row-reverse !important;
        justify-content: flex-start !important;
        align-items: center !important;
    }
    
    /* 1. החבא את *כל* ה-div-ים בתוך ה-summary כברירת מחדל */
    div[data-testid="stExpander"] summary > div {
        display: none !important;
    }
    
    /* 2. הצג מחדש *רק* את ה-div שמכיל את הטקסט (p) */
    div[data-testid="stExpander"] summary > div:has(p) {
        display: flex !important;
        flex: 1 !important;
        /* ודא שה-p עצמו תופס מקום */
        p {
            flex: 1 !important;
            text-align: right !important;
        }
    }
    
    /* 3. הצג מחדש *רק* את ה-div שמכיל את החץ (svg) */
    div[data-testid="stExpander"] summary > div:has(svg) {
        display: flex !important;
        order: -1 !important; /* הזז אותו שמאלה (כי אנחנו ב-RTL) */
        margin-left: 0.5rem !important;
        margin-right: 0 !important;
    }

    /* 4. נקה שאריות ישנות */
    div[data-testid="stExpander"] summary::after,
    div[data-testid="stExpander"] [data-testid="StyledLinkIconContainer"] {
        content: none !important;
        display: none !important;
    }
    
    /* --- סוף התיקון --- */
    
    
    /* Debug info styling */
    .debug-box {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        font-family: 'Open Sans Hebrew', monospace !important;
        font-size: 12px;
    }
    
    /* SEO Analysis Box Styling */
    .seo-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .seo-section h3 {
        color: white;
        border-bottom: 2px solid rgba(255,255,255,0.3);
        padding-bottom: 10px;
        margin-bottom: 15px;
        font-family: 'Open Sans Hebrew', sans-serif !important;
    }
    
    .seo-section ul {
        background: rgba(255,255,255,0.1);
        padding: 15px 25px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .seo-section li {
        margin: 8px 0;
        line-height: 1.6;
    }
    
    .final-version-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .final-version-box h3 {
        color: white;
        border-bottom: 2px solid rgba(255,255,255,0.3);
        padding-bottom: 10px;
        margin-bottom: 15px;
    }
    
    /* Remove bold/emphasis from markdown content */
    .stMarkdown strong, .stMarkdown b {
        font-weight: normal !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("מחולל תיאורי מוצר (גרסה משופרת) 🖋️")

# --- 1. Load API Keys from Secrets ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    SEARCH_ENGINE_ID = st.secrets["SEARCH_ENGINE_ID"]
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    API_KEYS_LOADED = True
except KeyError:
    st.error("Error: API keys (GOOGLE_API_KEY, SEARCH_ENGINE_ID, GEMINI_API_KEY) not found in Streamlit Secrets.")
    st.caption("Please add these keys to your Streamlit Cloud app's Secrets.")
    API_KEYS_LOADED = False
except Exception as e:
    st.error(f"An error occurred loading keys: {e}")
    API_KEYS_LOADED = False

# --- 2. Helper Functions ---

@st.cache_data(ttl=3600)
def search_google_for_url(brand, model, sites, debug_mode=False):
    """
    Searches Google Custom Search for the product URL on trusted sites.
    Tries multiple search strategies for better results.
    """
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
        
        # Strategy 1: Flexible search without quotes
        site_query = " OR ".join([f"site:{site}" for site in sites])
        query1 = f'{brand} {model} ({site_query})'
        
        if debug_mode:
            st.info(f"🔍 ניסיון 1: {query1}")
        
        res1 = service.cse().list(q=query1, cx=SEARCH_ENGINE_ID, num=5).execute()
        
        # Check results from strategy 1
        if 'items' in res1 and len(res1['items']) > 0:
            for item in res1['items']:
                title_lower = item.get('title', '').lower()
                snippet_lower = item.get('snippet', '').lower()
                url_lower = item.get('link', '').lower()
                combined = f"{title_lower} {snippet_lower} {url_lower}"
                
                # Verify both brand and model appear
                if brand.lower() in combined and model.lower() in combined:
                    if debug_mode:
                        st.success(f"✅ מצאתי התאמה: {item['title']}")
                    return item['link'], item['snippet'], query1
                
            # Return first result if no perfect match
            if debug_mode:
                st.warning("⚠️ לא נמצאה התאמה מושלמת, מחזיר תוצאה ראשונה")
            return res1['items'][0]['link'], res1['items'][0]['snippet'], query1
        
        # Strategy 2: Try with exact phrase for model
        query2 = f'{brand} "{model}" ({site_query})'
        if debug_mode:
            st.info(f"🔍 ניסיון 2: {query2}")
        
        res2 = service.cse().list(q=query2, cx=SEARCH_ENGINE_ID, num=5).execute()
        
        if 'items' in res2 and len(res2['items']) > 0:
            if debug_mode:
                st.success(f"✅ נמצא בניסיון 2: {res2['items'][0]['title']}")
            return res2['items'][0]['link'], res2['items'][0]['snippet'], query2
        
        # Strategy 3: Try each site individually
        if debug_mode:
            st.info("🔍 ניסיון 3: חיפוש לכל אתר בנפרד")
        
        for site in sites[:3]:  # Try first 3 sites only
            query3 = f'{brand} {model} site:{site}'
            if debug_mode:
                st.info(f"    - מחפש ב: {site}")
            
            res3 = service.cse().list(q=query3, cx=SEARCH_ENGINE_ID, num=3).execute()
            
            if 'items' in res3 and len(res3['items']) > 0:
                if debug_mode:
                    st.success(f"✅ נמצא ב-{site}: {res3['items'][0]['title']}")
                return res3['items'][0]['link'], res3['items'][0]['snippet'], query3
        
        return None, "No results found after trying multiple strategies.", None
            
    except Exception as e:
        return None, f"Error during Google Search: {e}", None

@st.cache_data(ttl=600)
def scrape_page_text(url):
    """
    Scrapes all visible text from a given URL.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script/style tags
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
        
        text = soup.get_text(separator=' ', strip=True)
        # Limit text size
        return text[:20000]
        
    except Exception as e:
        st.error(f"Error scraping URL {url}: {e}")
        return None

def call_gemini(prompt_text, use_json_mode=False, model_name='models/gemini-2.5-flash', retry_count=3):
    """
    Generic function to call the Gemini API with retry logic.
    """
    import time
    
    for attempt in range(retry_count):
        try:
            model = genai.GenerativeModel(model_name)
            generation_config = {}
            if use_json_mode:
                generation_config = {"response_mime_type": "application/json"}
                
            response = model.generate_content(prompt_text, generation_config=generation_config)
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            
            # Check if it's a quota error
            if "429" in error_msg or "quota" in error_msg.lower():
                st.warning(f"⚠️ חריגה ממכסת המודל '{model_name}'")
                
                # Try to extract retry delay
                if "retry in" in error_msg.lower():
                    import re
                    match = re.search(r'retry in ([\d.]+)s', error_msg)
                    if match:
                        wait_time = float(match.group(1))
                        st.info(f"⏳ ממתין {int(wait_time)} שניות לפני ניסיון חוזר...")
                        time.sleep(wait_time)
                        continue
                
                # If this is not the last attempt, try with flash model
                if attempt < retry_count - 1 and 'pro' in model_name:
                    st.info("🔄 מנסה עם מודל Flash (זול יותר)...")
                    model_name = 'models/gemini-2.5-flash'
                    time.sleep(2)
                    continue
                else:
                    st.error(f"""
                    ❌ **מכסת ה-API מלאה!**
                    
                    פתרונות אפשריים:
                    1. המתן כ-60 שניות ונסה שוב (המכסה מתאפסת כל דקה)
                    2. השתמש במודל `gemini-2.5-flash` במקום `pro` (יש לו מכסה גבוהה יותר)
                    3. שדרג לתוכנית בתשלום: [Google AI Studio](https://ai.google.dev/pricing)
                    4. בדוק את השימוש שלך: [Usage Dashboard](https://ai.dev/usage?tab=rate-limit)
                    
                    **הסבר:** אתה ב-2/2 RPM על gemini-2.5-pro - המכסה מלאה! 
                    """)
                    return None
            
            # Other errors
            elif attempt < retry_count - 1:
                st.warning(f"⚠️ ניסיון {attempt + 1} נכשל, מנסה שוב...")
                time.sleep(2)
            else:
                st.error(f"❌ Gemini API Error: {error_msg}")
                st.info(f"💡 המודל '{model_name}' לא זמין. נסה לבחור מודל אחר")
                return None
    
    return None

# --- 3. Streamlit UI Layout ---

if not API_KEYS_LOADED:
    st.warning("Application is not configured. Please check API keys.")
    st.stop()

# Session state initialization
if 'found_url' not in st.session_state:
    st.session_state.found_url = None
if 'scraped_text' not in st.session_state:
    st.session_state.scraped_text = None
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = None

# --- PHASE 1: INPUT AND SEARCH ---
st.header("שלב 1: מצא את הבושם")

col1, col2 = st.columns(2)
with col1:
    brand_input = st.text_input("שם המותג", placeholder="לדוגמה: Xerjoff")
with col2:
    model_input = st.text_input("שם הדגם", placeholder="לדוגמה: Naxos")

# Site options
site_options = [
    "nicheperfumes.net",
    "jovoyparis.com",
    "nadiaperfumeria.com",
    "selfridges.com",
    "luckyscent.com",
    "lamaisonduparfum.com",
    "fragrancesandart.com",
    "neroli.hu",
    "ecuacionnatural.com",
    "profumiluxurybrands.it",
    "maxaroma.com",
    "essenza-nobile.de",
    "ausliebezumduft.de",
    "fragrantica.com",
    "basenotes.net"
]

sites_to_search = st.multiselect(
    "אתרים אמינים לחיפוש",
    options=site_options,
    default=["jovoyparis.com", "essenza-nobile.de", "nicheperfumes.net", "luckyscent.com", "fragrantica.com"]
)

# Debug mode toggle
debug_mode = st.checkbox("🔧 מצב דיבאג (הצג פרטי חיפוש)", value=False)

# Clean sites list (fix for RTL bug)
cleaned_sites = []
for site in sites_to_search:
    if site.startswith('x') and site[1:] in site_options:
        cleaned_sites.append(site[1:])
    else:
        cleaned_sites.append(site)

# Optional inputs for AI writer
st.subheader("הגדרות לכתיבה (אופציונלי)")
col1, col2, col3, col4 = st.columns(4)
vibe_input = col1.selectbox("בחר 'אווירה'", ["ערב ומסתורי", "רענן ויומיומי", "חושני וסקסי", "יוקרתי ורשמי"])
audience_input = col2.selectbox("בחר קהל יעד", ["יוניסקס", "גבר", "אישה"])
seo_keywords_input = col3.text_input("מילות מפתח נוספות ל-SEO", placeholder="בושם נישה, בושם וניל")

# --- הוספת הסליידר ---
length_slider = col4.slider(
    "אורך תיאור רצוי (במילים)",
    min_value=50,
    max_value=300,
    value=150,  # ברירת המחדל המומלצת
    step=25
)
# --- סוף הוספת הסליידר ---

# Get available models dynamically
available_models = []
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
except:
    # Fallback to common model names
    available_models = [
        'models/gemini-2.5-flash',
        'models/gemini-1.5-flash',
        'models/gemini-1.5-pro', 
        'models/gemini-pro'
    ]

# Clean model names for display
display_models = [m.replace('models/', '') for m in available_models]

# Default to flash model (cheaper and faster)
default_index = 0
if 'gemini-2.5-flash' in display_models:
    default_index = display_models.index('gemini-2.5-flash')
elif 'gemini-1.5-flash' in display_models:
    default_index = display_models.index('gemini-1.5-flash')

# הזזנו את בחירת המודל מחוץ לעמודות
gemini_model = st.selectbox("מודל Gemini", 
    display_models,
    index=default_index,
    help="⚡ Flash = מהיר וזול | 🧠 Pro = חכם יותר, יקר יותר"
)

# Add back 'models/' prefix if needed
if not gemini_model.startswith('models/'):
    gemini_model_full = f'models/{gemini_model}'
else:
    gemini_model_full = gemini_model

if st.button("מצא URL ונתונים 🔍", type="primary"):
    if not brand_input or not model_input:
        st.warning("אנא מלא שם מותג ושם דגם.")
    else:
        with st.spinner("מחפש בגוגל את ה-URL המתאים..."):
            url, snippet, query = search_google_for_url(
                brand_input, 
                model_input, 
                cleaned_sites,
                debug_mode=debug_mode
            )
            
            if url:
                st.session_state.found_url = url
                st.session_state.search_query = query
                st.success(f"✅ נמצא URL!")
                
                # Show result in an organized way
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**🔗 קישור:** [{url}]({url})")
                    st.caption(f"📝 תקציר: {snippet}")
                with col2:
                    if debug_mode and query:
                        st.markdown(f'<div class="debug-box">שאילתה שעבדה:<br>{query}</div>', unsafe_allow_html=True)
                
                with st.spinner(f"מגרד נתונים מהעמוד..."):
                    text = scrape_page_text(url)
                    if text:
                        st.session_state.scraped_text = text
                        st.info(f"✅ הצלחתי לגרד {len(text):,} תווים מהעמוד.")
                    else:
                        st.error("❌ לא הצלחתי לגרד נתונים מהעמוד.")
            else:
                st.error(f"❌ לא מצאתי תוצאות עבור '{brand_input} {model_input}' באתרים שצוינו.")
                st.info("💡 טיפים:")
                st.markdown("""
                - נסה להפחית את מספר האתרים
                - בדוק שהשמות נכונים
                - נסה לחפש ידנית ב-Google: `{brand} {model} site:jovoyparis.com`
                - הפעל מצב דיבאג לפרטים נוספים
                """)

# --- PHASE 2: GENERATION ---
if st.session_state.found_url and st.session_state.scraped_text:
    
    st.markdown("---")
    st.header("שלב 2: הפק תיאורים")
    
    if st.button("צור תיאור! (מפעיל 3 קריאות AI) ✨", type="primary"):
        
        # Show current model being used
        st.info(f"משתמש במודל: **{gemini_model_full}** 🤖")
        
        # Step 1: Extract Data
        with st.spinner("שלב א': מחלץ תווים מהעמוד... ⏳"):
            prompt_extract = f"""
You are a data extraction bot. Your task is to parse the following raw text from a perfume website.
Extract ONLY the following information in a clean JSON format.
If you can't find information, return null for that field. Do not add any commentary.
Respond *only* with valid JSON.

JSON Structure:
{{
  "perfume_name": "...",
  "brand_name": "...",
  "top_notes": ["...", "..."],
  "heart_notes": ["...", "..."],
  "base_notes": ["...", "..."],
  "perfumer": "...",
  "year": "...",
  "concentration": "..."
}}

RAW TEXT:
{st.session_state.scraped_text}
"""
            
            extracted_json_str = call_gemini(prompt_extract, use_json_mode=True, model_name=gemini_model_full)
            
            if not extracted_json_str:
                st.error("❌ שלב א' נכשל: Gemini לא החזיר נתונים.")
                st.stop()
                
            try:
                extracted_json_str = extracted_json_str.replace("```json", "").replace("```", "").strip()
                st.session_state.extracted_data = json.loads(extracted_json_str)
                
                with st.expander("תווים שחולצו (לחץ להצגה) 📋", expanded=False):
                    st.json(st.session_state.extracted_data)
                    
            except Exception as e:
                st.error(f"שלב א' נכשל: לא הצלחתי לפענח את ה-JSON. {e} ❌")
                with st.expander("תשובה גולמית מ-Gemini 🐛"):
                    st.text(extracted_json_str)
                st.stop()

        # Step 2: Creative Writing
        with st.spinner("שלב ב': כותב תיאור יצירתי... ⏳"):
            extracted_data = st.session_state.extracted_data
            
            # Build notes description
            notes_desc = ""
            if extracted_data.get('top_notes'):
                notes_desc += f"תווים עליונים: {', '.join(extracted_data['top_notes'])}\n"
            if extracted_data.get('heart_notes'):
                notes_desc += f"תווים אמצעיים: {', '.join(extracted_data['heart_notes'])}\n"
            if extracted_data.get('base_notes'):
                notes_desc += f"תווים בסיסיים: {', '.join(extracted_data['base_notes'])}"
            
            # --- עדכון הפרומפט עם הסליידר ---
            prompt_write = f"""
אתה קופירייטר מומחה לבשמי נישה עבור בוטיק יוקרתי.
הטון שלך מתוחכם, מעורר חושים ומסתורי.

משימה: כתוב תיאור מוצר שיווקי ומרגש באורך של כ-{length_slider} מילים.
אל תציין רק את התווים, אלא תשזור אותם בתוך סיפור או חוויה חושית.
חשוב: אל תשתמש בכוכביות (**) או הדגשות אחרות במקטע. כתוב טקסט רגיל בלבד.

נתונים:
- שם: {extracted_data.get('perfume_name') or model_input}
- מותג: {extracted_data.get('brand_name') or brand_input}
{notes_desc}
- קהל יעד: {audience_input}
- אווירה רצויה: {vibe_input}

כתוב בעברית. התחל עם כותרת מרתקת (לא כותרת H1, רק משפט פותח).
התמקד בחוויה ובתחושות, לא בפירוט טכני יבש.
"""
            # --- סוף עדכון הפרומפט ---
            
            creative_draft = call_gemini(prompt_write, model_name=gemini_model_full)
            if not creative_draft:
                st.error("שלב ב' נכשל: Gemini לא החזיר טיוטה. ❌")
                st.stop()
            
            # Remove any bold/emphasis markers from the response
            creative_draft = creative_draft.replace("**", "").replace("__", "")
            
            with st.expander("טיוטה יצירתית (לחץ להצגה) 📝", expanded=True):
                st.markdown(creative_draft)

        # Step 3: SEO Optimization
        with st.spinner("שלב ג': מבצע אופטימיזציית SEO... ⏳"):
            prompt_seo = f"""
אתה מומחה SEO לאתרי איקומרס בתחום הבישום.

משימה:
1. נתח את תיאור המוצר הבא מבחינת SEO
2. ספק 3-5 נקודות לשיפור (צפיפות מילות מפתח, קריאות, ייחודיות)
3. כתוב את הגרסה הסופית המשופרת בעברית

חשוב מאוד: אל תשתמש בכוכביות (**) או הדגשות כלשהן בטקסט הסופי!

מילות מפתח חובה לשילוב: '{model_input}', '{brand_input}', 'בושם יוקרה', 'בושם נישה', {seo_keywords_input}.

טיוטה לניתוח:
{creative_draft}

החזר בפורמט הבא (בדיוק כך):

## ניתוח SEO
- נקודה 1
- נקודה 2
- נקודה 3

## גרסה סופית משופרת
[הטקסט המוכן ללא כוכביות או הדגשות]
"""
            
            final_output = call_gemini(prompt_seo, model_name=gemini_model_full)
            if not final_output:
                st.error("שלב ג' נכשל: Gemini לא החזיר ניתוח SEO. ❌")
                st.stop()

            # Remove bold markers
            final_output = final_output.replace("**", "").replace("__", "")

            st.markdown("---")
            st.subheader("תוצר סופי: ניתוח SEO ותיאור מוכן ✅")
            
            # Parse and format the output with styled boxes
            sections = final_output.split("##")
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                    
                if "ניתוח seo" in section.lower():
                    # SEO Analysis section
                    lines = section.split('\n')
                    title = lines[0].strip()
                    content = '\n'.join(lines[1:]).strip()
                    
                    st.markdown(f"""
                    <div class="seo-section">
                        <h3>{title}</h3>
                        <div style="text-align: right;">
                            {content.replace('- ', '• ').replace('\n', '<br>')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                elif "גרסה סופית" in section.lower() or "הטקסט המוכן" in section.lower():
                    # Final version section
                    lines = section.split('\n')
                    title = lines[0].strip()
                    content = '\n'.join(lines[1:]).strip().replace("[הטקסט המוכן ללא כוכביות או הדגשות]", "")
                    
                    st.markdown(f"""
                    <div class="final-version-box">
                        <h3>{title}</h3>
                        <div style="text-align: right; line-height: 1.8;">
                            {content}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Clean text area for copying
                    if content:
                        st.subheader("העתק-הדבק (טקסט נקי) 📋")
                        
                        st.text_area("תיאור סופי (להעתקה):", content, height=300)

# Footer
st.markdown("---")
st.caption("מופעל על ידי Google Gemini & Google Custom Search API | נוצר עבור בוטיקי בשמים יוקרתיים 🚀")
