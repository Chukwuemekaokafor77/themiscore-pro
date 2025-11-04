from datetime import datetime, timedelta
from sqlalchemy import or_

def get_pagination(page, per_page=10):
    """Helper function to get pagination parameters."""
    return {
        'page': max(1, int(page) if str(page).isdigit() else 1),
        'per_page': min(50, max(1, int(per_page) if str(per_page).isdigit() else 10))
    }

def apply_case_filters(query, args):
    """Apply filters to case query based on request arguments."""
    from models import Case  # Import here to avoid circular imports
    
    # Filter by client
    client_id = args.get('client_id')
    if client_id and client_id.isdigit():
        query = query.filter(Case.client_id == int(client_id))
    
    # Filter by status
    status = args.get('status')
    if status in ['open', 'in_progress', 'closed']:
        query = query.filter(Case.status == status)
    
    # Filter by priority
    priority = args.get('priority')
    if priority in ['high', 'medium', 'low']:
        query = query.filter(Case.priority == priority)
    
    # Search by title or description
    search = args.get('search')
    if search:
        search = f"%{search}%"
        query = query.filter(
            or_(
                Case.title.ilike(search),
                Case.description.ilike(search),
                Case.case_number.ilike(search)
            )
        )
    
    return query

def get_sort_params(args, default_sort='-created_at'):
    """Get sort parameters from request arguments."""
    from models import Case  # Import here to avoid circular imports
    
    sort = args.get('sort', default_sort)
    sort_field = sort.lstrip('-')
    sort_order = 'desc' if sort.startswith('-') else 'asc'
    
    # Map sort fields to model columns
    sort_mapping = {
        'title': Case.title,
        'status': Case.status,
        'priority': Case.priority,
        'created_at': Case.created_at,
        'updated_at': Case.updated_at,
        'case_number': Case.case_number,
        'client_name': 'Client.last_name'  # This will be handled specially
    }
    
    # Default sort column if the requested one doesn't exist
    sort_column = sort_mapping.get(sort_field, Case.created_at)
    
    # Special handling for client name sorting
    if sort_field == 'client_name':
        from models import Client
        sort_column = Client.last_name
    
    return sort_column, sort_order
