# Licensed under LICENSE.md; also available at https://www.prefect.io/licenses/alpha-eula

import dask
import dask.bag
import multiprocessing
import signal

from prefect.engine.state import Failed


def multiprocessing_timeout(fn, timeout):
    def retrieve_value(*args, _container, **kwargs):
        """Puts the return value in a multiprocessing-safe container"""
        _container.put(fn(*args, **kwargs))

    def timeout_handler(*args, **kwargs):
        q = multiprocessing.Queue()
        kwargs["_container"] = q
        p = multiprocessing.Process(target=retrieve_value, args=args, kwargs=kwargs)
        p.start()
        p.join(timeout)
        p.terminate()
        if not q.empty():
            return q.get()
        else:
            return Failed(message=TimeoutError("Execution timed out."))

    return timeout_handler


def main_thread_timeout(fn, *args, timeout, **kwargs):
    pass


def dict_to_list(dd):
    """
    Given a dictionary of {Edge: States (or lists of States)} which need to be
    iterated over, effectively converts any states which return a list to a list of individual states and
    zips the values together to return a list of dictionaries, with each key now associated to a single element.
    """
    mapped = {e: state_to_list(s) for e, s in dd.items() if e.mapped}
    unmapped = {e: s for e, s in dd.items() if not e.mapped}
    m_list = [dict(zip(mapped, vals)) for vals in zip(*mapped.values())]
    for d in m_list:
        d.update(unmapped)
    return m_list


def state_to_list(s):
    """
    Converts a State `s` with an iterator as its result to a list of states of the same type.

    Example:
        ```python
        s = State(result=[1, 2, 3])
        state_to_list(s) # [State(result=1), State(result=2), State(result=3)]
    """
    if isinstance(s, list):
        return s
    return [type(s)(result=elem) for elem in s.result]


def unpack_dict_to_bag(*values, keys):
    "Convenience function for packaging up all keywords into a dictionary"
    return {k: v for k, v in zip(keys, values)}
