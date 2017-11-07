# -*- coding: utf-8 -*-
"""
This is the specialised dictionary that is used by Sanic Plugins Framework
to manage Context objects. It can be hierarchical, and it searches its
parents if it cannot find an item in its own dictionary. It can create its
own children.
"""


class ContextDict(object):
    __slots__ = ('_spf', '_parent_context', '_dict', '__weakref__')

    def _inner(self):
        return object.__getattribute__(self, '_dict')

    def __repr__(self):
        _dict_repr = repr(self._inner())
        return "ContextDict({:s})".format(_dict_repr)

    def __str__(self):
        _dict_str = repr(self._inner())
        return "ContextDict({:s})".format(_dict_str)

    def __len__(self):
        return len(self._inner())

    def __setitem__(self, key, value):
        return self._inner().__setitem__(key, value)

    def __getitem__(self, item):
        try:
            return self._inner().__getitem__(item)
        except KeyError as e1:
            parents_searched = [self, ]
            parent = self._parent_context
            while parent:
                try:
                    return parent._inner().__getitem__(item)
                except KeyError:
                    parents_searched.append(parent)
                    # noinspection PyProtectedMember
                    next_parent = parent._parent_context
                    if next_parent in parents_searched:
                        raise RuntimeError("Recursive ContextDict found!")
                    parent = next_parent
            raise e1

    def __delitem__(self, key):
        self._inner().__delitem__(key)

    def __delslice__(self, i, j):
        self._inner().__delslice__(i, j)

    def __getattr__(self, item):
        if item in self.__slots__:
            return object.__getattribute__(self, item)
        try:
            return self.__getitem__(item)
        except KeyError as e:
            raise AttributeError(*e.args)

    def __setattr__(self, key, value):
        if key in self.__slots__:
            return object.__setattr__(self, key, value)
        try:
            return self.__setitem__(key, value)
        except Exception as e:
            # what exceptions can occur on setting an item?
            raise e

    def __contains__(self, item):
        return self._inner().__contains__(item)

    def get(self, key, default=None):
        try:
            return self.__getattr__(key)
        except (AttributeError, KeyError):
            return default

    def set(self, key, value):
        try:
            return self.__setattr__(key, value)
        except Exception as e:
            raise e

    def items(self):
        return self._inner().items()

    def keys(self):
        return self._inner().keys()

    def values(self):
        return self._inner().values()

    def create_child_context(self, *args, **kwargs):
        return ContextDict(self._spf, self, *args, **kwargs)

    def __new__(cls, spf, parent, *args, **kwargs):
        self = super(ContextDict, cls).__new__(cls)
        self._dict = dict(*args, **kwargs)
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
        super(ContextDict, self).__init__()
