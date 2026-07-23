// ===== Configuration =====
const GEMINI_API_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent';

// ===== DOM Elements =====
const perfumeForm = document.getElementById('perfumeForm');
const generateBtn = document.getElementById('generateBtn');
const outputSection = document.getElementById('outputSection');
const outputContent = document.getElementById('outputContent');
const loadingOverlay = document.getElementById('loadingOverlay');
const copyBtn = document.getElementById('copyBtn');
const newGenerationBtn = document.getElementById('newGenerationBtn');

// ===== Local Storage for API Key =====
const API_KEY_STORAGE = 'gemini_api_key';

// Load saved API key on page load
window.addEventListener('DOMContentLoaded', () => {
    const savedApiKey = localStorage.getItem(API_KEY_STORAGE);
    if (savedApiKey) {
        document.getElementById('apiKey').value = savedApiKey;
    }
});

// ===== Form Submission =====
perfumeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Get form values
    const formData = {
        name: document.getElementById('perfumeName').value.trim(),
        type: document.getElementById('perfumeType').value,
        notes: document.getElementById('perfumeNotes').value.trim(),
        occasion: document.getElementById('perfumeOccasion').value.trim(),
        additionalInfo: document.getElementById('additionalInfo').value.trim(),
        apiKey: document.getElementById('apiKey').value.trim()
    };
    
    // Save API key to local storage
    localStorage.setItem(API_KEY_STORAGE, formData.apiKey);
    
    // Generate perfume description
    await generatePerfumeDescription(formData);
});

// ===== Generate Perfume Description =====
async function generatePerfumeDescription(data) {
    // Show loading overlay
    loadingOverlay.style.display = 'flex';
    generateBtn.disabled = true;
    
    try {
        // Create prompt for Gemini
        const prompt = createPrompt(data);
        
        // Call Gemini API
        const response = await fetch(`${GEMINI_API_ENDPOINT}?key=${data.apiKey}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: prompt
                    }]
                }],
                generationConfig: {
                    temperature: 0.9,
                    topK: 40,
                    topP: 0.95,
                    maxOutputTokens: 1024,
                }
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error?.message || 'שגיאה בקריאה ל-API');
        }
        
        const result = await response.json();
        const generatedText = result.candidates[0].content.parts[0].text;
        
        // Display result
        displayResult(generatedText);
        
    } catch (error) {
        console.error('Error:', error);
        alert(`שגיאה: ${error.message}\n\nאנא בדוק:\n1. שמפתח ה-API תקין\n2. שיש לך חיבור לאינטרנט\n3. שלא חרגת ממכסת ה-API`);
    } finally {
        // Hide loading overlay
        loadingOverlay.style.display = 'none';
        generateBtn.disabled = false;
    }
}

// ===== Create Prompt =====
function createPrompt(data) {
    let prompt = `אתה מומחה בתחום הבשמים ויוצר תיאורים מקצועיים ומרתקים לבשמים.

צור תיאור מפורט ומקצועי לבושם הבא:

שם הבושם: ${data.name}
סוג: ${data.type}
תווי ריח עיקריים: ${data.notes}`;

    if (data.occasion) {
        prompt += `\nאירוע/עונה: ${data.occasion}`;
    }
    
    if (data.additionalInfo) {
        prompt += `\nמידע נוסף: ${data.additionalInfo}`;
    }
    
    prompt += `

התיאור צריך לכלול:
1. פתיחה מרתקת שמושכת את הקורא
2. תיאור מפורט של תווי הריח (ראש, לב, בסיס)
3. האווירה והרגש שהבושם מעורר
4. למי הבושם מתאים (אישיות, סגנון חיים)
5. המלצות לשימוש (זמן, אירוע)
6. סיום מעורר השראה

כתוב בעברית, בסגנון מקצועי אך חם ומזמין. השתמש בשפה עשירה ותיאורים חושניים.`;

    return prompt;
}

// ===== Display Result =====
function displayResult(text) {
    outputContent.textContent = text;
    outputSection.style.display = 'block';
    
    // Smooth scroll to output
    outputSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ===== Copy to Clipboard =====
copyBtn.addEventListener('click', async () => {
    const text = outputContent.textContent;
    
    try {
        await navigator.clipboard.writeText(text);
        
        // Visual feedback
        const originalHTML = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i class="fas fa-check"></i> הועתק!';
        copyBtn.style.background = 'rgba(16, 185, 129, 0.2)';
        copyBtn.style.borderColor = '#10b981';
        
        setTimeout(() => {
            copyBtn.innerHTML = originalHTML;
            copyBtn.style.background = '';
            copyBtn.style.borderColor = '';
        }, 2000);
        
    } catch (error) {
        console.error('Failed to copy:', error);
        alert('שגיאה בהעתקה. אנא נסה שוב.');
    }
});

// ===== New Generation =====
newGenerationBtn.addEventListener('click', () => {
    outputSection.style.display = 'none';
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    // Clear form except API key
    document.getElementById('perfumeName').value = '';
    document.getElementById('perfumeType').value = '';
    document.getElementById('perfumeNotes').value = '';
    document.getElementById('perfumeOccasion').value = '';
    document.getElementById('additionalInfo').value = '';
    
    // Focus on first input
    document.getElementById('perfumeName').focus();
});

// ===== Form Validation Enhancement =====
const inputs = document.querySelectorAll('input, select, textarea');
inputs.forEach(input => {
    input.addEventListener('invalid', (e) => {
        e.preventDefault();
        input.style.borderColor = '#ef4444';
        
        setTimeout(() => {
            input.style.borderColor = '';
        }, 3000);
    });
    
    input.addEventListener('input', () => {
        input.style.borderColor = '';
    });
});
