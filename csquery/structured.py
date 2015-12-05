# -*- coding: utf-8 -*-
"""
    csquery.structured
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :author: tell-k <ffk2005 at gmail.com>
    :author2: podhmo <>
    :copyright: tell-k All Rights Reserved.
"""

# -*- coding:utf-8 -*-
import inspect
from collections import namedtuple
from cached_property import cached_property
from functools import partial
from six import binary_type, text_type

Pair = namedtuple("Pair", "value included")


def text_(s, encoding="utf-8"):
    if isinstance(s, binary_type):
        s = s.decode(encoding)
    return s


meta = {
    ord(u'\\'): u'\\\\',
    ord(u"'"): u"\\'",
}


def escape(s, meta=meta):
    return text_(s).translate(meta)


class Emitter(object):
    def quote(self, s):
        # todo escape
        return u"'{}'".format(escape(s))

    def atom_value(self, value):
        if hasattr(value, "isdigit") and not value.isdigit():
            value = self.quote(value)
        return u"{}".format(value)

    def range_left(self, pair):
        if not pair:
            return u"{"
        prefix = u"[" if pair.included else u"{"
        return u"{}{}".format(prefix, self.atom_value(pair.value).replace(u"\\-", u"-"))

    def range_right(self, pair):
        if not pair:
            return u"}"
        suffix = u"]" if pair.included else u"}"
        return u"{}{}".format(self.atom_value(pair.value).replace(u"\\-", u"-"), suffix)

    def range_value(self, begin=None, end=None):
        return u",".join([self.range_left(begin), self.range_right(end)])

    def list_value(self, args):
        return u" ".join(v.as_query(self) for v in args)

    def option(self, option):
        if option.value is None:
            return u""
        return u"{}={}".format(option.name, option.wrap(self, option.value))

    def expression(self, op, options, emitted):
        if options:
            return u"({} {} {})".format(op, options, emitted)
        else:
            return u"({} {})".format(op, emitted)

    # abstract
    def pairvalue(self, pairvalue):
        return self.expression(
            pairvalue.op,
            self.list_value(pairvalue.options),
            self.range_value(pairvalue.left, pairvalue.right)
        )

    def container(self, container):
        alived_args = [v for v in container.args if not v.is_empty]
        return self.expression(
            container.op,
            self.list_value(container.options),
            self.list_value(alived_args)
        )

    def onevalue(self, onevalue):
        return self.expression(
            onevalue.op,
            self.list_value(onevalue.options),
            self.atom_value(onevalue.value)
        )


class Printable(object):
    def query(self):
        return self.as_query(self.emitter)

    def __call__(self):
        return self.query()

    def __str__(self):
        return self.query()

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.query())


class HasAssertion(object):
    def do_assertion(self):
        for assertion in self.assertion_list:
            assertion(self)

    @cached_property
    def assertion_list(self):
        return []


class Option(Printable, HasAssertion):
    def __init__(self, emitter, wrap, name, value=""):
        self.emitter = emitter
        self.wrap = wrap
        self.name = name
        self.value = value

    def as_query(self, emitter=None):
        if self.value == "":
            return ""
        self.do_assertion()
        emitter = emitter or self.emitter
        return emitter.option(self)

    def __copy__(self):
        return self.__class__(self.emitter, self.wrap, self.name, self.value)


class Container(Printable, HasAssertion):
    # and not or
    def __init__(self, emitter, op, options, *args):
        self.emitter = emitter
        self.op = op
        self.options = options
        self.args = args

    @property
    def is_empty(self):
        return not self.args or all(x.is_empty for x in self.args)

    def as_query(self, emitter=None):
        self.do_assertion()
        emitter = emitter or self.emitter
        return emitter.container(self)

    def __copy__(self):
        return self.__class__(self.emitter, self.op, self.options[:], *self.args)


class OneValue(Printable, HasAssertion):
    # term, near, phrase, prefix?
    def __init__(self, emitter, op, options, value):
        self.emitter = emitter
        self.op = op
        self.options = options
        self.value = value

    is_empty = False

    def as_query(self, emitter=None):
        self.do_assertion()
        emitter = emitter or self.emitter
        return emitter.onevalue(self)

    def __copy__(self):
        return self.__class__(self.emitter, self.op, self.options[:], self.value)


class PairValue(Printable, HasAssertion):
    def __init__(self, emitter, op, options, left=None, right=None):
        self.emitter = emitter
        self.op = op
        self.options = options
        self.left = left
        self.right = right

    is_empty = False

    def as_query(self, emitter=None):
        self.do_assertion()
        emitter = emitter or self.emitter
        return emitter.pairvalue(self)

    def __copy__(self):
        return self.__class__(self.emitter, self.op, self.options[:], self.left, self.right)


