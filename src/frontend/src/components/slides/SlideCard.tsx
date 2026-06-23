import { Slide } from '@/lib/slides/types';

interface SlideCardProps {
  slide: Slide;
}

export default function SlideCard({ slide }: SlideCardProps) {
  const renderContent = () => {
    switch (slide.content.type) {
      case 'bullets':
        return (
          <ul className="space-y-3">
            {slide.content.items?.map((item, idx) => (
              <li key={idx} className="flex items-start gap-3">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                <span className="text-foreground leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>
        );

      case 'title-only':
        return (
          <div className="flex items-center justify-center h-full">
            <p className="text-3xl font-bold text-center text-foreground">
              {slide.content.mainText}
            </p>
          </div>
        );

      case 'two-column':
        return (
          <div className="grid grid-cols-2 gap-8 h-full">
            <div className="space-y-2">
              {slide.content.leftColumn?.map((text, idx) => (
                <p
                  key={idx}
                  className={`leading-relaxed ${
                    idx === 0
                      ? 'text-xl font-semibold text-primary'
                      : 'text-foreground'
                  }`}
                >
                  {text}
                </p>
              ))}
            </div>
            <div className="space-y-2">
              {slide.content.rightColumn?.map((text, idx) => (
                <p
                  key={idx}
                  className={`leading-relaxed ${
                    idx === 0
                      ? 'text-xl font-semibold text-primary'
                      : 'text-foreground'
                  }`}
                >
                  {text}
                </p>
              ))}
            </div>
          </div>
        );

      default:
        return <p className="text-foreground">No content</p>;
    }
  };

  return (
    <div className="w-full aspect-video bg-card rounded-xl border border-border shadow-2xl p-10 flex flex-col">
      {/* Title */}
      <h2 className="text-3xl font-bold text-foreground mb-6 pb-4 border-b border-border">
        {slide.title}
      </h2>

      {/* Content */}
      <div className="flex-1 overflow-auto">{renderContent()}</div>

      {/* Footer: suggestions + citations */}
      <div className="mt-6 pt-4 border-t border-border flex items-start justify-between">
        <div className="space-y-1">
          {slide.layoutSuggestion && (
            <p className="text-xs text-muted-foreground">
              💡 {slide.layoutSuggestion}
            </p>
          )}
          {slide.imageSuggestion && (
            <p className="text-xs text-muted-foreground">
              🖼️ {slide.imageSuggestion}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {slide.citations.map((citation) => (
            <span
              key={citation.chunk_id}
              className="inline-flex items-center gap-1 text-xs text-muted-foreground bg-muted px-2 py-1 rounded"
            >
              📄 Trang {citation.page}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}