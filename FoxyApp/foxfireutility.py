from datetime import datetime, timedelta

def friday():
    today = datetime.now()
    current_weekday = today.weekday()
    if current_weekday >= 4:
        days_until_friday = -(current_weekday - 4)
    else:
        days_until_friday = 4 - current_weekday
    this_friday = today + timedelta(days=days_until_friday)
    return this_friday.strftime('%d-%b-%Y')