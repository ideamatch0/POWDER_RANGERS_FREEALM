"""Illustrative pricing and cash/recognition model. Not market forecasts."""
import json,math
from pathlib import Path
ASSUMPTIONS={'currency':'EUR, excluding VAT','pilot_price':3000,'annual_list_price':6000,'conversion_credit':750,
 'production_onboarding':1500,'pilot_delivery_hours':24,'onboarding_hours':10,'support_hours_per_active_account':6,
 'delivery_hour_cost':65,'pilot_tools':100,'collection_rate':.02,
 'timing':'Annual subscriptions activate/renew at midyear; full cash collected upfront; services recognized in year of delivery.'}
def scenario(pilots,new,renewals,fixed,prior_new=0):
    a=ASSUMPTIONS;first=a['annual_list_price']-a['conversion_credit'];active=new+renewals
    cash=pilots*a['pilot_price']+new*(first+a['production_onboarding'])+renewals*a['annual_list_price']
    recognized=pilots*a['pilot_price']+new*a['production_onboarding']+.5*(prior_new*first+new*first+renewals*a['annual_list_price'])
    hours=pilots*a['pilot_delivery_hours']+new*a['onboarding_hours']+active*a['support_hours_per_active_account']
    variable=hours*a['delivery_hour_cost']+pilots*a['pilot_tools']+cash*a['collection_rate']
    return dict(pilots=pilots,new=new,renewals=renewals,end_customers=active,list_price_arr=active*a['annual_list_price'],
       cash_bookings=cash,recognized_revenue=recognized,delivery_hours=hours,variable_cost=variable,fixed_cost=fixed,
       operating_result=recognized-variable-fixed,cash_surplus=cash-variable-fixed)
def model():
    rows={}
    for name,y1,y2 in [('Downside',(6,2,0,90000),(12,4,1,120000)),('Base',(16,8,0,90000),(28,14,7,120000)),('Upside',(30,18,0,90000),(50,30,16,160000))]:
        rows[name]=[scenario(*y1),scenario(*y2,prior_new=y1[1])]
    saving=(4-.75)*65*80;first=3000+5250+1500;unit=(4-.75)*65
    return {'assumptions':ASSUMPTIONS,'scenarios':rows,'roi_example':{'jobs_per_year':80,'manual_hours_per_job':4,'assisted_hours_per_job':.75,
      'hourly_loaded_cost':65,'annual_time_value':saving,'first_year_total_price':first,'first_year_net_value':saving-first,
      'first_year_roi':(saving-first)/first,'renewal_net_value':saving-6000,'first_year_break_even_jobs':math.ceil(first/unit),
      'renewal_break_even_jobs':math.ceil(6000/unit)},'support_stress_base_y2':21*(30-6)*65}
if __name__=='__main__':
    data=model();p=Path(__file__).resolve().parents[1]/'output/financial_model.json';p.write_text(json.dumps(data,indent=2));print(json.dumps(data,indent=2))
