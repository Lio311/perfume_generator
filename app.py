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
        user-select: none;
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
    /* Debug info styling */
    .debug-box {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        font-family: monospace;
        font-size: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🖋️ מחולל תיאורי מוצר (גרסה משופרת)")

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
                st.info(f"   - מחפש ב: {site}")
            
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

def call_gemini(prompt_text, use_json_mode=False):
    """
    Generic function to call the Gemini API.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        generation_config = {}
        if use_json_mode:
            generation_config = {"response_mime_type": "application/json"}
            
        response = model.generate_content(prompt_text, generation_config=generation_config)
        return response.text
    except Exception as e:
        st.error(f"Gemini API Error: {e}")
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
col1, col2, col3 = st.columns(3)
vibe_input = col1.selectbox("בחר 'אווירה'", ["ערב ומסתורי", "רענן ויומיומי", "חושני וסקסי", "יוקרתי ורשמי"])
audience_input = col2.selectbox("בחר קהל יעד", ["יוניסקס", "גבר", "אישה"])
seo_keywords_input = col3.text_input("מילות מפתח נוספות ל-SEO", placeholder="בושם נישה, בושם וניל")

if st.button("🔍 1. מצא URL ונתונים", type="primary"):
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
    
    if st.button("✨ 2. צור תיאור! (מפעיל 3 קריאות AI)", type="primary"):
        
        # Step 1: Extract Data
        with st.spinner("⏳ שלב א': מחלץ תווים מהעמוד..."):
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
            
            extracted_json_str = call_gemini(prompt_extract, use_json_mode=True)
            
            if not extracted_json_str:
                st.error("❌ שלב א' נכשל: Gemini לא החזיר נתונים.")
                st.stop()
                
            try:
                extracted_json_str = extracted_json_str.replace("```json", "").replace("```", "").strip()
                st.session_state.extracted_data = json.loads(extracted_json_str)
                
                with st.expander("📋 תווים שחולצו (לחץ להצגה)", expanded=False):
                    st.json(st.session_state.extracted_data)
                    
            except Exception as e:
                st.error(f"❌ שלב א' נכשל: לא הצלחתי לפענח את ה-JSON. {e}")
                with st.expander("🐛 תשובה גולמית מ-Gemini"):
                    st.text(extracted_json_str)
                st.stop()

        # Step 2: Creative Writing
        with st.spinner("⏳ שלב ב': כותב תיאור יצירתי..."):
            extracted_data = st.session_state.extracted_data
            
            # Build notes description
            notes_desc = ""
            if extracted_data.get('top_notes'):
                notes_desc += f"תווים עליונים: {', '.join(extracted_data['top_notes'])}\n"
            if extracted_data.get('heart_notes'):
                notes_desc += f"תווים אמצעיים: {', '.join(extracted_data['heart_notes'])}\n"
            if extracted_data.get('base_notes'):
                notes_desc += f"תווים בסיסיים: {', '.join(extracted_data['base_notes'])}"
            
            prompt_write = f"""
אתה קופירייטר מומחה לבשמי נישה עבור בוטיק יוקרתי.
הטון שלך מתוחכם, מעורר חושים ומסתורי.

משימה: כתוב תיאור מוצר שיווקי ומרגש באורך 150-200 מילה.
אל תציין רק את התווים, אלא תשזור אותם בתוך סיפור או חוויה חושית.

נתונים:
- שם: {extracted_data.get('perfume_name') or model_input}
- מותג: {extracted_data.get('brand_name') or brand_input}
{notes_desc}
- קהל יעד: {audience_input}
- אווירה רצויה: {vibe_input}

כתוב בעברית. התחל עם כותרת מרתקת (לא כותרת H1, רק משפט פותח).
התמקד בחוויה ובתחושות, לא בפירוט טכני יבש.
"""
            
            creative_draft = call_gemini(prompt_write)
            if not creative_draft:
                st.error("❌ שלב ב' נכשל: Gemini לא החזיר טיוטה.")
                st.stop()
            
            with st.expander("📝 טיוטה יצירתית (לחץ להצגה)", expanded=True):
                st.markdown(creative_draft)

        # Step 3: SEO Optimization
        with st.spinner("⏳ שלב ג': מבצע אופטימיזציית SEO..."):
            prompt_seo = f"""
אתה מומחה SEO לאתרי איקומרס בתחום הבישום.

משימה:
1. נתח את תיאור המוצר הבא מבחינת SEO
2. ספק 3-5 נקודות לשיפור (צפיפות מילות מפתח, קריאות, ייחודיות)
3. כתוב את הגרסה הסופית המשופרת בעברית

מילות מפתח חובה לשילוב: '{model_input}', '{brand_input}', 'בושם יוקרה', 'בושם נישה', {seo_keywords_input}.

טיוטה לניתוח:
{creative_draft}

החזר בפורמט:

## ניתוח SEO
[רשימת נקודות]

## גרסה סופית משופרת
[הטקסט המוכן]
"""
            
            final_output = call_gemini(prompt_seo)
            if not final_output:
                st.error("❌ שלב ג' נכשל: Gemini לא החזיר ניתוח SEO.")
                st.stop()

            st.markdown("---")
            st.subheader("✅ תוצר סופי: ניתוח SEO ותיאור מוכן")
            st.markdown(final_output)
            
            # Try to extract final version
            if "גרסה סופית" in final_output.lower() or "הטקסט המוכן" in final_output.lower():
                try:
                    parts = final_output.split("##")
                    for part in parts:
                        if "גרסה סופית" in part.lower() or "הטקסט המוכן" in part.lower():
                            # Extract text after the header
                            lines = part.split('\n')
                            final_text = '\n'.join(lines[1:]).strip()
                            if final_text:
                                st.subheader("📋 העתק-הדבק (טקסט נקי)")
                                st.text_area("תיאור סופי להעתקה", final_text, height=300, key="final_copy")
                                break
                except Exception as e:
                    pass  # Full markdown is still displayed above
                    
            # Download button
            st.download_button(
                label="💾 הורד כקובץ טקסט",
                data=final_output,
                file_name=f"{brand_input}_{model_input}_description.txt",
                mime="text/plain"
            )

# Footer
st.markdown("---")
st.caption("🚀 מופעל על ידי Google Gemini & Google Custom Search API | נוצר עבור בוטיקי בשמים יוקרתיים")
