"""Adaptation des acquisitions sans hauteur connue au format commun de revue et de 3D."""
import hashlib
import json
from pathlib import Path

from imaging import context_box
from persistence import consecutive_runs, page_after
from priority import with_priority, review_sort


class AcquisitionViews:
    def acquisition_phases(self):
        return ['acquisition'] if self.acquisition_step==1 else ['sequence0','sequence1']

    def acquisition_phase(self,counter):
        return 'acquisition' if self.acquisition_step==1 else 'sequence'+str(counter%2)

    def acquisition_events(self):
        if not self.aalto_result:return [],{}
        signature=self.aalto_result['report']['signature'];cache_key=(signature,self.revision)
        cache=getattr(self,'_acquisition_events_cache',None)
        if cache and cache[0]==cache_key:return cache[1],cache[2]
        db=self.gallery_reviews()
        try:
            saved={(r['image'],r['prediction']):(r['status'],r['comment']) for r in db.execute(
                'SELECT image,prediction,status,comment FROM decisions WHERE signature=? AND job=?',(signature,self.library['job']))}
        finally:db.close()
        rows=[]
        for raw in sorted(self.aalto_result['images'].values(),key=lambda r:r['counter']):
            if raw['job']!=self.library['job']:continue
            for index,p in enumerate(raw['predictions']):
                key=hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()[:24]
                status,comment=saved.get((raw['id'],key),('a_examiner',''))
                rows.append({'id':f'{raw["id"]}:{index}','peak_frame':raw['id'],'prediction':index,'snapshot':key,
                             'geometry_key':json.dumps(raw.get('geometry'),sort_keys=True),
                             'start_layer':raw['counter'],'end_layer':raw['counter'],'phase':self.acquisition_phase(raw['counter']),
                             'camera':'aalto','box':json.dumps(p['box']),'kind':p['kind'],'score':p['score'],'status':status,'comment':comment})
        persistence=getattr(self,'_persistence_cache',None)
        if not persistence or persistence[0]!=signature:
            persistence=(signature,consecutive_runs(rows,self.acquisition_step));self._persistence_cache=persistence
        for row in rows:
            row.update(persistence[1][row['id']]);row.pop('geometry_key',None)
            row.update(with_priority(row,getattr(self,'score_weights',None)))
        lookup={r['id']:r for r in rows};self._acquisition_events_cache=(cache_key,rows,lookup)
        return rows,lookup

    def acquisition_listing(self,query):
        rows,lookup=self.acquisition_events();phase=query.get('phase',[''])[0];status=query.get('status',[''])[0]
        if phase and phase not in self.acquisition_phases():raise ValueError('Unknown sequence.')
        if status and status not in {'a_examiner','retenue','ecartee'}:raise ValueError('Unknown decision.')
        rows=[r for r in rows if (not phase or r['phase']==phase) and (not status or r['status']==status)]
        before=len(rows);rows=[r for r in rows if r['consecutive_count']>=self.min_consecutive]
        offset=max(0,int(query.get('offset',['0'])[0]))
        after=query.get('after',[None])[0];anchor=None
        if after is not None:
            anchor=lookup.get(after)
            if anchor is None:raise ValueError('Starting indication not found.')
        order=review_sort(query.get('sort',['layer'])[0])
        return {**page_after(rows,offset,anchor,order),'sort':order,'axis':'acquisition','before_persistence':before,'min_consecutive':self.min_consecutive}

    def acquisition_detail(self,event_id,context):
        _,lookup=self.acquisition_events();event=lookup.get(str(event_id))
        if event is None:raise ValueError('Indication not found in this job.')
        measured=self.aalto_result['images'][str(event['peak_frame'])];geometry=measured['geometry']
        by_counter={r['counter']:r for r in self.gallery};frames=[]
        for counter in [event['start_layer']-self.acquisition_step,event['start_layer'],event['start_layer']+self.acquisition_step]:
            r=by_counter.get(counter)
            if not r:frames.append(None);continue
            result=self.aalto_result['images'].get(str(r['id']),{});dims=result.get('geometry')
            comparable=bool(dims and all(dims[k]==geometry[k] for k in ('width','height')) and not result.get('error'))
            frames.append({'id':r['id'],'layer':counter,'phase':self.acquisition_phase(counter),'name':r['name'],
                           'geometry':dims,'comparable':comparable})
        return {'event':dict(event),'frames':frames,'peak_layer':event['start_layer'],'axis':'acquisition','step':self.acquisition_step,
                'z_mm':None,'pair':None,'crop':context_box(json.loads(event['box']),geometry['width'],geometry['height'],context),
                'context':context,'geometry':geometry}

    def acquisition_decision(self,data):
        event=self.acquisition_detail(data.get('id'),'standard')['event']
        if event['snapshot']!=data.get('snapshot'):raise ValueError('This indication has changed. Reload it before saving a decision.')
        return self.gallery_decide({'run':data.get('run'),'id':event['peak_frame'],'prediction':event['snapshot'],
                                    'status':data.get('status'),'comment':data.get('comment','')})

    def acquisition_image(self,frame_id,event_id=None,context='standard',stack_region=None):
        record=next((r for r in self.gallery if r['id']==frame_id),None)
        if record is None:raise ValueError('Image not found in this job.')
        path=(self.source/record['name']).resolve()
        if self.source.resolve() not in path.parents:raise ValueError('Image outside the library.')
        crop=None
        if event_id is not None:
            detail=self.acquisition_detail(event_id,context)
            if frame_id not in {f['id'] for f in detail['frames'] if f and f['comparable']}:
                raise ValueError('This image does not match the compared acquisitions.')
            crop=tuple(detail['crop'])
        if stack_region is not None:
            measurement=self.aalto_result['images'].get(str(frame_id),{}) if self.aalto_result else {}
            if not measurement.get('geometry') or measurement.get('error'):raise ValueError('Acquisition not measured.')
            crop=tuple(self.stack_crop(measurement['geometry'],stack_region,'aalto'))
        return self.render_preview(str(path),255,crop,384 if stack_region is not None else 1400)

    def acquisition_stack(self,phase,region,camera):
        if not self.aalto_result:raise ValueError('Run an analysis to prepare the stack.')
        phases=self.acquisition_phases()
        if phase not in phases:raise ValueError('Unknown 3D sequence.')
        if camera not in {None,'','aalto'}:raise ValueError('Unknown camera.')
        measured=[r for r in self.aalto_result['images'].values() if r['job']==self.library['job']
                  and self.acquisition_phase(r['counter'])==phase and r.get('geometry') and not r.get('error')]
        measured.sort(key=lambda r:r['counter'])
        if not measured:raise ValueError('No measured acquisitions.')
        geometry=measured[0]['geometry'];crop=self.stack_crop(geometry,region,'aalto');frames=[]
        for r in measured:
            if all(r['geometry'][k]==geometry[k] for k in ('width','height')):
                frames.append({'id':r['id'],'layer':r['counter'],'position':r['counter'],'z_mm':None})
        layers={r['layer'] for r in frames};events=[]
        for event in self.acquisition_events()[0]:
            if event['consecutive_count']<self.min_consecutive:continue
            if event['phase']!=phase or event['start_layer'] not in layers:continue
            box=json.loads(event['box']);clipped=[max(crop[0],box[0]),max(crop[1],box[1]),min(crop[2],box[2]),min(crop[3],box[3])]
            if clipped[0]>=clipped[2] or clipped[1]>=clipped[3]:continue
            events.append({k:event[k] for k in ('id','start_layer','end_layer','status','kind','score','consecutive_count','priority_score','legacy_priority_score','variation_component','persistence_component','area_component','part_component','stage_component')}|
                          {'box':clipped,'layer':event['start_layer'],'position':event['start_layer'],'z_mm':None})
        return {'phase':phase,'phases':phases,'camera':'aalto','cameras':['aalto'],'frames':frames,'events':events,
                'crop':crop,'width':crop[2]-crop[0],'height':crop[3]-crop[1],'excluded_dimensions':len(measured)-len(frames),
                'layer_um':None,'axis':'acquisition','texture_max_px':384,'min_consecutive':self.min_consecutive}
