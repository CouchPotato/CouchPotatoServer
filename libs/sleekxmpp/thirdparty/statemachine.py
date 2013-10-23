"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import threading
import time
import logging

log = logging.getLogger(__name__)


class StateMachine(object):

    def __init__(self, states=[]):
        self.lock = threading.Condition()
        self.__states = []
        self.addStates(states)
        self.__default_state = self.__states[0]
        self.__current_state = self.__default_state

    def addStates(self, states):
        self.lock.acquire()
        try:
            for state in states:
                if state in self.__states:
                    raise IndexError("The state '%s' is already in the StateMachine." % state)
                self.__states.append(state)
        finally:
            self.lock.release()


    def transition(self, from_state, to_state, wait=0.0, func=None, args=[], kwargs={}):
        '''
        Transition from the given `from_state` to the given `to_state`.
        This method will return `True` if the state machine is now in `to_state`.  It
        will return `False` if a timeout occurred the transition did not occur.
        If `wait` is 0 (the default,) this method returns immediately if the state machine
        is not in `from_state`.

        If you want the thread to block and transition once the state machine to enters
        `from_state`, set `wait` to a non-negative value.  Note there is no 'block
        indefinitely' flag since this leads to deadlock.  If you want to wait indefinitely,
        choose a reasonable value for `wait` (e.g. 20 seconds) and do so in a while loop like so:

        ::

            while not thread_should_exit and not state_machine.transition('disconnected', 'connecting', wait=20 ):
                    pass # timeout will occur every 20s unless transition occurs
            if thread_should_exit: return
            # perform actions here after successful transition

        This allows the thread to be responsive by setting `thread_should_exit=True`.

        The optional `func` argument allows the user to pass a callable operation which occurs
        within the context of the state transition (e.g. while the state machine is locked.)
        If `func` returns a True value, the transition will occur.  If `func` returns a non-
        True value or if an exception is thrown, the transition will not occur.  Any thrown
        exception is not caught by the state machine and is the caller's responsibility to handle.
        If `func` completes normally, this method will return the value returned by `func.`  If
        values for `args` and `kwargs` are provided, they are expanded and passed like so:
        `func( *args, **kwargs )`.
        '''

        return self.transition_any((from_state,), to_state, wait=wait,
                                    func=func, args=args, kwargs=kwargs)


    def transition_any(self, from_states, to_state, wait=0.0, func=None, args=[], kwargs={}):
        '''
        Transition from any of the given `from_states` to the given `to_state`.
        '''

        if not isinstance(from_states, (tuple, list, set)):
            raise ValueError("from_states should be a list, tuple, or set")

        for state in from_states:
            if not state in self.__states:
                raise ValueError("StateMachine does not contain from_state %s." % state)
        if not to_state in self.__states:
            raise ValueError("StateMachine does not contain to_state %s." % to_state)

        if self.__current_state == to_state:
            return True

        start = time.time()
        while not self.lock.acquire(False):
            time.sleep(.001)
            if (start + wait - time.time()) <= 0.0:
                log.debug("==== Could not acquire lock in %s sec: %s -> %s ", wait, self.__current_state, to_state)
                return False

        while not self.__current_state in from_states:
            # detect timeout:
            remainder = start + wait - time.time()
            if remainder > 0:
                self.lock.wait(remainder)
            else:
                log.debug("State was not ready")
                self.lock.release()
                return False

        try: # lock is acquired; all other threads will return false or wait until notify/timeout
            if self.__current_state in from_states: # should always be True due to lock

                # Note that func might throw an exception, but that's OK, it aborts the transition
                return_val = func(*args,**kwargs) if func is not None else True

                # some 'false' value returned from func,
                # indicating that transition should not occur:
                if not return_val:
                    return return_val

                log.debug(' ==== TRANSITION %s -> %s', self.__current_state, to_state)
                self._set_state(to_state)
                return return_val  # some 'true' value returned by func or True if func was None
            else:
                log.error("StateMachine bug!!  The lock should ensure this doesn't happen!")
                return False
        finally:
            self.lock.notify_all()
            self.lock.release()


    def transition_ctx(self, from_state, to_state, wait=0.0):
        '''
        Use the state machine as a context manager.  The transition occurs on /exit/ from
        the `with` context, so long as no exception is thrown.  For example:

        ::

            with state_machine.transition_ctx('one','two', wait=5) as locked:
                if locked:
                    # the state machine is currently locked in state 'one', and will
                    # transition to 'two' when the 'with' statement ends, so long as
                    # no exception is thrown.
                    print 'Currently locked in state one: %s' % state_machine['one']

                else:
                    # The 'wait' timed out, and no lock has been acquired
                    print 'Timed out before entering state "one"'

            print 'Since no exception was thrown, we are now in state "two": %s' % state_machine['two']


        The other main difference between this method and `transition()` is that the
        state machine is locked for the duration of the `with` statement.  Normally,
        after a `transition()` occurs, the state machine is immediately unlocked and
        available to another thread to call `transition()` again.
        '''

        if not from_state in self.__states:
            raise ValueError("StateMachine does not contain from_state %s." % from_state)
        if not to_state in self.__states:
            raise ValueError("StateMachine does not contain to_state %s." % to_state)

        return _StateCtx(self, from_state, to_state, wait)


    def ensure(self, state, wait=0.0, block_on_transition=False):
        '''
        Ensure the state machine is currently in `state`, or wait until it enters `state`.
        '''
        return self.ensure_any((state,), wait=wait, block_on_transition=block_on_transition)


    def ensure_any(self, states, wait=0.0, block_on_transition=False):
        '''
        Ensure we are currently in one of the given `states` or wait until
        we enter one of those states.

        Note that due to the nature of the function, you cannot guarantee that
        the entirety of some operation completes while you remain in a given
        state.  That would require acquiring and holding a lock, which
        would mean no other threads could do the same.  (You'd essentially
        be serializing all of the threads that are 'ensuring' their tasks
        occurred in some state.
        '''
        if not (isinstance(states,tuple) or isinstance(states,list)):
            raise ValueError('states arg should be a tuple or list')

        for state in states:
            if not state in self.__states:
                raise ValueError("StateMachine does not contain state '%s'" % state)

        # if we're in the middle of a transition, determine whether we should
        # 'fall back' to the 'current' state, or wait for the new state, in order to
        # avoid an operation occurring in the wrong state.
        # TODO another option would be an ensure_ctx that uses a semaphore to allow
        # threads to indicate they want to remain in a particular state.
        self.lock.acquire()
        start = time.time()
        while not self.__current_state in states:
            # detect timeout:
            remainder = start + wait - time.time()
            if remainder > 0:
                self.lock.wait(remainder)
            else:
                self.lock.release()
                return False
        self.lock.release()
        return True

    def reset(self):
        # TODO need to lock before calling this?
        self.transition(self.__current_state, self.__default_state)

    def _set_state(self, state): #unsynchronized, only call internally after lock is acquired
        self.__current_state = state
        return state

    def current_state(self):
        '''
        Return the current state name.
        '''
        return self.__current_state

    def __getitem__(self, state):
        '''
        Non-blocking, non-synchronized test to determine if we are in the given state.
        Use `StateMachine.ensure(state)` to wait until the machine enters a certain state.
        '''
        return self.__current_state == state

    def __str__(self):
        return "".join(("StateMachine(", ','.join(self.__states), "): ", self.__current_state))



