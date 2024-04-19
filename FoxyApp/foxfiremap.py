import requests


def get_milage(dest, api_key):
    source = "2107 South Fork Ridge Rd Liberty KY 42539"
    dest = dest
    url = 'https://maps.googleapis.com/maps/api/distancematrix/json?'
    r = requests.get(url + 'origins=' + source +
                        '&destinations=' + dest +
                        '&units=imperial' +
                        '&key=' + api_key)
    x = r.json()
    x = x['rows'][0]['elements'][0]['distance']['text']
    x = x.split(' ')
    return x[0]