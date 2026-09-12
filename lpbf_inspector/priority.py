"""Score de priorité explicable, indépendant des décisions et de la calibration."""
import math

PRIORITY_HELP = (
    'Priority score / 100: 100 × √(V × P), with V = r / (r + 2) and P = n / (n + 3). '
    'r is the peak detection-threshold ratio; n is consecutive persistence. '
    'Both components have equal weight. This review score depends on the job settings; '
    'it is neither a defect probability nor a measure of material severity.'
)


def components(ratio, count):
    r, n = float(ratio), int(count)
    if not math.isfinite(r) or r < 0 or n < 1:
        raise ValueError('Invalid score intensity or persistence.')
    return r / (r + 2), n / (n + 3)


def priority_value(ratio, count):
    v, p = components(ratio, count)
    return round(100 * math.sqrt(v * p), 1)


def with_priority(event):
    row = dict(event)
    n = row.get('consecutive_count', row['end_layer'] - row['start_layer'] + 1)
    v, p = components(row['score'], n)
    row.update(consecutive_count=n, priority_score=priority_value(row['score'], n),
               variation_component=round(100*v, 1), persistence_component=round(100*p, 1))
    return row


def review_sort(value):
    if value not in {'layer', 'priority'}:
        raise ValueError('Unknown review order.')
    return value


def priority_text(event):
    row = with_priority(event)
    return (f"Priority {row['priority_score']:.1f} / 100 · intensity × {row['score']:.2f} "
            f"· persistence: {row['consecutive_count']} consecutive comparable image(s)")