class _StateCtx:

    def __init__(self, state_machine, from_state, to_state, wait):
        self.state_machine = state_machine
        self.from_state = from_state
        self.to_state = to_state
        self.wait = wait
        self._locked = False

    def __enter__(self):
        start = time.time()
        while not self.state_machine[self.from_state] or not self.state_machine.lock.acquire(False):
            # detect timeout:
            remainder = start + self.wait - time.time()
            if remainder > 0:
                self.state_machine.lock.wait(remainder)
            else:
                log.debug('StateMachine timeout while waiting for state: %s', self.from_state)
                return False

        self._locked = True # lock has been acquired at this point
        self.state_machine.lock.clear()
        log.debug('StateMachine entered context in state: %s',
                self.state_machine.current_state())
        return True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            log.exception("StateMachine exception in context, remaining in state: %s\n%s:%s",
                self.state_machine.current_state(), exc_type.__name__, exc_val)

        if self._locked:
            if exc_val is None:
                log.debug(' ==== TRANSITION %s -> %s',
                        self.state_machine.current_state(), self.to_state)
                self.state_machine._set_state(self.to_state)

            self.state_machine.lock.notify_all()
            self.state_machine.lock.release()

        return False # re-raise any exception

if __name__ == '__main__':

    def callback(s, s2):
        print((1, s.transition('on', 'off', wait=0.0, func=callback, args=[s,s2])))
        print((2, s2.transition('off', 'on', func=callback, args=[s,s2])))
        return True

    s = StateMachine(('off', 'on'))
    s2 = StateMachine(('off', 'on'))
    print((3, s.transition('off', 'on', wait=0.0, func=callback, args=[s,s2]),))
    print((s.current_state(), s2.current_state()))
