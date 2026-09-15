"""Score de priorité explicable, indépendant des décisions et de la calibration."""
import math

PRIORITY_HELP = (
    'Priority score / 100: weighted review score using intensity, persistence, area, part overlap and stage. '
    'Intensity uses V = r / (r + 2), where r is the peak detection-threshold ratio. '
    'Persistence uses P = n / (n + 3), where n is consecutive persistence. '
    'Default weights are intensity 35%, persistence 25%, area 15%, part overlap 20%, stage 5%. '
    'The previous intensity-persistence score is kept as legacy_priority_score for traceability. '
    'This review score depends on the job settings and photographic reconstruction; '
    'it is neither a defect probability nor a measure of material severity.'
)

DEFAULT_WEIGHTS = {'intensity': .35, 'persistence': .25, 'area': .15, 'part': .20, 'stage': .05}


def components(ratio, count):
    r, n = float(ratio), int(count)
    if not math.isfinite(r) or r < 0 or n < 1:
        raise ValueError('Invalid score intensity or persistence.')
    return r / (r + 2), n / (n + 3)


def legacy_priority_value(ratio, count):
    v, p = components(ratio, count)
    return round(100 * math.sqrt(v * p), 1)


def area_component(box):
    if not box:
        return 0.0
    x0, y0, x1, y1 = [float(v) for v in box]
    area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    return area / (area + 4096.0)


def stage_component(phase, kind=None):
    if kind in {'luminosite_globale', 'derive_globale', 'niveau_gris'}:
        return .35
    if phase == 'fusion':
        return 1.0
    if phase == 'etalement':
        return .75
    return .5


def part_component(value):
    if value is None:
        return .5
    v = float(value)
    if not math.isfinite(v):
        return .5
    return max(0.0, min(1.0, v))


def priority_value(ratio, count, box=None, part_overlap=None, phase=None, kind=None, weights=None):
    intensity, persistence = components(ratio, count)
    w = weights or DEFAULT_WEIGHTS
    value = (
        w['intensity'] * intensity +
        w['persistence'] * persistence +
        w['area'] * area_component(box) +
        w['part'] * part_component(part_overlap) +
        w['stage'] * stage_component(phase, kind)
    )
    return round(100 * value, 1)


def validate_weights(weights=None):
    if weights is None:
        return dict(DEFAULT_WEIGHTS)
    result = {k: float(weights.get(k, DEFAULT_WEIGHTS[k])) for k in DEFAULT_WEIGHTS}
    if any(not math.isfinite(v) or v < 0 for v in result.values()):
        raise ValueError('Score weights must be finite positive numbers.')
    total = sum(result.values())
    if total <= 0:
        raise ValueError('At least one score weight must be positive.')
    return {k: v / total for k, v in result.items()}


def with_priority(event, weights=None):
    row = dict(event)
    n = row.get('consecutive_count', row['end_layer'] - row['start_layer'] + 1)
    v, p = components(row['score'], n)
    import json
    box = row.get('box')
    if isinstance(box, str):
        box = json.loads(box)
    part = row.get('part_overlap')
    weights = validate_weights(weights)
    row.update(consecutive_count=n,
               legacy_priority_score=legacy_priority_value(row['score'], n),
               priority_score=priority_value(row['score'], n, box, part, row.get('phase'), row.get('kind'), weights),
               variation_component=round(100*v, 1), persistence_component=round(100*p, 1),
               area_component=round(100*area_component(box), 1),
               part_component=round(100*part_component(part), 1),
               stage_component=round(100*stage_component(row.get('phase'), row.get('kind')), 1))
    return row


def review_sort(value):
    if value not in {'layer', 'priority'}:
        raise ValueError('Unknown review order.')
    return value


def priority_text(event):
    row = with_priority(event)
    return (f"Priority {row['priority_score']:.1f} / 100 · intensity × {row['score']:.2f} "
            f"· persistence: {row['consecutive_count']} · area component {row['area_component']:.1f} "
            f"· part component {row['part_component']:.1f}")
