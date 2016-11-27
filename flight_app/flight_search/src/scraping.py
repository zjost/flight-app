from datetime import datetime
from hashlib import sha1
import requests
from bs4 import BeautifulSoup
import pandas as pd

class SouthwestFlightData(object):
    def __init__(self, form_data):
        url = "https://www.southwest.com/flight/search-flight.html?preserveBugFareType=TRUE"
        response = requests.post(url, data=form_data)
        self.query_date = datetime.now()
        self.form = form_data
        self.soup = BeautifulSoup(response.content, "lxml")

    @property
    def depart_or_return_list(self):
        depart_or_return_list = []
        for i, tbody in enumerate(self.soup.find_all('table', class_ = 'searchResultsTable')):
            # Loop through table rows
            for row in tbody.find_all('tr'):
                # Try to extract product prices
                product_prices = row.find_all('label', class_='product_price')
                # If prices exist, we know it's a proper row
                if len(product_prices) > 0:
                    # If on the first table, mark as depart
                    if i==0:
                        depart_or_return_list.append('depart')
                    else:
                        depart_or_return_list.append('return')

        return depart_or_return_list

    @property
    def prices(self):
        """
        This function extracts the "Wanna Get Away" prices
        from the soup object of the webpage results.
        """
        price_list = []
        for i, tbody in enumerate(self.soup.find_all('table', class_ = 'searchResultsTable')):
            # Loop through table rows
            for row in tbody.find_all('tr'):
                # Get the three product prices
                product_prices = row.find_all('label', class_='product_price')
                # If all prices are not there, add an error indicator of -1
                if len(product_prices) > 0 and len(product_prices) < 3:
                    price_list.append(-1)
                # If it does exist, append it
                elif len(product_prices) > 0:
                    price_list.append(float(product_prices[2].text.strip().lstrip('$')))

        return price_list
    
    @property
    def flight_numbers(self):
        master_list = []
        # Scan each row
        for row in self.soup.find_all('tr'):
            # Create new list to hold all route's flight numbers
            flight_list = []
            # Check if row has the relevant entry
            if row.find('a', class_='bugLinkText'):
                # Find all flights
                for span in row.find_all('a', class_='bugLinkText'):
                        flight_list.append(int(span.text.strip().split()[0]))
                master_list.append(flight_list)

        return master_list
    
    @property
    def depart_and_arrive_lists(self):
        """
        Returns a tuple of two lists.  The lists are
        the departure and arrival times
        """
        # Create new lists to hold depart/arrival times
        depart_list = []
        arrive_list = []

        for row in self.soup.find_all('tr'):

            # Check if row has the relevant entry
            if row.find('td', class_='depart_column'):
                # Find all flights
                depart_text = row.find(
                    'td', class_='depart_column').find(
                    'span', class_='bugText').text.strip()

                depart_list.append(
                    datetime.strptime(depart_text, '%I:%M %p').time())

            # Check if row has the relevant entry
            if row.find('td', class_='arrive_column'):
                # Find arrival text
                arrive_text = row.find(
                    'td', class_='arrive_column').find(
                    'span', class_='bugText').text.strip()

                # Indicate if arrival is next day
                # XXX:TODO somehow record this data so can filter on it later
                """
                if arrive_text.find('Next Day') != -1:
                    print 'found'
                """

                # Format string for datetime parsing
                time = arrive_text.replace(
                    '\n', ' ').replace(
                    'Next Day', '').strip()
                
                arrive_list.append(
                    datetime.strptime(time, '%I:%M %p').time())

        return depart_list, arrive_list

    def flight_hash(self, x):
        """
        Constructs the SHA1 hash based on airline code, depart_city,
        destination city, and flight numbers.
        To be used as a lambda function in a pd.DataFrame.apply()
        call.

        Args:
            x (pd.DataFrame row):

        :return:
         string of hash
        """
        flight_str = "{airline}+{depart_city}+{dest_city}+{flight_num}".format(
            airline=x['airline'], depart_city=x['depart_city'],
            dest_city=x['destination_city'],
            flight_num='&'.join([str(flight) for flight in x['flight_numbers']])
        )

        return sha1(flight_str).hexdigest()
    
    @property
    def df(self):
        """
        Build a pandas DataFrame from the scraped data
        
        Note:  If there's an error, make sure each array has same
            length.  
        """
        # Extract the lists from the flight time tuple
        depart_times, arrive_times = self.depart_and_arrive_lists
        data = {'arrival': arrive_times, 'departure': depart_times,
                'flight_numbers': self.flight_numbers, 'price': self.prices,
                'depart_or_return': self.depart_or_return_list}
        
        df = pd.DataFrame(data)
        
        # Create a layover indicator based on count of flight numbers
        df['layover_ind'] = df.flight_numbers.apply(lambda x: 1 if len(x)>1 else 0)
        
        # Append a column for departure date
        depart_date = datetime.strptime(
                self.form['outboundDateString'], '%m/%d/%Y').date()
        return_date = datetime.strptime(
                self.form['returnDateString'], '%m/%d/%Y').date()
        df.loc[df.depart_or_return=='depart', 'depart_date'] = depart_date
        df.loc[df.depart_or_return=='return', 'depart_date'] = return_date
        # Add depart city
        df.loc[df.depart_or_return == 'depart', 'depart_city'] = \
            self.form['originAirport']
        df.loc[df.depart_or_return == 'return', 'depart_city'] = \
            self.form['destinationAirport']
        # Add destination city
        df.loc[df.depart_or_return == 'depart', 'destination_city'] = \
            self.form['destinationAirport']
        df.loc[df.depart_or_return == 'return', 'destination_city'] = \
            self.form['originAirport']

        # Add airline ICAO code
        df.loc[:,'airline'] = 'SWA'

        # Add query date
        df.loc[:, 'query_dt'] = self.query_date

        # Add flight hash
        df.loc[:, 'flight_hash'] = df.apply(lambda x: self.flight_hash(x),
                                            axis=1)

        # Filter out rows with missing price data
        df = df[df.price > 0]

        return df
