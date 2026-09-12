"""Persistance des indications détectées, indépendante du gris et des décisions."""
from collections import defaultdict
from itertools import groupby
import json


def minimum_count(value):
    if type(value) is not int or not 1 <= value <= 10000:
        raise ValueError('Persistence must be an integer between 1 and 10,000.')
    return value


def event_order(row):
    return row['start_layer'], row['peak_frame'], row['prediction']


def consecutive_runs(rows, step=1):
    """Plus longue chaîne passant par chaque occurrence ; aucun saut autorisé.

    Une arête relie des rectangles qui se recouvrent sur deux acquisitions
    comparables successives. Les deux parcours évitent de prêter à toutes
    les branches d'un groupe la durée totale de ce groupe.
    """
    series=defaultdict(list)
    for row in rows:
        series[(row['camera'],row['phase'],row['kind'],row.get('geometry_key'))].append(
            (row['id'],row['start_layer'],json.loads(row['box'])))
    before={};after={}
    for values in series.values():
        values.sort(key=lambda row:row[1])
        for direction,ordered,result in [(1,values,before),(-1,reversed(values),after)]:
            previous=[];previous_position=None
            for position,batch in groupby(ordered,key=lambda row:row[1]):
                batch=list(batch)
                if previous_position is None or position-previous_position!=direction*step:previous=[]
                for identifier,_,box in batch:
                    best=(1,position)
                    for other,_,b in previous:
                        if max(box[0],b[0])<min(box[2],b[2]) and max(box[1],b[1])<min(box[3],b[3]):
                            count,endpoint=result[other]
                            if count+1>best[0]:best=(count+1,endpoint)
                    result[identifier]=best
                previous=batch;previous_position=position
    return {r['id']:{'consecutive_count':before[r['id']][0]+after[r['id']][0]-1,
                     'persistence_start':before[r['id']][1],'persistence_end':after[r['id']][1]} for r in rows}


def page_after(rows, offset=0, anchor=None, sort='layer'):
    from priority import review_sort
    review_sort(sort)
    key = (lambda row: (-row['priority_score'], *event_order(row))) if sort=='priority' else event_order
    rows = sorted(rows, key=key)
    next_id=None
    if anchor is not None:
        index=next((i for i,r in enumerate(rows) if key(r)>key(anchor)),len(rows))
        next_id=rows[index]['id'] if index<len(rows) else None
        offset=(index//25)*25
    offset=min(max(0,offset),((len(rows)-1)//25)*25 if rows else 0)
    result={'items':rows[offset:offset+25],'total':len(rows),'offset':offset}
    if anchor is not None:result['next_id']=next_id
    return result
