import React, { useState } from 'react';
import { 
  Plus, 
  Search, 
  Trash2, 
  Edit3, 
  Check, 
  X, 
  MessageSquare,
  Activity
} from 'lucide-react';

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
  searchQuery,
  onSearchChange
}) {
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");

  const handleStartRename = (e, c) => {
    e.stopPropagation();
    setEditingId(c.id);
    setEditTitle(c.title);
  };

  const handleSaveRename = (e, id) => {
    e.stopPropagation();
    if (editTitle.trim()) {
      onRename(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e) => {
    e.stopPropagation();
    setEditingId(null);
  };

  // Group by date
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterdayStart = todayStart - 24 * 60 * 60 * 1000;
  const sevenDaysAgoStart = todayStart - 7 * 24 * 60 * 60 * 1000;

  const filtered = conversations.filter(c => 
    (c.title || "").toLowerCase().includes((searchQuery || "").toLowerCase())
  );

  const groups = {
    "Today": [],
    "Yesterday": [],
    "Previous 7 Days": [],
    "Older": []
  };

  filtered.forEach(c => {
    const timestamp = new Date(c.created_at).getTime();
    if (timestamp >= todayStart) {
      groups["Today"].push(c);
    } else if (timestamp >= yesterdayStart) {
      groups["Yesterday"].push(c);
    } else if (timestamp >= sevenDaysAgoStart) {
      groups["Previous 7 Days"].push(c);
    } else {
      groups["Older"].push(c);
    }
  });

  return (
    <aside className="w-80 bg-slate-900 border-r border-slate-800 flex flex-col text-slate-300 h-full select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800 flex items-center gap-3">
        <div className="bg-sky-500/10 p-2 rounded-xl border border-sky-500/20 text-sky-400">
          <Activity className="h-5 w-5 animate-pulse" />
        </div>
        <div>
          <h1 className="font-bold text-sm tracking-tight text-white">Symptom Triage</h1>
          <span className="text-[10px] text-slate-500 font-semibold tracking-wider uppercase">Multi-Agent System</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="p-4 space-y-3">
        <button
          onClick={onCreate}
          className="w-full bg-sky-500 hover:bg-sky-600 active:bg-sky-700 text-white font-medium py-2.5 px-4 rounded-xl flex items-center justify-center gap-2 transition-all duration-150 shadow-lg shadow-sky-500/10 text-sm"
        >
          <Plus className="h-4 w-4" /> New Triage Chat
        </button>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search conversations..."
            className="w-full bg-slate-950 border border-slate-850 rounded-xl py-2 pl-9 pr-4 text-xs placeholder-slate-600 focus:outline-none focus:border-sky-500/50 transition-colors"
          />
        </div>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-4">
        {Object.entries(groups).map(([groupName, items]) => {
          if (items.length === 0) return null;
          return (
            <div key={groupName} className="space-y-1">
              <h3 className="px-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                {groupName}
              </h3>
              <div className="space-y-0.5">
                {items.map(c => {
                  const isActive = c.id === activeId;
                  const isEditing = c.id === editingId;

                  return (
                    <div
                      key={c.id}
                      onClick={() => !isEditing && onSelect(c.id)}
                      className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium cursor-pointer transition-all duration-150 ${
                        isActive
                          ? 'bg-slate-800 text-white border-l-2 border-sky-400'
                          : 'hover:bg-slate-850/50 text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      <MessageSquare className={`h-4 w-4 flex-shrink-0 ${isActive ? 'text-sky-400' : 'text-slate-600'}`} />
                      
                      {isEditing ? (
                        <div className="flex items-center gap-1.5 flex-1 pr-12">
                          <input
                            type="text"
                            value={editTitle}
                            onChange={(e) => setEditTitle(e.target.value)}
                            onClick={(e) => e.stopPropagation()}
                            onKeyDown={(e) => e.key === 'Enter' && handleSaveRename(e, c.id)}
                            className="bg-slate-950 border border-sky-500/50 text-white rounded-md py-0.5 px-2 text-xs focus:outline-none w-full"
                            autoFocus
                          />
                          <button
                            onClick={(e) => handleSaveRename(e, c.id)}
                            className="text-emerald-400 hover:text-emerald-300 p-0.5"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={handleCancelRename}
                            className="text-rose-400 hover:text-rose-300 p-0.5"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <span className="truncate flex-1 pr-12 text-slate-300 group-hover:text-white">
                          {c.title || "Untitled Session"}
                        </span>
                      )}

                      {/* Hover controls */}
                      {!isEditing && (
                        <div className="absolute right-2 opacity-0 group-hover:opacity-100 flex items-center gap-1 transition-opacity duration-100 bg-slate-900 group-hover:bg-transparent pl-2">
                          <button
                            onClick={(e) => handleStartRename(e, c)}
                            className="text-slate-500 hover:text-slate-300 p-1 hover:bg-slate-850 rounded"
                            title="Rename"
                          >
                            <Edit3 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onDelete(c.id);
                            }}
                            className="text-slate-500 hover:text-rose-400 p-1 hover:bg-slate-850 rounded"
                            title="Delete"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="text-center py-8 text-xs text-slate-600">
            No conversations found.
          </div>
        )}
      </div>
    </aside>
  );
}
