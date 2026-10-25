"""Bounded retries own a fresh Session and the whole transaction each time."""
import time
from sqlalchemy.exc import DBAPIError
from college_maintenance.sessions import SessionFactory

RETRYABLE = frozenset({'40001','40P01'})

def retry_transaction(operation,*,session_factory=SessionFactory,attempts=3,pause=None):
    if type(attempts) is not int or not 1<=attempts<=5:raise ValueError('attempts must be 1-5')
    for attempt in range(attempts):
        try:
            with session_factory() as session,session.begin():result=operation(session)
            return result
        except DBAPIError as error:
            if getattr(error.orig,'sqlstate',None) not in RETRYABLE or attempt+1==attempts:raise
        # Context exit has already rolled back and closed before waiting.
        (pause or time.sleep)(min(0.02*(2**attempt),0.2))
