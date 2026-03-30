export function toFiniteNumber(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "string" && value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function toDateOnly(dateValue) {
  const d = new Date(dateValue);
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}

export function shiftDate(dateValue, deltaDays) {
  const dt = new Date(`${dateValue}T00:00:00`);
  if (Number.isNaN(dt.getTime())) {
    return dateValue;
  }
  dt.setDate(dt.getDate() + deltaDays);
  return toDateOnly(dt);
}

export function formatCompactCalendarLabel(value, previousValue) {
  if (!value) return "--";

  const current = new Date(`${value}T00:00:00`);
  if (Number.isNaN(current.getTime())) return String(value);

  const month = current.getMonth() + 1;
  const day = current.getDate();
  if (!previousValue) return `${month}/${day}`;

  const previous = new Date(`${previousValue}T00:00:00`);
  if (Number.isNaN(previous.getTime())) return `${month}/${day}`;

  return previous.getMonth() === current.getMonth() ? String(day) : `${month}/${day}`;
}

export function formatChartDateTick(row, index, rows) {
  return formatCompactCalendarLabel(row?.day, index > 0 ? rows[index - 1]?.day : null);
}

export function formatSignedDelta(value, digits = 1) {
  const n = toFiniteNumber(value);
  if (n === null) return "n/a";
  const sign = n > 0 ? "+" : "";
  if (Math.abs(n) >= 1000) {
    return `${sign}${Math.round(n).toLocaleString()}`;
  }
  if (Math.abs(n - Math.round(n)) < 0.05) {
    return `${sign}${Math.round(n)}`;
  }
  return `${sign}${n.toFixed(digits)}`;
}

export function chartX(index, total, frame) {
  const width = frame.width - frame.padLeft - frame.padRight;
  if (total <= 1) return frame.padLeft + width / 2;
  return frame.padLeft + (index * width) / (total - 1);
}

export function chartY(value, min, max, frame) {
  const height = frame.height - frame.padTop - frame.padBottom;
  const range = max - min || 1;
  const ratio = (value - min) / range;
  return frame.padTop + (1 - ratio) * height;
}

export function buildPathSegments(points) {
  const segments = [];
  let current = [];

  for (const point of points) {
    if (point.value === null || point.y === null) {
      if (current.length) {
        segments.push(current.join(" "));
        current = [];
      }
      continue;
    }

    const prefix = current.length === 0 ? "M" : "L";
    current.push(`${prefix}${point.x.toFixed(2)},${point.y.toFixed(2)}`);
  }

  if (current.length) {
    segments.push(current.join(" "));
  }

  return segments;
}

function formatTickNumber(value) {
  const rounded = Math.round(value);
  if (Math.abs(value - rounded) < 0.05) return String(rounded);
  return value.toFixed(1);
}

export function buildYTicks(min, max, steps, formatter = formatTickNumber, frame) {
  const ticks = [];
  const safeSteps = Math.max(1, steps);

  for (let i = 0; i <= safeSteps; i += 1) {
    const ratio = i / safeSteps;
    const value = max - (max - min) * ratio;
    ticks.push({
      value,
      y: chartY(value, min, max, frame),
      label: formatter(value),
    });
  }

  return ticks;
}

export function buildXTicks(points, labeler, maxTickCount = null) {
  if (!points.length) return [];

  let selectedIndexes = points.map((_, index) => index);
  if (typeof maxTickCount === "number" && maxTickCount >= 2 && points.length > maxTickCount) {
    const stride = Math.max(1, Math.ceil((points.length - 1) / (maxTickCount - 1)));
    selectedIndexes = [];

    for (let index = 0; index < points.length; index += stride) {
      selectedIndexes.push(index);
    }

    if (selectedIndexes[selectedIndexes.length - 1] !== points.length - 1) {
      selectedIndexes.push(points.length - 1);
    }
  }

  const rows = points.map((point) => point.raw);
  return selectedIndexes.map((pointIndex) => {
    const point = points[pointIndex];
    return {
      x: point.x,
      label: labeler(point.raw, pointIndex, rows),
      anchor: pointIndex === 0 ? "start" : (pointIndex === points.length - 1 ? "end" : "middle"),
    };
  });
}

export function buildLineChart(rows, getValue, options = {}) {
  const frame = options.frame;
  const values = rows.map((row) => toFiniteNumber(getValue(row)));
  const numeric = values.filter((value) => value !== null);

  const hasFixedMin = typeof options.fixedMin === "number";
  const hasFixedMax = typeof options.fixedMax === "number";

  let min = hasFixedMin ? options.fixedMin : (numeric.length ? Math.min(...numeric) : 0);
  let max = hasFixedMax ? options.fixedMax : (numeric.length ? Math.max(...numeric) : 1);

  if (!hasFixedMin || !hasFixedMax) {
    if (min === max) {
      const bump = min === 0 ? 1 : Math.max(1, Math.abs(min * 0.1));
      if (!hasFixedMin) min -= bump;
      if (!hasFixedMax) max += bump;
    } else {
      const padRatio = options.padRatio ?? 0.08;
      const pad = (max - min) * padRatio;
      if (!hasFixedMin) min -= pad;
      if (!hasFixedMax) max += pad;
    }
  }

  if (min === max) {
    max = min + 1;
  }

  const points = rows.map((row, index) => {
    const value = values[index];
    return {
      raw: row,
      index,
      value,
      x: chartX(index, rows.length, frame),
      y: value === null ? null : chartY(value, min, max, frame),
    };
  });

  return {
    points,
    segments: buildPathSegments(points),
    yTicks: buildYTicks(min, max, options.ySteps ?? 4, options.yFormatter, frame),
    xTicks: buildXTicks(points, options.xLabel ?? formatChartDateTick, options.xMaxTicks),
    min,
    max,
  };
}
