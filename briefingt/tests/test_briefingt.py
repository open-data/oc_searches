from common.util import search_path
from playwright.sync_api import Page, expect
import re

def test_page_title_en(page: Page):
    page.goto(search_path('briefing_titles', 'en'))
    expect(page).to_have_title("Briefing Note Titles and Numbers")


def test_page_title_fr(page: Page):
    page.goto(search_path('notesdinfo', 'fr'))
    expect(page).to_have_title("Titres et numéros des notes d’information")


def test_not_empty_en(page: Page):
    page.goto(search_path('briefing_titles', 'en'))
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_not_empty_fr(page: Page):
    page.goto(search_path('notesdinfo', 'fr'))
    count = page.get_by_test_id("itemsfound")
    # Just should not contain '0''
    expect(count).to_contain_text(re.compile(r"[1-9a-zA-Z]+"))


def test_click_facet_en(page: Page):
    page.goto(search_path('briefing_titles', 'en'))
    cb = page.get_by_label("facet-owner_org-tbs-sct")
    # Because of the way Search handles facets, need to use a clock event
    cb.dispatch_event('click')
    count = page.get_by_test_id("itemsfound")
    expect(count).to_contain_text(re.compile(r"[1-9][0-9]*"))


def test_click_facet_fr(page: Page):
    page.goto(search_path('notesdinfo', 'fr'))
    cb = page.get_by_label("facet-owner_org-tbs-sct")
    # Because of the way Search handles facets, need to use a clock event
    cb.dispatch_event('click')
    count = page.get_by_test_id("itemsfound")
    expect(count).to_contain_text(re.compile(r"[1-9][0-9]*"))


def test_simple_search_en(page: Page):
    page.goto(search_path('briefing_titles', 'en'))
    tb = page.get_by_label("Search text")
    tb.fill('58705277')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    # Should find exactly one record
    expect(count).to_have_text("one")


def test_simple_search_fr(page: Page):
    page.goto(search_path('notesdinfo', 'fr'))
    tb = page.get_by_label("Recherche")
    tb.fill('58705277')
    bt = page.get_by_label("Search button")
    bt.click()
    count = page.get_by_test_id("itemsfound")
    # Should find exactly one record
    expect(count).to_have_text("un")


def test_simple_record_en(page: Page):
    page.goto(search_path('briefing_titles', 'en', '/record/tbs-sct,58705277'))
    expect(page).to_have_title("Briefing Note Titles and Numbers")


def test_simple_record_fr(page: Page):
    page.goto(search_path('notesdinfo', 'fr', '/record/tbs-sct,58705277'))
    expect(page).to_have_title("Titres et numéros des notes d’information")
