{% load i18n %}
var allLanguages = [ {% for code, name in languages %}"{{ code }}"{% if not forloop.last %},{% endif %}{% endfor %} ];
var popularLanguages = [{% for code in popular_languages %}"{{ code }}"{% if not forloop.last %},{% endif %}{% endfor %} ];
var languageNames = { {% for code, name in languages %}"{{ code }}": "{{ name|safe }}"{% if not forloop.last %},{% endif %}{% endfor %} };
var localeChoices = { {% for code in locale_choices %}"{{ code }}":1{% if not forloop.last %},{% endif %}{% endfor %} };

var allLanguagesLabel = {{ allLanguagesLabel|safe }};
var popularLanguagesLabel = {{ popularLanguagesLabel|safe }};

function getLanguageName(languageCode) {
    return languageNames[languageCode];
}
