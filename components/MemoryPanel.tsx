'use client';

import { useState, useEffect } from 'react';

interface Memory {
    id: string;
    category: string;
    key: string;
    value: string;
    source: string;
    importance: number;
    timestamp: string;
}

const CATEGORY_ICONS: Record<string, string> = {
    personal: '👤',
    family: '👨‍👩‍👧',
    tech: '💻',
    work: '💼',
    preferences: '⚙️'
};

const CATEGORY_COLORS: Record<string, string> = {
    personal: 'border-blue-500/30 bg-blue-500/10',
    family: 'border-pink-500/30 bg-pink-500/10',
    tech: 'border-emerald-500/30 bg-emerald-500/10',
    work: 'border-amber-500/30 bg-amber-500/10',
    preferences: 'border-purple-500/30 bg-purple-500/10'
};

export function MemoryPanel() {
    const [memories, setMemories] = useState<Memory[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);
    const [conflicts, setConflicts] = useState<any[]>([]);

    useEffect(() => {
        loadMemories();
        checkConflicts();
    }, []);

    const loadMemories = async () => {
        try {
            const res = await fetch('http://127.0.0.1:8765/memory');
            const data = await res.json();
            setMemories(data.memories || []);
        } catch (error) {
            console.error('Failed to load memories:', error);
        } finally {
            setLoading(false);
        }
    };

    const checkConflicts = async () => {
        try {
            const res = await fetch('http://127.0.0.1:8765/memory/conflicts');
            const data = await res.json();
            setConflicts(data.conflicts || []);
        } catch (error) {
            console.error('Failed to check conflicts:', error);
        }
    };

    const deleteMemory = async (id: string) => {
        if (!confirm('Delete this memory?')) return;

        try {
            await fetch(`http://127.0.0.1:8765/memory/${id}`, {
                method: 'DELETE'
            });
            loadMemories();
        } catch (error) {
            console.error('Failed to delete:', error);
        }
    };

    const clearAll = async () => {
        if (!confirm('⚠️ DANGER: Delete ALL memories? This cannot be undone!')) return;

        try {
            await fetch('http://127.0.0.1:8765/memory/clear', {
                method: 'POST'
            });
            loadMemories();
        } catch (error) {
            console.error('Failed to clear:', error);
        }
    };

    const filteredMemories = memories.filter(m =>
        m.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.value.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const groupedByCategory = filteredMemories.reduce((acc, mem) => {
        if (!acc[mem.category]) acc[mem.category] = [];
        acc[mem.category].push(mem);
        return acc;
    }, {} as Record<string, Memory[]>);

    const formatDate = (timestamp: string) => {
        try {
            return new Date(timestamp).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return timestamp;
        }
    };

    if (loading) {
        return (
            <div className="text-center text-slate-400 py-8">
                Loading memories...
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-lg font-semibold text-slate-100">
                        💾 Saved Memories ({memories.length})
                    </h2>
                    <p className="text-xs text-slate-500 mt-1">
                        Auto-extracted personal info from conversations
                    </p>
                </div>
            </div>

            {/* Conflict Warning */}
            {conflicts.length > 0 && (
                <div className="rounded-lg border border-amber-600/50 bg-amber-900/20 p-3">
                    <span className="text-amber-400 text-sm">
                        ⚠️ {conflicts.length} conflicting memories detected! Review and update.
                    </span>
                </div>
            )}

            {/* Search */}
            <div className="relative">
                <svg
                    className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                </svg>
                <input
                    type="text"
                    placeholder="Search memories..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 rounded-lg border border-slate-700 bg-slate-800 text-slate-100 text-sm placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none"
                />
            </div>

            {/* Memory Groups */}
            {Object.keys(groupedByCategory).length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                    <p className="text-4xl mb-4">🧠</p>
                    <p className="text-sm">No memories yet.</p>
                    <p className="text-xs mt-2">
                        Share personal info in chat and it will be auto-saved here.
                    </p>
                </div>
            ) : (
                <div className="space-y-4">
                    {Object.entries(groupedByCategory).map(([category, items]) => (
                        <div
                            key={category}
                            className={`rounded-lg border p-4 ${CATEGORY_COLORS[category] || 'border-slate-700 bg-slate-800/50'}`}
                        >
                            <h3 className="text-sm font-medium text-slate-200 mb-3">
                                {CATEGORY_ICONS[category] || '📁'} {category.charAt(0).toUpperCase() + category.slice(1)}
                            </h3>

                            <div className="space-y-2">
                                {items.map(mem => (
                                    <div
                                        key={mem.id}
                                        className="rounded-md bg-slate-900/60 p-3 flex justify-between items-start gap-3"
                                    >
                                        <div className="flex-1 min-w-0">
                                            <div className="text-sm text-slate-100">
                                                <span className="font-medium text-slate-300">{mem.key}:</span>{' '}
                                                <span>{mem.value}</span>
                                            </div>
                                            <div className="text-xs text-slate-500 mt-1 flex items-center gap-2">
                                                <span>{formatDate(mem.timestamp)}</span>
                                                <span>·</span>
                                                <span className="capitalize">{mem.source.replace('_', ' ')}</span>
                                                <span>·</span>
                                                <span>{'⭐'.repeat(Math.min(mem.importance, 3))}</span>
                                            </div>
                                        </div>

                                        <button
                                            onClick={() => deleteMemory(mem.id)}
                                            className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                                            title="Delete memory"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Danger Zone */}
            {memories.length > 0 && (
                <div className="rounded-lg border border-red-900/50 bg-red-900/10 p-4 mt-8">
                    <h3 className="text-sm font-medium text-red-400 mb-2">⚠️ Danger Zone</h3>
                    <button
                        onClick={clearAll}
                        className="px-4 py-2 rounded-md border border-red-700/50 bg-red-900/30 text-sm text-red-300 hover:bg-red-800/40 transition-colors"
                    >
                        Clear All Memories
                    </button>
                </div>
            )}
        </div>
    );
}
