import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ThemeToggle from './components/ThemeToggle';
import ReportCard from './components/ReportCard';
import { 
  Send, 
  Paperclip, 
  Mic, 
  HelpCircle,
  AlertTriangle,
  Loader2,
  Activity,
  Heart
} from 'lucide-react';

const API_BASE = "/api";

export default function App() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    return saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
  });

  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [inputText, setInputText] = useState("");
  
  // Streaming states
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStage, setCurrentStage] = useState(null);
  const [streamingReport, setStreamingReport] = useState("");
  const [errorText, setErrorText] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Sync theme
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  // Fetch initial conversations
  useEffect(() => {
    fetchConversations();
  }, []);

  // Fetch messages when active ID changes
  useEffect(() => {
    if (activeId) {
      fetchMessages(activeId);
      // Reset streaming states
      setIsStreaming(false);
      setCurrentStage(null);
      setStreamingReport("");
      setErrorText(null);
    } else {
      setMessages([]);
    }
  }, [activeId]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingReport, currentStage]);

  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`);
      const data = await res.json();
      setConversations(data);
      if (data.length > 0 && !activeId) {
        setActiveId(data[0].id);
      }
    } catch (e) {
      console.error("Error fetching conversations:", e);
    }
  };

  const fetchMessages = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/conversations/${id}/messages`);
      const data = await res.json();
      setMessages(data);
    } catch (e) {
      console.error("Error fetching messages:", e);
    }
  };

  const handleCreateChat = async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: "New Triage Session" })
      });
      const newChat = await res.json();
      setConversations(prev => [newChat, ...prev]);
      setActiveId(newChat.id);
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (e) {
      console.error("Error creating chat:", e);
    }
  };

  const handleRenameChat = async (id, newTitle) => {
    try {
      await fetch(`${API_BASE}/conversations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle })
      });
      setConversations(prev => prev.map(c => c.id === id ? { ...c, title: newTitle } : c));
    } catch (e) {
      console.error("Error renaming chat:", e);
    }
  };

  const handleDeleteChat = async (id) => {
    try {
      await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' });
      setConversations(prev => prev.filter(c => c.id !== id));
      if (activeId === id) {
        setActiveId(null);
        setMessages([]);
      }
    } catch (e) {
      console.error("Error deleting chat:", e);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || isStreaming || !activeId) return;

    const userText = inputText.trim();
    setInputText("");
    setErrorText(null);
    setStreamingReport("");
    setIsStreaming(true);
    setCurrentStage({ id: "intake", text: "Analyzing symptom description..." });

    // Optimistically update UI
    setMessages(prev => [...prev, { role: 'user', content: userText }]);

    try {
      const response = await fetch(`${API_BASE}/conversations/${activeId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText })
      });

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Hold onto incomplete line

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            const dataStr = trimmed.substring(6);
            if (!dataStr) continue;
            try {
              const data = JSON.parse(dataStr);
              
              if (data.type === "stage") {
                setCurrentStage({ id: data.stage, text: data.text });
              } else if (data.type === "token") {
                if (data.agent === "report_compiler") {
                  setStreamingReport(prev => prev + data.token);
                }
              } else if (data.type === "clarification") {
                setMessages(prev => [...prev, { role: 'assistant', content: data.question }]);
                cleanupStreaming();
              } else if (data.type === "complete") {
                setMessages(prev => [...prev, { role: 'assistant', content: data.report }]);
                cleanupStreaming();
                fetchConversations(); // Update title if summary changed
              } else if (data.type === "error") {
                setErrorText(data.message);
                cleanupStreaming();
              }
            } catch (err) {
              console.error("Failed to parse event data JSON:", err, trimmed);
            }
          }
        }
      }
    } catch (err) {
      console.error("Error sending message:", err);
      setErrorText("Connection lost. Please make sure the backend server is running and try again.");
      cleanupStreaming();
    }
  };

  const cleanupStreaming = () => {
    setIsStreaming(false);
    setCurrentStage(null);
    setStreamingReport("");
  };

  const handleTextareaInput = (e) => {
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
  };

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200 overflow-hidden">
      {/* Sidebar history */}
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onCreate={handleCreateChat}
        onRename={handleRenameChat}
        onDelete={handleDeleteChat}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* Main Panel */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Header */}
        <header className="h-16 border-b border-slate-200 dark:border-slate-800 px-6 flex items-center justify-between bg-white/70 dark:bg-slate-900/50 backdrop-blur-md z-10">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <h2 className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              {activeId ? "System Active" : "Create or Select a Chat to Begin"}
            </h2>
          </div>
          <ThemeToggle darkMode={darkMode} onToggle={() => setDarkMode(!darkMode)} />
        </header>

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
          <div className="max-w-3xl mx-auto w-full space-y-6">
            
            {/* Landing page if no active conversation */}
            {!activeId && (
              <div className="text-center py-20 max-w-md mx-auto space-y-4">
                <div className="mx-auto w-12 h-12 bg-sky-100 dark:bg-sky-950/40 text-sky-500 rounded-2xl flex items-center justify-center border border-sky-200 dark:border-sky-850">
                  <Activity className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">Welcome to Symptom Triage</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  Describe your symptoms in detail (e.g. fever duration, severity, breathing conditions). Our multi-agent supervisor system will guide you through structured intake, specialist review, and risk escalation.
                </p>
                <button
                  onClick={handleCreateChat}
                  className="bg-sky-500 hover:bg-sky-600 text-white font-medium text-xs py-2 px-4 rounded-xl transition-all"
                >
                  Start Assessment Chat
                </button>
              </div>
            )}

            {/* Render history messages */}
            {activeId && messages.map((msg, idx) => {
              const isUser = msg.role === 'user';
              const isReport = msg.content.includes('Symptom Summary') || msg.content.startsWith('### ');

              if (isUser) {
                return (
                  <div key={idx} className="flex justify-end">
                    <div className="bg-sky-500 text-white rounded-2xl px-4 py-2.5 max-w-[80%] text-sm shadow-sm">
                      {msg.content}
                    </div>
                  </div>
                );
              }

              return (
                <div key={idx} className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 border border-slate-350 dark:border-slate-700 flex items-center justify-center font-bold text-xs text-slate-700 dark:text-slate-300">
                    AI
                  </div>
                  <div className="flex-1 min-w-0">
                    {isReport ? (
                      <ReportCard content={msg.content} />
                    ) : (
                      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-850 rounded-2xl px-4 py-3 text-sm text-slate-800 dark:text-slate-250 leading-relaxed shadow-sm max-w-[85%]">
                        {msg.content}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Render active stream output */}
            {isStreaming && streamingReport && (
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 border border-slate-350 dark:border-slate-700 flex items-center justify-center font-bold text-xs text-slate-700 dark:text-slate-300">
                  AI
                </div>
                <div className="flex-1 min-w-0">
                  <ReportCard content={streamingReport} />
                </div>
              </div>
            )}

            {/* Error display */}
            {errorText && (
              <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-2xl p-4 flex gap-3 text-sm text-rose-800 dark:text-rose-400">
                <AlertTriangle className="h-5 w-5 text-rose-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold">System Error</h4>
                  <p className="text-xs mt-1">{errorText}</p>
                </div>
              </div>
            )}

            {/* Anchor scroll point */}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Bar */}
        {activeId && (
          <div className="p-4 md:p-6 bg-slate-50 dark:bg-slate-950">
            <div className="max-w-3xl mx-auto space-y-2.5">
              
              {/* Active Pipeline Status Line */}
              {isStreaming && currentStage && (
                <div className="flex items-center gap-2 text-xs text-sky-600 dark:text-sky-400 font-semibold px-2">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>{currentStage.text}</span>
                </div>
              )}

              {/* Chat Input form */}
              <form 
                onSubmit={handleSendMessage}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-md p-2 flex items-end gap-2 focus-within:border-sky-500/50 transition-colors"
              >
                {/* Placeholders for voice/attach */}
                <button
                  type="button"
                  disabled
                  className="p-2 text-slate-300 dark:text-slate-700 cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800/30 rounded-xl"
                  title="Attachment (Placeholder)"
                >
                  <Paperclip className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  disabled
                  className="p-2 text-slate-300 dark:text-slate-700 cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800/30 rounded-xl"
                  title="Voice Input (Placeholder)"
                >
                  <Mic className="h-4 w-4" />
                </button>

                <textarea
                  ref={inputRef}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onInput={handleTextareaInput}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage(e);
                    }
                  }}
                  disabled={isStreaming}
                  placeholder={isStreaming ? "AI Triage pipeline executing..." : "Describe symptoms in detail..."}
                  rows={1}
                  className="flex-1 bg-transparent border-0 focus:ring-0 focus:outline-none text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-600 max-h-44 py-2 resize-none"
                />

                <button
                  type="submit"
                  disabled={!inputText.trim() || isStreaming}
                  className={`p-2.5 rounded-xl flex items-center justify-center transition-all ${
                    inputText.trim() && !isStreaming
                      ? 'bg-sky-500 text-white hover:bg-sky-600 active:scale-95 shadow-md shadow-sky-500/10'
                      : 'bg-slate-100 dark:bg-slate-850 text-slate-300 dark:text-slate-700 cursor-not-allowed'
                  }`}
                >
                  <Send className="h-4 w-4" />
                </button>
              </form>

              {/* Sticky bottom disclaimer info */}
              <div className="text-[10px] text-center text-slate-400 dark:text-slate-600 font-medium">
                🚨 This system provides automated symptom routing and does NOT replace professional medical advice. Always consult a physician.
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
