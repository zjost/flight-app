from datetime import datetime, timedelta
import pandas as pd

from src.scraping import SouthwestFlightData
from src.tripsearches import WeekendSearch

depart_weekdays = [5] # Monday = 1
trip_duration = 2 # in days
# Number of days away from today to search departure dates
start_days, end_days = 28, 120
weekend = WeekendSearch('DAL', 'STL', 1)
weekend.search_trips(depart_weekdays, start_days, end_days, trip_duration = 2)

weekend.set_all_trips()
print len(weekend.joined_trips)

weekend.filter_by_price(240)
print len(weekend.joined_trips)

weekend.filter_no_layovers()
print len(weekend.joined_trips)
