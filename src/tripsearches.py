from datetime import datetime, timedelta
import pandas as pd
from scraping import SouthwestFlightData

class WeekendSearch(object):
    outTime = 'ANYTIME'
    returnTime = 'ANYTIME'
    seniorCount = '0'
    fareType = 'DOLLARS'
    
    def __init__(self, originAirport, destinationAirport, adultCount, roundTrip=True):
        self.form = {
            'twoWayTrip': roundTrip,
            'originAirport': originAirport,
            'destinationAirport': destinationAirport,
            'outboundTimeOfDay': self.outTime,
            'returnTimeOfDay': self.returnTime,
            'adultPassengerCount': adultCount,
            'seniorPassengerCount': self.seniorCount,
            'fareType': self.fareType,
            'submitButton': 'submit'}
        
        self.trips = None
        
    def find_dow_dates(self, dow_list, start_days, end_days, baseline):
        """
        Args:
            dow_list (list): List of integers representing the days
                of the week you're willing to depart.  1 = Monday,
                2 = Tuesday...etc.
            start_days (int): Number of days away from the baseline
                to start the search
            end_days (int): Number of days away from the baseline
                to stop the search
            baseline (datetime.date): Reference date for start_days
                and end_days

        Returns:
            dates (list): A list of datetime.date objects that
                satisfy the day-of-week criteria
        """
        date_list = []
        for i in range(start_days, end_days+1):
            date = baseline + timedelta(days=i)
            if date.isoweekday() in dow_list:
                date_list.append(date)

        return date_list
       
    def search_trips(self, dow_list, start_days, end_days, trip_duration, 
                     baseline=datetime.now().date()):
        
        trip_data_list = [] # list of DataFrames
        
        depart_dates = self.find_dow_dates(dow_list, start_days, end_days, baseline)
        return_dates = [day + timedelta(days=trip_duration) for day in depart_dates]
        trip_dates = zip(depart_dates, return_dates)
        
        fmt = '%m/%d/%Y'
        for i, (depart_dt, return_dt) in enumerate(trip_dates):
            outDate = depart_dt.strftime(fmt)
            returnDate = return_dt.strftime(fmt)
            self.form['outboundDateString'] = outDate
            self.form['returnDateString'] = returnDate
            
            # Scrape the data and append to DF list
            sw = SouthwestFlightData(self.form)
            dat = sw.df.copy()
            dat.loc[:, 'trip_ind'] = i+1
            trip_data_list.append(dat)
            
        self.trips = pd.concat(trip_data_list, axis=0)

    def set_all_trips(self):
        """
        Joins all departures to all arrivals for each unique trip
        to give an exhaustive list of trip options.  Calculates
        a "total_price" column
        """
        if self.trips is None:
            raise ValueError("self.trips doesn't exist!")

        joined_trips = self.trips[self.trips.depart_or_return=='depart'].merge(
            self.trips[self.trips.depart_or_return=='return'], how='outer', 
            on = 'trip_ind', suffixes = ['_dep', '_ret'])

        # Add a "total_price" column
        joined_trips['total_price'] = joined_trips.prices_dep + joined_trips.prices_ret
        
        self.joined_trips = joined_trips
   
    def filter_by_price(self, max_price):
        """
        Alters self.joined_trips to only include 
        trips with total price less than max_price
        """
        self.joined_trips = self.joined_trips[\
            self.joined_trips.total_price <= max_price].\
            sort_values(by='total_price')

    def filter_no_layovers(self):
        """
        Alters self.joined_trips to only include
        trips with no layovers
        """
        self.joined_trips = self.joined_trips[\
            (self.joined_trips.layover_ind_dep==0) &
            (self.joined_trips.layover_ind_ret==0)].\
            sort_values(by='total_price')
