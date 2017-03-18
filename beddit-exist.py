from datetime import datetime, timedelta
from beddit.client import BedditClient
from beddit.sleep import SleepStage
import requests, json

# Change these to your own values
exist_access_token = ''
beddit_username = ''
beddit_password = ''
days_to_migrate = 7

# read in data from Beddit API
client=BedditClient(beddit_username, beddit_password)
end_date = datetime.today()
start_date = end_date-timedelta(days=days_to_migrate)
sleeps = client.get_sleeps(start=start_date, end=end_date)

# extract Exist-compatible variables and convert to a JSON structure 
json_data=[]
for sleep in sleeps:
    data_date=sleep.date.strftime('%Y-%m-%d')

    time_asleep_mins = int((sleep.property.stage_duration_S+sleep.property.stage_duration_R)/60)

    bedtime = sleep.session_range_start
    if (bedtime.hour > 12):
        noon=bedtime.replace(hour=12, minute=0, second=0)
    else:
        yesterday=bedtime-timedelta(days=1)
        noon=bedtime.replace(year=yesterday.year, month=yesterday.month, day=yesterday.day, hour=12, minute=0, second=0)   
    bedtime_since_noon_mins=int((bedtime-noon).seconds/60)

    waketime = sleep.session_range_end
    midnight=waketime.replace(day=waketime.day, hour=0, minute=0, second=0)    
    waketime_since_midnight_mins=int((waketime-midnight).seconds/60)

    time_in_bed_mins = int((waketime-bedtime).seconds/60)

    # count awakenings during night
    awake=0
    previous_state=0
    for event in sorted(sleep.sleep_event):
        state=sleep.sleep_event[event]
        # two concecutive awake events are combined to one
        if (state == SleepStage.Awake and previous_state != SleepStage.Awake):
            awake += 1
        previous_state=state

    json_data.append(dict([
                           ('name','sleep'), ('date',data_date), ('value',time_asleep_mins)
                           ]))  
    json_data.append(dict([
                           ('name','time_in_bed'), ('date',data_date), ('value',time_in_bed_mins)
                           ]))
    json_data.append(dict([
                           ('name','sleep_start'), ('date',data_date), ('value',bedtime_since_noon_mins)
                           ]))
    json_data.append(dict([
                          ('name','sleep_end'), ('date',data_date), ('value',waketime_since_midnight_mins)
                           ]))
    json_data.append(dict([
                           ('name','sleep_awakenings'), ('date',data_date), ('value',awake)
                           ]))    

# start uploading to Exist API    
print("Uploading to Exist.io")

url = 'https://exist.io/api/1/attributes/update/'

response = requests.post(url, headers={
                                       'Authorization':'Bearer '+exist_access_token, 
                                       'Accept':'application/json',
                                       'Content-type':'application/json'},
    data=json.dumps(json_data))

result=json.loads(response.text)
failed=len(result["failed"])
success=len(result["success"])

print("Failed:", failed, "Success:", success)
