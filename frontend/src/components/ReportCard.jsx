import React from 'react';
import { 
  FileText, 
  Search, 
  AlertTriangle, 
  CheckSquare, 
  ShieldAlert, 
  Activity,
  Heart
} from 'lucide-react';

export default function ReportCard({ content }) {
  if (!content) return null;

  // Simple, robust markdown section splitter
  // Splits by '### ' and parses headers
  const sections = content.split(/###\s+/);
  
  const parsedSections = {};
  
  sections.forEach(section => {
    const lines = section.trim().split('\n');
    const header = lines[0].trim();
    const body = lines.slice(1).join('\n').trim();
    
    if (header && body) {
      // Normalize header key
      if (header.includes('Symptom Summary') || header.includes('Summary')) {
        parsedSections.summary = body;
      } else if (header.includes('Specialist Findings') || header.includes('Findings')) {
        parsedSections.findings = body;
      } else if (header.includes('Urgency') || header.includes('Risk Level')) {
        parsedSections.risk = body;
      } else if (header.includes('Actions') || header.includes('Recommendation')) {
        parsedSections.actions = body;
      } else if (header.includes('Disclaimer')) {
        parsedSections.disclaimer = body;
      }
    }
  });

  // If parsing didn't segment anything, render the raw content safely
  const isParsed = Object.keys(parsedSections).length > 0;

  const renderMarkdownBody = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, idx) => {
      const trimmed = line.trim();
      if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
        // Bullet point
        const contentStr = trimmed.substring(1).trim();
        // Bold parsing
        return (
          <li key={idx} className="ml-4 list-disc text-sm text-slate-700 dark:text-slate-300 mb-1">
            {parseBoldText(contentStr)}
          </li>
        );
      }
      if (trimmed.startsWith('####')) {
        return (
          <h4 key={idx} className="text-md font-bold text-sky-600 dark:text-sky-400 mt-3 mb-1">
            {trimmed.replace(/####/g, '').trim()}
          </h4>
        );
      }
      if (trimmed) {
        return (
          <p key={idx} className="text-sm text-slate-700 dark:text-slate-300 mb-2 leading-relaxed">
            {parseBoldText(trimmed)}
          </p>
        );
      }
      return null;
    });
  };

  const parseBoldText = (text) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-bold text-slate-900 dark:text-slate-100">{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  const getRiskStyles = (text) => {
    const lower = text.toLowerCase();
    if (lower.includes('critical')) {
      return {
        badgeBg: 'bg-rose-100 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-300 dark:border-rose-900/50',
        cardBg: 'bg-rose-50/50 dark:bg-rose-950/10 border-rose-200 dark:border-rose-950/20',
        label: 'CRITICAL'
      };
    }
    if (lower.includes('high')) {
      return {
        badgeBg: 'bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-300 dark:border-amber-900/50',
        cardBg: 'bg-amber-50/50 dark:bg-amber-950/10 border-amber-200 dark:border-amber-950/20',
        label: 'HIGH'
      };
    }
    if (lower.includes('medium')) {
      return {
        badgeBg: 'bg-yellow-100 dark:bg-yellow-950/40 text-yellow-700 dark:text-yellow-400 border-yellow-300 dark:border-yellow-900/50',
        cardBg: 'bg-yellow-50/50 dark:bg-yellow-950/10 border-yellow-200 dark:border-yellow-950/20',
        label: 'MEDIUM'
      };
    }
    return {
      badgeBg: 'bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-300 dark:border-emerald-900/50',
      cardBg: 'bg-emerald-50/50 dark:bg-emerald-950/10 border-emerald-200 dark:border-emerald-950/20',
      label: 'LOW'
    };
  };

  if (!isParsed) {
    // Fallback renderer
    return (
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-md max-w-3xl mx-auto w-full report-markdown">
        <div className="flex items-center gap-2 pb-4 mb-4 border-b border-slate-100 dark:border-slate-800">
          <Activity className="h-5 w-5 text-sky-500" />
          <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">Symptom Triage Report</h2>
        </div>
        <div className="text-slate-700 dark:text-slate-300 text-sm whitespace-pre-wrap leading-relaxed">
          {content}
        </div>
      </div>
    );
  }

  const riskStyles = getRiskStyles(parsedSections.risk || 'low');

  return (
    <div className="space-y-6 max-w-3xl mx-auto w-full mb-8">
      {/* Header Badge */}
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <Heart className="h-5 w-5 text-rose-500 fill-rose-500 animate-pulse" />
          <span className="font-semibold text-slate-800 dark:text-slate-200">Symptom Assessment Completed</span>
        </div>
        <div className={`px-3 py-1 rounded-full text-xs font-bold border ${riskStyles.badgeBg}`}>
          {riskStyles.label} URGENCY
        </div>
      </div>

      {/* Summary Card */}
      {parsedSections.summary && (
        <div className="bg-sky-50/40 dark:bg-sky-950/10 border border-sky-100 dark:border-sky-900/20 rounded-2xl p-5 shadow-sm">
          <h3 className="flex items-center gap-2 text-sm font-bold text-sky-800 dark:text-sky-400 uppercase tracking-wider mb-3">
            <FileText className="h-4 w-4" /> Symptom Summary
          </h3>
          <div className="space-y-2">
            {renderMarkdownBody(parsedSections.summary)}
          </div>
        </div>
      )}

      {/* Specialist Findings Card */}
      {parsedSections.findings && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
          <h3 className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-3">
            <Search className="h-4 w-4 text-slate-500" /> Clinical Specialist Findings
          </h3>
          <div className="space-y-3">
            {renderMarkdownBody(parsedSections.findings)}
          </div>
        </div>
      )}

      {/* Risk Level Card */}
      {parsedSections.risk && (
        <div className={`border rounded-2xl p-5 shadow-sm transition-all duration-200 ${riskStyles.cardBg}`}>
          <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider mb-2 text-slate-800 dark:text-slate-200">
            <AlertTriangle className="h-4 w-4" /> Urgency & Risk Level
          </h3>
          <div className="space-y-2">
            {renderMarkdownBody(parsedSections.risk)}
          </div>
        </div>
      )}

      {/* Recommendations Card */}
      {parsedSections.actions && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm">
          <h3 className="flex items-center gap-2 text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-3">
            <CheckSquare className="h-4 w-4 text-emerald-500" /> Recommended Actions
          </h3>
          <ul className="space-y-1">
            {renderMarkdownBody(parsedSections.actions)}
          </ul>
        </div>
      )}

      {/* Disclaimer Card */}
      {parsedSections.disclaimer && (
        <div className="bg-slate-50 dark:bg-slate-950/20 border border-slate-200 dark:border-slate-800/80 rounded-2xl p-5 shadow-sm">
          <h3 className="flex items-center gap-2 text-sm font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider mb-3">
            <ShieldAlert className="h-4 w-4" /> Medical Disclaimer
          </h3>
          <div className="text-slate-600 dark:text-slate-400 italic text-xs leading-relaxed">
            {renderMarkdownBody(parsedSections.disclaimer)}
          </div>
        </div>
      )}
    </div>
  );
}
