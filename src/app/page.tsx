"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  SprayCan, Tag, VenusAndMars, Leaf, CalendarDays, 
  Info, Key, Sparkles, Copy, RefreshCw, Loader2
} from "lucide-react";
import gsap from "gsap";

const GEMINI_API_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent';
const API_KEY_STORAGE = 'gemini_api_key';

export default function PerfumeGenerator() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [formData, setFormData] = useState({
    name: "",
    type: "",
    notes: "",
    occasion: "",
    additionalInfo: "",
    apiKey: ""
  });
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedText, setGeneratedText] = useState("");
  const [isCopied, setIsCopied] = useState(false);

  useEffect(() => {
    const savedApiKey = localStorage.getItem(API_KEY_STORAGE);
    if (savedApiKey) {
      setFormData(prev => ({ ...prev, apiKey: savedApiKey }));
    }
    
    const ctx = gsap.context(() => {
      gsap.from(".header-anim", { y: -30, opacity: 0, duration: 0.8, ease: "power3.out" });
      gsap.from(".card-anim", { y: 30, opacity: 0, duration: 0.8, stagger: 0.2, ease: "power3.out", delay: 0.2 });
    }, containerRef);
    
    return () => ctx.revert();
  }, []);

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.apiKey || !formData.name || !formData.type || !formData.notes) return;
    
    localStorage.setItem(API_KEY_STORAGE, formData.apiKey);
    setIsGenerating(true);
    setGeneratedText("");

    try {
      const prompt = `אתה מומחה בתחום הבשמים ויוצר תיאורים מקצועיים ומרתקים לבשמים.

צור תיאור מפורט ומקצועי לבושם הבא:

שם הבושם: ${formData.name}
סוג: ${formData.type}
תווי ריח עיקריים: ${formData.notes}
${formData.occasion ? `אירוע/עונה: ${formData.occasion}` : ''}
${formData.additionalInfo ? `מידע נוסף: ${formData.additionalInfo}` : ''}

התיאור צריך לכלול:
1. פתיחה מרתקת שמושכת את הקורא
2. תיאור מפורט של תווי הריח (ראש, לב, בסיס)
3. האווירה והרגש שהבושם מעורר
4. למי הבושם מתאים (אישיות, סגנון חיים)
5. המלצות לשימוש (זמן, אירוע)
6. סיום מעורר השראה

כתוב בעברית, בסגנון מקצועי אך חם ומזמין. השתמש בשפה עשירה ותיאורים חושניים.`;

      const response = await fetch(`${GEMINI_API_ENDPOINT}?key=${formData.apiKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.9, topK: 40, topP: 0.95, maxOutputTokens: 1024 }
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error?.message || 'שגיאה בקריאה ל-API');
      }
      
      const result = await response.json();
      const text = result.candidates[0].content.parts[0].text;
      
      setGeneratedText(text);
      
      // Animate output section
      setTimeout(() => {
        gsap.fromTo(".output-anim", { y: 20, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: "power2.out" });
        document.getElementById('outputSection')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
      
    } catch (error: any) {
      alert(`שגיאה: ${error.message}\n\nאנא בדוק את מפתח ה-API שלך.`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(generatedText);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      alert("שגיאה בהעתקה");
    }
  };

  const handleNew = () => {
    setGeneratedText("");
    setFormData(prev => ({ ...prev, name: "", type: "", notes: "", occasion: "", additionalInfo: "" }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="relative min-h-screen text-foreground" dir="rtl" ref={containerRef}>
      {/* Background Animation */}
      <div className="bg-animation">
        {[1, 2, 3, 4, 5].map(i => <div key={i} className="bubble"></div>)}
      </div>

      <div className="container max-w-3xl mx-auto py-12 px-4 relative z-10">
        {/* Header */}
        <header className="header-anim text-center mb-12">
          <div className="flex items-center justify-center gap-4 mb-4">
            <SprayCan className="w-12 h-12 text-purple-400" />
            <h1 className="text-4xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-pink-500 pb-2">
              מחולל תיאורי בשמים
            </h1>
          </div>
          <p className="text-lg text-foreground font-light">
            צור תיאורים מקצועיים ויצירתיים לבשמים באמצעות בינה מלאכותית
          </p>
        </header>

        {/* Form Card */}
        <Card className="card-anim shadow-lg border border-border mb-8 bg-card">
          <CardHeader>
            <CardTitle className="text-2xl flex items-center gap-2 text-foreground">
              <Sparkles className="w-6 h-6 text-purple-400" />
              פרטי הבושם
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleGenerate} className="space-y-6">
              
              <div className="space-y-2 text-right">
                <Label htmlFor="perfumeName" className="flex items-center gap-2 text-foreground">
                  <Tag className="w-4 h-4 text-purple-400" /> שם הבושם
                </Label>
                <Input 
                  id="perfumeName" 
                  value={formData.name}
                  onChange={(e) => handleChange("name", e.target.value)}
                  placeholder="לדוגמה: Midnight Rose" 
                  required 
                  className="bg-background border-border focus-visible:ring-purple-500 text-foreground placeholder:text-muted-foreground text-right"
                />
              </div>

              <div className="space-y-2 text-right">
                <Label className="flex items-center gap-2 text-foreground">
                  <VenusAndMars className="w-4 h-4 text-purple-400" /> סוג הבושם
                </Label>
                <Select value={formData.type} onValueChange={(val) => handleChange("type", val || "")} required>
                  <SelectTrigger className="bg-background border-border text-foreground focus:ring-purple-500 text-right text-base flex-row-reverse justify-between">
                    <SelectValue placeholder="בחר סוג" />
                  </SelectTrigger>
                  <SelectContent className="bg-background border-border text-foreground" dir="rtl">
                    <SelectItem value="לנשים">לנשים</SelectItem>
                    <SelectItem value="לגברים">לגברים</SelectItem>
                    <SelectItem value="יוניסקס">יוניסקס</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 text-right">
                <Label htmlFor="perfumeNotes" className="flex items-center gap-2 text-foreground">
                  <Leaf className="w-4 h-4 text-purple-400" /> תווי ריח עיקריים
                </Label>
                <Textarea 
                  id="perfumeNotes" 
                  value={formData.notes}
                  onChange={(e) => handleChange("notes", e.target.value)}
                  placeholder="לדוגמה: ורד, וניל, עץ סנדל, ברגמוט" 
                  required 
                  className="bg-background border-border focus-visible:ring-purple-500 text-foreground min-h-[80px] placeholder:text-muted-foreground text-right"
                />
              </div>

              <div className="space-y-2 text-right">
                <Label htmlFor="perfumeOccasion" className="flex items-center gap-2 text-foreground">
                  <CalendarDays className="w-4 h-4 text-purple-400" /> אירוע/עונה
                </Label>
                <Input 
                  id="perfumeOccasion" 
                  value={formData.occasion}
                  onChange={(e) => handleChange("occasion", e.target.value)}
                  placeholder="לדוגמה: ערב, קיץ, יום יום" 
                  className="bg-background border-border focus-visible:ring-purple-500 text-foreground placeholder:text-muted-foreground text-right"
                />
              </div>

              <div className="space-y-2 text-right">
                <Label htmlFor="additionalInfo" className="flex items-center gap-2 text-foreground">
                  <Info className="w-4 h-4 text-purple-400" /> מידע נוסף (אופציונלי)
                </Label>
                <Textarea 
                  id="additionalInfo" 
                  value={formData.additionalInfo}
                  onChange={(e) => handleChange("additionalInfo", e.target.value)}
                  placeholder="כל מידע נוסף שתרצה להוסיף..." 
                  className="bg-background border-border focus-visible:ring-purple-500 text-foreground placeholder:text-muted-foreground text-right"
                />
              </div>

              <div className="space-y-2 pt-4 border-t border-border text-right">
                <Label htmlFor="apiKey" className="flex items-center gap-2 text-foreground">
                  <Key className="w-4 h-4 text-purple-400" /> Google Gemini API Key
                </Label>
                <Input 
                  id="apiKey" 
                  type="password"
                  value={formData.apiKey}
                  onChange={(e) => handleChange("apiKey", e.target.value)}
                  placeholder="הזן את מפתח ה-API שלך" 
                  required 
                  className="bg-background border-border focus-visible:ring-purple-500 text-foreground placeholder:text-muted-foreground text-right"
                  dir="ltr"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  <a href="https://makersuite.google.com/app/apikey" target="_blank" rel="noreferrer" className="text-purple-400 hover:underline">
                    קבל מפתח API חינמי
                  </a>
                </p>
              </div>

              <Button 
                type="submit" 
                disabled={isGenerating}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-foreground font-semibold py-6 rounded-xl shadow-[0_4px_16px_rgba(139,92,246,0.3)] hover:shadow-[0_6px_24px_rgba(139,92,246,0.4)] transition-all duration-300 text-lg border-0"
              >
                {isGenerating ? (
                  <><Loader2 className="w-5 h-5 ml-2 animate-spin" /> יוצר תיאור...</>
                ) : (
                  <><Sparkles className="w-5 h-5 ml-2" /> צור תיאור</>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Output Section */}
        {generatedText && (
          <Card id="outputSection" className="output-anim shadow-lg border border-border mb-8 bg-card">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border pb-4">
              <CardTitle className="text-xl flex items-center gap-2 text-foreground">
                <Sparkles className="w-5 h-5 text-purple-400" /> התיאור שנוצר
              </CardTitle>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleCopy}
                className="bg-background border-border hover:bg-white/10 text-foreground"
              >
                {isCopied ? <span className="text-green-400">הועתק!</span> : <><Copy className="w-4 h-4 ml-2" /> העתק</>}
              </Button>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="bg-card rounded-xl p-6 mb-6 text-foreground whitespace-pre-wrap leading-relaxed border border-border text-right">
                {generatedText}
              </div>
              <div className="flex justify-center">
                <Button 
                  variant="secondary" 
                  onClick={handleNew}
                  className="bg-white/10 hover:bg-white/20 text-foreground border-border border"
                >
                  <RefreshCw className="w-4 h-4 ml-2" /> צור תיאור חדש
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <footer className="text-center text-muted-foreground text-sm mt-12 pb-8 border-t border-border pt-8">
          <p>מופעל על ידי <strong className="text-purple-400">Google Gemini AI</strong></p>
          <p className="mt-1">המידע נשמר באופן מקומי בדפדפן שלך בלבד</p>
        </footer>
      </div>
    </div>
  );
}


