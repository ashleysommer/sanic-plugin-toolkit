# -*- coding: utf-8 -*-
"""
This is the specialised dictionary that is used by Sanic Plugins Framework
to manage Context objects. It can be hierarchical, and it searches its
parents if it cannot find an item in its own dictionary. It can create its
own children.
"""


class ContextDict(dict):
    __slots__ = ('_spf', '_parent_context', '__weakref__')

    def __repr__(self):
        _dict_repr = super(ContextDict, self).__repr__()
        return "ContextDict({:s})".format(_dict_repr)

    def __str__(self):
        _dict_str = super(ContextDict, self).__str__()
        return "ContextDict({:s})".format(_dict_str)

    def __getitem__(self, item):
        try:
            return super(ContextDict, self).__getitem__(item)
        except KeyError as e1:
            parents_searched = [self, ]
            parent = self._parent_context
            while parent:
                try:
                    return super(ContextDict, parent).__getitem__(item)
                except KeyError:
                    parents_searched.append(parent)
                    # noinspection PyProtectedMember
                    next_parent = parent._parent_context
                    if next_parent in parents_searched:
                        raise RuntimeError("Recursive ContextDict found!")
                    parent = next_parent
            raise e1

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError as e:
            raise AttributeError(*e.args)

    def __setattr__(self, key, value):
        try:
            return self.__setitem__(key, value)
        except Exception as e:
            # what exceptions can occur on setting an item?
            raise e

    def create_child_context(self, *args, **kwargs):
        return ContextDict(self._spf, self, *args, **kwargs)

    def __new__(cls, spf, parent, *args, **kwargs):
        self = super(ContextDict, cls).__new__(cls, *args, **kwargs)
        if parent is not None:
            assert isinstance(parent, ContextDict),\
                "Parent context must be a valid initialised ContextDict"
            self._parent_context = parent
        else:
            self._parent_context = None
        self._spf = spf
        return self

    def __init__(self, *args, **kwargs):
        args = list(args)
        args.pop(0)  # remove spf
        args.pop(0)  # remove parent
        super(ContextDict, self).__init__(*args, **kwargs)
