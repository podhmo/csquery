# -*- coding: utf-8 -*-
"""
    tests.test_structured
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    unittest for csquery.structured

    :author: tell-k <ffk2005 at gmail.com>
    :copyright: tell-k. All Rights Reserved.
"""
from __future__ import division, print_function, absolute_import, unicode_literals  # NOQA


class TestEscape(object):

    def _get_target(self):
        from csquery.structured import escape
        return escape

    def _call_fut(self, *args, **kwargs):
        return self._get_target()(*args, **kwargs)

    def test_it(self):
        assert r"test\'test" == self._call_fut("test'test")
        assert r"\'test\'test\'" == self._call_fut("'test'test'")
        assert r"test\\test" == self._call_fut(r"test\test")


class TestAnd_(object):

    def _get_target(self):
        from csquery.structured import and_
        return and_

    def _call_fut(self, *args, **kwargs):
        return self._get_target()(*args, **kwargs)

    def test_it(self):
        from csquery.structured import not_, or_, term, range_

        actual = self._call_fut(term("Harrison Ford", field="actors"),
                                term('star', field="title"),
                                range_(None, 2000, field="year"))
        expected = "(and (term field='actors' 'Harrison Ford') (term field='title' 'star') (range field='year' {,2000]))"
        assert expected == actual()

        actual = self._call_fut(term('star', field='title'), term('star2', field='title'))
        assert "(and (term field='title' 'star') (term field='title' 'star2'))" == actual()

        actual = self._call_fut(term('star', field='title'), term('star2', field='title'), boost=2)
        assert "(and boost=2 (term field='title' 'star') (term field='title' 'star2'))" == actual()

        # complex query
        actual = self._call_fut(
            not_(term('テスト', field='genres')),
            or_(
                term('star', field='title', boost=2),
                term('star', field='plot'),

            ),
            boost='plot'
        )
        expected = "(and boost=plot (not (term field='genres' 'テスト')) "
        expected += "(or (term field='title' boost=2 'star') "
        expected += "(term field='plot' 'star')))"
        assert expected == actual()


class TestOr_(object):

    def _get_target(self):
        from csquery.structured import or_
        return or_

    def _call_fut(self, *args, **kwargs):
        return self._get_target()(*args, **kwargs)

    def test_it(self):
        from csquery.structured import term, range_
        actual = self._call_fut(term("Harrison Ford", field="actors"),
                                term("star", field="title"),
                                range_(field="year", left=None, right=2000))
        expected = "(or (term field='actors' 'Harrison Ford') (term field='title' 'star') (range field='year' {,2000]))"
        assert expected == actual()

        actual = self._call_fut(star="title", star2="title")
        assert "(or (term field='star' 'title') (term field='star2' 'title'))" == actual()

        actual = self._call_fut(star="title", star2="title", boost=2)
        assert "(or boost=2 (term field='star' 'title') (term field='star2' 'title'))" == actual()


class TestNot_(object):

    def _get_target(self):
        from csquery.structured import not_
        return not_

    def _call_fut(self, *args, **kwargs):
        return self._get_target()(*args, **kwargs)

    def test_it(self):
        from csquery.structured import and_

        actual = self._call_fut(and_(actors='Harrison Ford', year=('', 2010)))
        assert "(not (and (term field='actors' 'Harrison Ford') (range field='year' {,2010])))" == actual()

        actual = self._call_fut(and_(actors='Harrison Ford',
                                     year=('', 2010)), boost=2)
        expected = "(not boost=2 (and (term field='actors' 'Harrison Ford') (range field='year' {,2010])))"
        assert expected == actual()


class TestNear(object):

    def _get_target(self):
        from csquery.structured import near
        return near

    def _call_fut(self, *args, **kwargs):
        return self._get_target()(*args, **kwargs)

    def test_it(self):
        actual = self._call_fut('teenage vampire')
        assert "(near 'teenage vampire')" == actual()

        actual = self._call_fut('teenage vampire', boost=2,
                                field='plot', distance=2)
        expected = "(near field='plot' distance=2 boost=2 'teenage vampire')"
        assert expected == actual()


class TestPhrase(object):

    def _get_target(self):
        from csquery.structured import phrase
        return phrase

    def _call_fut(self, *args, **kwargs):
        return self._get_target()(*args, **kwargs)

    def test_it(self):
        actual = self._call_fut('teenage girl')
        assert "(phrase 'teenage girl')" == actual()

        actual = self._call_fut('teenage girl', boost=2, field='plot')
        assert "(phrase field='plot' boost=2 'teenage girl')" == actual()


class TestPrefix(object):

    def _get_target(self):
        from csquery.structured import prefix
        return prefix

    def _call_fut(self, *args, **kwargs):
        return self._get_target()(*args, **kwargs)

    def test_it(self):
        actual = self._call_fut('star')
        assert "(prefix 'star')" == actual()

        actual = self._call_fut('star', boost=2, field='title')
        assert "(prefix field='title' boost=2 'star')" == actual()


class TestRange_(object):

    def _get_target(self):
        from csquery.structured import range_
        return range_

    def _call_fut(self, *args, **kwargs):
        return self._get_target()(*args, **kwargs)

    def test_it(self):
        actual = self._call_fut(1990, 2000)
        assert '(range [1990,2000])' == actual()

        actual = self._call_fut(None, 2000)
        assert '(range {,2000])' == actual()
        actual = self._call_fut('', 2000)
        assert '(range {,2000])' == actual()

        actual = self._call_fut(1990,)
        assert '(range [1990,})' == actual()
        actual = self._call_fut(1990, None)
        assert '(range [1990,})' == actual()
        actual = self._call_fut(1990, '')
        assert '(range [1990,})' == actual()

        actual = self._call_fut('1967-01-31T23:20:50.650Z',
                                '1967-01-31T23:59:59.999Z')
        expect = '(range [\'1967-01-31T23:20:50.650Z\',\'1967-01-31T23:59:59.999Z\'])'
        assert expect == actual()

        actual = self._call_fut(1990, 2000, field='date', boost=2)
        assert '(range field=\'date\' boost=2 [1990,2000])' == actual()


class TestTerm(object):

    def _get_target(self):
        from csquery.structured import term
        return term

    def _call_fut(self, *args, **kwargs):
        return self._get_target()(*args, **kwargs)

    def test_it(self):
        actual = self._call_fut('star')
        assert "(term 'star')" == actual()
        actual = self._call_fut(2000)
        assert '(term 2000)' == actual()
        actual = self._call_fut(2000, field='year', boost=2)
        expected = '(term field=\'year\' boost=2 2000)'
        assert expected == actual()
