export interface SliderProps {
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  "aria-label": string;
  /** Render the numeric value next to the slider (e.g. "60%"). */
  formatValue?: (value: number) => string;
  width?: number;
  className?: string;
}

/** Keyboard-steppable range control (native input, arrow keys work out of
 * the box). Used by Compare's opacity slider in 2C. */
export function Slider({ value, min, max, step = 1, onChange, formatValue, width = 140, className, ...rest }: SliderProps) {
  return (
    <span className={className ? `lfui-slider ${className}` : "lfui-slider"}>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        style={{ width }}
        aria-label={rest["aria-label"]}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      {formatValue && <span className="lfui-slider-value">{formatValue(value)}</span>}
    </span>
  );
}
