import datetime


def get_today(tz: datetime.tzinfo = datetime.timezone.utc) -> datetime.date:
    return datetime.datetime.now(tz=tz).date()


def get_yesterday(tz: datetime.tzinfo = datetime.timezone.utc) -> datetime.date:
    return (datetime.datetime.now(tz=tz).date() - datetime.timedelta(days=1))
    

def convert_to_date(date: str | datetime.datetime | datetime.date, format: str = '%Y-%m-%d') -> datetime.date:
    if isinstance(date, datetime.date):
        return date
    elif isinstance(date, datetime.datetime):
        return date.date()
    elif isinstance(date, str):
        return datetime.datetime.strptime(date, format).date()
    else:
        raise ValueError(f'Invalid date type: {type(date)}')

    
def get_utc_now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)

    
def convert_ts_to_dt(ts: float, tz: datetime.tzinfo = datetime.timezone.utc):
    return datetime.datetime.fromtimestamp(ts, tz=tz)


def get_local_timezone() -> datetime.tzinfo:
    return datetime.datetime.now().astimezone().tzinfo


def format_timezone_for_date(date: str, tz_identifier='US/Eastern'):
    '''Returns timezone abbreviation and UTC offset for a specific date and timezone.

    This function determines the timezone abbreviation (e.g., EST, EDT) and UTC offset
    for a given date, accounting for daylight saving time transitions. Useful when you
    need to determine if a timezone is in standard or daylight saving time on a specific date.

    Args:
        date: Date string in 'YYYY-MM-DD' format (e.g., '2023-11-11')
        tz_identifier: IANA timezone database identifier (default: 'US/Eastern')
                      Examples: 'US/Eastern', 'US/Pacific', 'Europe/London', 'Asia/Tokyo'

    Returns:
        str: Timezone abbreviation concatenated with UTC offset.
             Format: '{abbreviation}{offset}' where offset is in ±HHMM format.

    Examples:
        >>> format_timezone_for_date('2023-11-11', 'US/Eastern')
        'EST-0500'  # November is in Eastern Standard Time (UTC-5)

        >>> format_timezone_for_date('2023-07-11', 'US/Eastern')
        'EDT-0400'  # July is in Eastern Daylight Time (UTC-4)

        >>> format_timezone_for_date('2023-06-15', 'US/Pacific')
        'PDT-0700'  # Pacific Daylight Time

        >>> format_timezone_for_date('2023-12-25', 'Europe/London')
        'GMT+0000'  # Greenwich Mean Time

        >>> format_timezone_for_date('2023-08-01', 'Asia/Tokyo')
        'JST+0900'  # Japan Standard Time (no DST)
    '''
    import pytz
    date = datetime.datetime.strptime(date, '%Y-%m-%d')
    timezone = pytz.timezone(tz_identifier)
    local_date = timezone.localize(date)  # attach timezone to the datetime object 
    return local_date.strftime('%Z%z')