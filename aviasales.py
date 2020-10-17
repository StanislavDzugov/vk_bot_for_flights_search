from pprint import pprint
import json
import requests
import csv

try:
    import settings
except ImportError:
    exit('DO cp settings.py.default settings.py and set token')


class TicketSearch:
    def __init__(self, airlines, airports, origin, destination, depart_date, return_date=None):
        self.airlines = airlines
        self.airports = airports
        self.origin = origin
        self.destination = destination
        self.depart_date = depart_date
        self.return_date = return_date

    def get_iata_airports(self):
        iata_airports = {}
        with open(self.airports, newline='', encoding='utf-8') as csvfile:
            for line in csvfile:
                new_line = line.split(',')
                if new_line[9] != '':
                    iata_airports[new_line[2]] = new_line[9]
        return iata_airports

    def get_iata_airlines(self):
        iata_airlines = {}
        with open(self.airlines, newline='', encoding='utf-8') as csvfile:
            for line in csvfile:
                new_line = line.split(';')
                if new_line[1] != '':
                    iata_airlines[new_line[1][:2]] = new_line[0]
        return iata_airlines

    def convert_into_iata(self, airport_name):
        iata_airports = self.get_iata_airports()
        for key, value in iata_airports.items():
            if airport_name in key:
                return value

    def get_info(self):
        self.origin = self.convert_into_iata(self.origin)
        self.destination = self.convert_into_iata(self.destination)
        url = "https://api.travelpayouts.com/v1/prices/cheap"
        if self.return_date is not None:
            querystring = {"origin": f"{self.origin}", "destination": f"{self.destination}",
                           "depart_date": f"{self.depart_date}",
                           "return_date": f"{self.return_date}"}
        else:
            querystring = {"origin": f"{self.origin}", "destination": f"{self.destination}",
                           "depart_date": f"{self.depart_date}"}
        headers = {'x-access-token': settings.TOKEN_AVIASALES}
        response = requests.request("GET", url, headers=headers, params=querystring)
        return response

    def convert_info(self, info):
        if info['success'] is True:
            flight_info = dict()
            for key, value in info['data'][self.destination].items():
                flight_info[f'flight {key}'] = value
            for key, value in flight_info.items():
                flight_info[key].pop('return_at')
                flight_info[key].pop('expires_at')
            return flight_info

    def process_info_for_client(self):
        info = self.get_info()
        info_dict = json.loads(info.text)
        iata_airlines = self.get_iata_airlines()
        covnert_info = self.convert_info(info_dict)
        for key, value in covnert_info.items():
            for key1, value1 in value.items():
                if 'airline' in key1:
                    for iata_code, airlines in iata_airlines.items():
                        if iata_code in value1:
                            value[key1] = airlines
                            break
                        else:
                            value[key1] = value1
                if 'price' in key1:
                    value[key1] = f'{value1} RUB.'
                if 'departure_at' in key1:
                    value1 = value1.split('T')
                    value[key1] = f'{value1[0]}, time: {value1[1][:-1]}'
        return covnert_info

    def save_xml_file(self):
        convert_info = self.process_info_for_client()
        with open('flights.csv', 'w', newline='') as csvfile:
            header = ['Airline', 'Flight number', 'Departure info', 'Price']
            writer = csv.DictWriter(csvfile, fieldnames=header)
            writer.writeheader()
            for key, value in convert_info.items():
                writer.writerow({
                    header[0]: value['airline'],
                    header[1]: value['flight_number'],
                    header[2]: value['departure_at'],
                    header[3]: value['price'],
                })

    def run(self):
        self.save_xml_file()

