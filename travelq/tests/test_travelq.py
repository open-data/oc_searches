from common.util import search_path
from playwright.sync_api import Page, expect
import re

def test_page_title_en(page: Page):
    page.goto(search_path('travel', 'en'))
    expect(page).to_have_title("Government Travel Expenses")


def test_page_title_fr(page: Page):
    page.goto(search_path('voyage', 'fr'))
    expect(page).to_have_title("Dépenses de voyage gouvernementaux")


def test_not_empty_en(page: Page):
    page.goto(search_path('travel', 'en'))
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_not_empty_fr(page: Page):
    page.goto(search_path('voyage', 'fr'))
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_click_facet_en(page: Page):
    page.goto(search_path('travel', 'en'))
    cb = page.get_by_label("facet-owner_org-tbs-sct")
    # Because of the way Search handles facets, need to use a clock event
    cb.dispatch_event('click')
    count = page.get_by_test_id("itemsfound")
    expect(count).to_contain_text(re.compile(r"[1-9][0-9]*"))

def test_click_facet_fr(page: Page):
    page.goto(search_path('voyage', 'fr'))
    cb = page.get_by_label("facet-owner_org-tbs-sct")
    # Because of the way Search handles facets, need to use a clock event
    cb.dispatch_event('click')
    count = page.get_by_test_id("itemsfound")
    expect(count).to_contain_text(re.compile(r"[1-9][0-9]*"))


def test_simple_search_en(page: Page):
    page.goto(search_path('travel', 'en'))
    tb = page.get_by_label("Search text")
    tb.fill('T-2022-P11-0008 wagner')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    # Should find exactly one record
    expect(count).to_have_text("one")


def test_simple_search_fr(page: Page):
    page.goto(search_path('voyage', 'fr'))
    tb = page.get_by_label("Recherche")
    tb.fill('T-2022-P11-0008 wagner')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    # Should find exactly one record
    expect(count).to_have_text("un")


def test_simple_record_en(page: Page):
    page.goto(search_path('travel', 'en', '/record/tbs-sct,T-2022-P11-0008'))
    expect(page).to_have_title("Government Travel Expenses")


def test_simple_record_fr(page: Page):
    page.goto(search_path('voyage', 'fr', '/record/tbs-sct,T-2022-P11-0008'))
    expect(page).to_have_title("Dépenses de voyage gouvernementaux")
