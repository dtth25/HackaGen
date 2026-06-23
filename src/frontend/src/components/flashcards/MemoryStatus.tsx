'use client';

import { MemoryStatus } from '@/lib/flashcards/types';

interface MemoryStatusProps {
  currentStatus?: MemoryStatus;
  onStatusChange: (status: MemoryStatus) => void;
}

export default function MemoryStatus({
  currentStatus,
  onStatusChange,
}: MemoryStatusProps) {
  const statuses: { value: MemoryStatus; label: string; emoji: string; color: string }[] =
    [
      { value: 'remembered', label: 'Đã nhớ', emoji: '✅', color: 'bg-green-500' },
      {
        value: 'partial',
        label: 'Nhớ một phần',
        emoji: '⚠️',
        color: 'bg-amber-500',
      },
      { value: 'forgot', label: 'Chưa nhớ', emoji: '❌', color: 'bg-red-500' },
    ];

  return (
    <div className="flex items-center justify-center gap-3 mt-6">
      <span className="text-sm text-muted-foreground">Trạng thái:</span>
      {statuses.map(({ value, label, emoji, color }) => (
        <button
          key={value}
          onClick={() => onStatusChange(value)}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all ${
            currentStatus === value
              ? `${color} text-white shadow-md scale-105`
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          }`}
        >
          <span>{emoji}</span>
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}