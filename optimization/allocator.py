"""CityWatch inspection allocation. Uses only the Python standard library.

Run demo: python optimization/allocator.py --demo --teams 3 --capacity 4
Real data: python optimization/allocator.py --input predictive_models/output/daily_scores.csv \
    --date 2025-09-10 --teams 3 --capacity 4 --output assignments.csv

Scores select locations. A deterministic geographic heuristic assigns teams.
Equal inspection durations are assumed. Distances exclude depots, returns,
road networks and traffic. Sample predictions are invented demonstration data.
"""
import argparse
import csv
import json
import math
from pathlib import Path


def distance_km(first, second):
    """Great-circle distance between two location records."""
    lat1, lat2 = map(math.radians, (first['latitude'], second['latitude']))
    delta_lat = lat2 - lat1
    delta_lon = math.radians(second['longitude'] - first['longitude'])
    value = (math.sin(delta_lat / 2) ** 2
             + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2)
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1, max(0, value))))


def order_visits(group):
    """Use the highest-priority location first, then nearest unvisited location."""
    remaining = sorted(group, key=lambda row: (-row['priority_score'], row['cell_id']))
    route = []
    while remaining:
        if route:
            next_index = min(range(len(remaining)), key=lambda index: (
                distance_km(route[-1], remaining[index]), remaining[index]['cell_id']))
        else:
            next_index = 0
        route.append(remaining.pop(next_index))
    return route


def route_distance(group):
    route = order_visits(group)
    return sum(distance_km(first, second) for first, second in zip(route, route[1:]))


def optimize_inspections(areas, team_count, inspections_per_team,
                         date=None, score_column='with_weather'):
    """Accept records (for a DataFrame, pass df.to_dict('records')).

    Return assignments and summary as JSON-compatible dictionaries.
    Select highest scores exactly under equal inspection cost; team assignment
    is a geographic heuristic, with the simple assignment retained if better.
    Zero-score cells remain eligible; no minimum priority threshold is assumed.
    Multi-date input requires an explicit date. Invalid records raise ValueError.
    """
    for name, value in [('team_count', team_count),
                        ('inspections_per_team', inspections_per_team)]:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(name + ' must be a positive integer')
    records = [dict(row) for row in areas]
    dates = {str(row['date'])[:10] for row in records if row.get('date')}
    if date is None and len(dates) > 1:
        raise ValueError('Multiple dates found. Select one date explicitly.')
    if date is not None:
        date = str(date)[:10]
        records = [row for row in records if str(row.get('date', ''))[:10] == date]
        if not records:
            raise ValueError('No predictions for date ' + date)
    candidates = []
    seen = set()
    for row in records:
        try:
            cell_id = str(row['cell_id']).strip()
            latitude = float(row['latitude'])
            longitude = float(row['longitude'])
            score = float(row[score_column])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Each row needs cell_id, latitude, longitude and '
                             + score_column) from error
        if not cell_id or cell_id in seen:
            raise ValueError('Empty or duplicate cell_id: ' + cell_id)
        if not all(math.isfinite(value) for value in (latitude, longitude, score)):
            raise ValueError('Nonfinite value for ' + cell_id)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or score < 0:
            raise ValueError('Invalid coordinates or negative score for ' + cell_id)
        seen.add(cell_id)
        candidates.append(dict(cell_id=cell_id, latitude=latitude,
                               longitude=longitude, priority_score=score))
    candidates.sort(key=lambda row: (-row['priority_score'], row['cell_id']))
    capacity = team_count * inspections_per_team
    selected = candidates[:capacity]
    # The baseline distributes priority-ranked locations in round-robin order.
    baseline = [selected[index::team_count] for index in range(team_count)]
    groups = [[] for _ in range(team_count)]
    if selected:
        remaining = list(selected)
        for group in groups[:min(team_count, len(selected))]:
            if any(groups):
                seeds = [existing[0] for existing in groups if existing]
                index = max(range(len(remaining)), key=lambda index:
                            min(distance_km(remaining[index], seed) for seed in seeds))
            else:
                index = 0
            group.append(remaining.pop(index))
        # Add high-priority locations to the nearest team's current locations.
        for location in remaining:
            eligible = [index for index, group in enumerate(groups)
                        if len(group) < inspections_per_team]
            index = min(eligible, key=lambda index: (
                min(distance_km(location, other) for other in groups[index]), index))
            groups[index].append(location)
    baseline_distance = sum(route_distance(group) for group in baseline)
    grouped_distance = sum(route_distance(group) for group in groups)
    method = 'geographic_heuristic'
    if grouped_distance > baseline_distance:
        groups = baseline
        grouped_distance = baseline_distance
        method = 'baseline_fallback'
    assignments = []
    for team_index, group in enumerate(groups, start=1):
        for visit, location in enumerate(order_visits(group), start=1):
            assignments.append(dict(location, team_id=team_index, visit_order=visit))
    return {
        'assignments': assignments,
        'summary': {
            'date': date or (next(iter(dates)) if dates else None),
            'score_column': score_column,
            'assignment_method': method,
            'candidate_count': len(candidates),
            'selected_count': len(selected),
            'unused_capacity': capacity - len(selected),
            'teams_used': sum(bool(group) for group in groups),
            'selected_priority_total': sum(row['priority_score'] for row in selected),
            'baseline_distance_km': baseline_distance,
            'assigned_distance_km': grouped_distance,
            'distance_reduction_km': baseline_distance - grouped_distance,
            'distance_definition': 'Straight-line legs between inspections; no depot or return',
        },
    }


def demo_predictions():
    """Invented scores and coordinates for software demonstration only."""
    centers = [(40.75, -73.99), (40.68, -73.95), (40.83, -73.91)]
    return [dict(cell_id=f'demo-{index}', date='2025-09-10',
                 latitude=centers[index % 3][0] + (index // 3) * 0.003,
                 longitude=centers[index % 3][1] + (index // 3) * 0.002,
                 with_weather=round(0.30 - index * 0.01, 3))
            for index in range(18)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input', type=Path)
    source.add_argument('--demo', action='store_true')
    parser.add_argument('--date')
    parser.add_argument('--teams', type=int, default=3)
    parser.add_argument('--capacity', type=int, default=4)
    parser.add_argument('--score-column', default='with_weather')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.demo:
            rows = demo_predictions()
            print('DEMO ONLY: invented predictions, not actual collision estimates.')
        else:
            with args.input.open(newline='', encoding='utf-8-sig') as stream:
                rows = list(csv.DictReader(stream))
        result = optimize_inspections(rows, args.teams, args.capacity,
                                      args.date, args.score_column)
        result['summary']['demo'] = args.demo
        if args.output:
            fields = ['team_id', 'visit_order', 'cell_id', 'latitude',
                      'longitude', 'priority_score']
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(result['assignments'])
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