class ValueWrapper(object):
    def quote(self, emitter, value):
        return emitter.quote(value)

    def raw(self, emitter, value):
        return value


class ExpressionRepository(object):
    def __init__(self, emitter=None, option_wrapper=None):
        self.emitter = emitter or Emitter()
        self.option_wrapper = option_wrapper or ValueWrapper()

    def register(self, op, cls, option_list):
        factories = []
        for name, wrap in option_list:
            if not callable(wrap):
                wrap = getattr(self.option_wrapper, wrap)
            factories.append((name, partial(Option, self.emitter, wrap, name)))
        factory = ExpressionFactory(self.emitter, cls, op, factories)
        setattr(self, op, factory)
        return factory


def get_optionals(argspec):
    if argspec.defaults is None:
        return []
    else:
        return argspec.args[-len(argspec.defaults or []):]


class ExpressionFactory(object):
    def __init__(self, emitter, cls, op, option_factories):
        self.emitter = emitter
        self.cls = cls
        self.op = op  # Str
        self.option_factories = option_factories  # List(Tuple[Str, Callable])
        argspec = inspect.getargspec(cls.__init__ if isinstance(cls, type) else cls.__call__)
        self.optionals = get_optionals(argspec)  # List[Str]
        self.keywords = argspec.keywords  # **kwargs

    def __call__(self, *args, **kwargs):
        kwargs = kwargs.copy()
        options = [fn(kwargs.pop(name)) for name, fn in self.option_factories if name in kwargs]
        new_kwargs = {name: kwargs.pop(name) for name in self.optionals if name in kwargs}

        if self.keywords:
            new_kwargs.update(kwargs)
        return self.cls(self.emitter, self.op, options, *args, **new_kwargs)


class LiftedContainerFactory(object):
    def __init__(self, factory):
        self.factory = factory

    def __call__(self, emitter, op, options, *args, **fields):
        args = [(self.lift(x)) for x in args]
        if fields:
            args.extend([self.lift(v, k) for k, v in fields.items()])
        return self.factory(emitter, op, options, *args)

    def lift(self, value, field=None):
        if hasattr(value, "emitter"):
            if field is not None:
                value.options.append(option("field", field))
            return value
        elif isinstance(value, (list, tuple)):
            return range_(left=value[0], right=value[1], field=field)
        else:
            return term(value, field=field)


class LiftedPairValueFactory(object):
    def __init__(self, factory):
        self.factory = factory

    def lift(self, value):
        if value is None or value == "":
            return None
        elif not hasattr(value, "included"):
            value = Pair(value, included=True)
        return value

    def __call__(self, emitter, op, options, left=None, right=None):
        left = self.lift(left)
        right = self.lift(right)
        return self.factory(emitter, op, options, left=left, right=right)


class RangeAssertionPairValueFactory(object):
    def __init__(self, factory):
        self.factory = factory

    def __call__(self, emitter, op, options, left=None, right=None):
        pairvalue = self.factory(emitter, op, options, left=left, right=right)
        pairvalue.assertion_list.append(self.assertion)
        return pairvalue

    def assertion(self, pairvalue):
        # assertion ad-hocなので後でまともにする
        # assert any(op.name == "field" for op in pairvalue.options), "<Pair Value> field is required"
        assert (pairvalue.left or pairvalue.right), "<PairValue> both of left and right are empty"
        assert pairvalue.left is None or isinstance(pairvalue.left, Pair)
        if isinstance(pairvalue.left, Pair):
            assert isinstance(pairvalue.left.value, (text_type, binary_type, int))
        assert pairvalue.right is None or isinstance(pairvalue.right, Pair)
        if isinstance(pairvalue.right, Pair):
            assert isinstance(pairvalue.right.value, (text_type, binary_type, int))

vw = ValueWrapper()
emitter = Emitter()
repository = ExpressionRepository(emitter, vw)
option = partial(Option, emitter, vw.raw)

and_ = repository.register("and", LiftedContainerFactory(Container), [("boost", vw.raw)])
or_ = repository.register("or", LiftedContainerFactory(Container), [("boost", vw.raw)])
not_ = repository.register("not", LiftedContainerFactory(Container), [("field", vw.quote), ("boost", vw.raw)])

term = repository.register("term", OneValue, [("field", vw.quote), ("boost", vw.raw)])
near = repository.register("near", OneValue, [("field", vw.quote), ("distance", vw.raw), ("boost", vw.raw)])
phrase = repository.register("phrase", OneValue, [("field", vw.quote), ("boost", vw.raw)])
prefix = repository.register("prefix", OneValue, [("field", vw.quote), ("boost", vw.raw)])
range_ = repository.register("range", RangeAssertionPairValueFactory(LiftedPairValueFactory(PairValue)), [("field", vw.quote), ("boost", vw.raw)])
