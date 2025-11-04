from datetime import datetime

def time_ago(dt):
    """
    Returns a human-readable time difference between now and the given datetime.
    """
    if not dt:
        return ""
        
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    intervals = {
        'year': 31536000,
        'month': 2592000,
        'week': 604800,
        'day': 86400,
        'hour': 3600,
        'minute': 60,
        'second': 1
    }
    
    for unit, seconds_in_unit in intervals.items():
        interval = int(seconds // seconds_in_unit)
        if interval >= 1:
            if unit == 'second' and interval < 10:
                return "just now"
            return f"{interval} {unit}{'s' if interval > 1 else ''} ago"
    
    return "just now"

def format_date(dt, format_str='%b %d, %Y'):
    """Format a datetime object as a string."""
    if not dt:
        return ""
    return dt.strftime(format_str)

def format_currency(amount):
    """Format a number as currency."""
    if amount is None:
        return ""
    return f"${amount:,.2f}"

def pluralize(count, singular, plural=None):
    """Return the singular or plural form based on the count."""
    if not plural:
        plural = singular + 's'
    return f"{count} {singular if count == 1 else plural}"
