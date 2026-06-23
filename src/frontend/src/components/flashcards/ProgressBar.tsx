'use client';

interface ProgressBarProps {
  current: number;
  total: number;
  className?: string;
}

export default function ProgressBar({ current, total, className = '' }: ProgressBarProps) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
  
  const getColorClass = () => {
    if (percentage >= 80) return 'bg-green-500';
    if (percentage >= 50) return 'bg-amber-500';
    return 'bg-primary';
  };

  return (
    <div className={`w-full ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-muted-foreground">
          Tiến độ học tập
        </span>
        <span className="text-sm font-medium text-foreground">
          {current} / {total} thẻ
        </span>
      </div>
      
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${getColorClass()}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      
      <div className="mt-1 text-xs text-muted-foreground text-right">
        {percentage}% hoàn thành
      </div>
    </div>
  );
}