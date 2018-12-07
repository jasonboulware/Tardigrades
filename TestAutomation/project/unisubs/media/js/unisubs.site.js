// Amara, universalsubtitles.org
//
// Copyright (C) 2013 Participatory Culture Foundation
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see
// http://www.gnu.org/licenses/agpl-3.0.html.

var Site = function(Site) {
    /*
     * This is the master JavaScript file for
     * the Amara website.
     */

    var that = this;

    this.init = function() {

        // Global cached jQuery objects
        this.$html = $('html');
        this.$body = $('html');

        this.pageShowCallbacks = new Array();

        // Base JS (any page that extends base.html)
        if (this.$html.hasClass('base')) {
            this.Views['base']();
        }

        // Page specific JS
        if (this.$html.attr('id')) {
            this.Views[this.$html.attr('id')]();
        }

    };
    this.onPageShow = function() {
        if(this.onPageShowCalled == null) {
            // This is the initial load of the page, we don't need to do
            // anything this time around.
            this.onPageShowCalled = true;
            return;
        }
        for(var i=0; i < this.pageShowCallbacks.length; i++) {
            this.pageShowCallbacks[i]();
        }
    };
    this.callOnPageShow = function(callback) {
        /*
         * Schedule a function to be called during future "pageshow" events.
         * This fires when the user navigates away from the page, then back to
         * it, and the page is in the back-forward cache on FF/chrome.
         */
        this.pageShowCallbacks.push(callback);
    };
    this.Utils = {
        /*
         * These are reusable utilities that are
         * usually run on multiple pages. If you
         * find duplicate code that runs on multiple
         * pages, it should be converted to a
         * utility function in this object and
         * called from each of the specific views,
         * like this:
         *
         *     that.Utils.chosenify();
         *
         */
	parsedQuery: function() {
	    var query = window.location.search;
	    var output = {};
	    if (query && query[0] === '?')
		query.slice(1).split('&').forEach(function(x) {
		    var vals = x.split('=');
		    if (vals.length == 2)
			output[vals[0]] = vals[1];
		});
	    return output;
	},
        chosenify: function() {
            $('select', '.v1 .content').not('.raw-select').filter(function() {
                if ($(this).parents('div').hasClass('ajaxChosen')) {
                    return false;
                }
                if ($(this).parents('div').hasClass('no-chosen')) {
                    return false;
                }
                return true;
            }).chosen().change(function() {
                $select = $(this);

                // New message
                if ($('body').hasClass('new-message')) {
                    $option = $('option:selected', $select);

                    if ($select.attr('id') === 'id_team') {
                        if ($option.val() !== '') {
                            $('div.recipient, div.or').addClass('disabled');
                            $('select#id_user').attr('disabled', 'disabled').trigger('liszt:updated');
                        } else {
                            $('div.recipient, div.or').removeClass('disabled');
                            $('select#id_user').removeAttr('disabled').trigger('liszt:updated');
                        }
                    }
                }
            });
        },
        messagesDeleteAndSend: function(from_sentbox) {
            $('.messages .delete').click(function(){
                if (confirm(window.DELETE_MESSAGE_CONFIRM)){
                    var $this = $(this);
                    var message_id = $this.attr('message_id');
                    var callback = function(response) {
                        if (response.error){
                            $.jGrowl.error(response.error);
                        } else {
                            $this.parents('li.message').fadeOut('fast', function() {
                                $(this).remove();
                            });
                        }
                    };
                    if (from_sentbox)
                        MessagesApi.remove_sent(message_id, callback);
                    else
                        MessagesApi.remove(message_id, callback);
                }
                return false;
            });
            $('#send-message-form').ajaxForm({
                type: 'RPC',
                api: {
                    submit: MessagesApi.send
                },
                success: function(data, resp, $form){
                    if (data.errors) {
                        for (key in data.errors){
                            var $field = $('input[name="'+key+'"]', $form);
                            var error = '<p class="error_list">'+data.errors[key]+'</p>';
                            if ($field.length){
                                $field.before(error);
                            }else{
                                $('.global-errors', $form).prepend(error);
                            }
                        }
                    } else {
                        if (resp.status) {
                            $.jGrowl(window.MESSAGE_SUCCESSFULLY_SENT);
                        }
                        $('a.close', '#msg_modal').click();
                        $form.clearForm();
                    }
                },
                beforeSubmit: function(formData, $form, options){
                    $('p.error_list', $form).remove();
                }
            });
        },
        resetLangFilter: function($select) {
            if (typeof $select == 'undefined') {
                $select = $('select#lang-filter');
            }

            if (window.REQUEST_GET_LANG) {
                $opt = $('option[id="lang-opt-' + window.REQUEST_GET_LANG + '"]');
            } else {
                $opt = $('option[id="lang-opt-mine"]');
            }

            $select.children().removeAttr('selected');
            $opt.attr('selected', 'selected');
            $select.trigger('liszt:updated');
        },
        resetProjFilter: function($select) {
            if (typeof $select == 'undefined') {
                $select = $('select.project-filter');
            }

            var $defaultOpt = $('option[selected]', $select);
            // We want to set the selected property, but not change any
            // attributes.  Newer versions of jquery support this, but for now
            // we have to use straight javascript to do it.
            if($defaultOpt.length > 0) {
                $defaultOpt[0].selected = true;
                $select.trigger('liszt:updated');
            }
        },
        collapsibleLists: function($lists) {
            $.each($lists, function() {
                var $list = $(this);
                var $anchor = $('li.expand a', $list);
                var anchorTextShowAll = $anchor.children('span.all').text();
                var anchorTextShowLess = $anchor.children('span.less').text();

                $anchor.click(function(e) {
                    if ($list.hasClass('expanded')) {
                        $anchor.text(anchorTextShowAll);
                        $list.removeClass('expanded');
                        $list.addClass('collapsed');
                    } else {
                        $anchor.text(anchorTextShowLess);
                        $list.removeClass('collapsed');
                        $list.addClass('expanded');
                    }
                    e.preventDefault();
                });
            });
        },
        assignTask: function(task, callback){
            $.ajax({
                url: window.ASSIGN_TASK_AJAX_URL,
                type: 'POST',
                data: {
                    task: task,
                    assignee: window.CURRENT_USER_ID
                },
                success: function() {
                    callback();
                }
            });
        },
        bulkCheckboxes: function(bulkCheckbox, bulkableCheckboxes, bulkCheckboxAnchor) {
	    bulkableCheckboxes.attr('checked', false);
	    bulkCheckbox.attr("checked", false);
	    bulkCheckbox.change(function() {
		bulkableCheckboxes.attr('checked', $(this).attr('checked'));
		bulkCheckbox.attr("checked", $(this).attr('checked'));
	    });
	    bulkableCheckboxes.change(function() {
		bulkCheckbox.attr('checked', false);
	    });
	    bulkCheckboxAnchor.click(function() {
		bulkCheckbox.attr("checked", !bulkCheckbox.attr("checked")).change();
		return false;
	    });
	},
	filterOptions: function(filter, store, select) {
	    // Populate the store if not done yet
	    if (store.text() == "") {
		$('option[class^="store-"]').each(function() {
		    var optvalue = $(this).val();
		    var optclass = $(this).attr('class');
		    var opttext = $(this).text();
		    optionlist = store.text() + "@%" + optvalue + "@%" + optclass + "@%" + opttext;
		    store.text(optionlist);
		});
	    }
	    // Delete everything
	    $('option[class^="store-"]').remove();
	    // Put the filtered stuff back
	    populateOptions = that.Utils.rewriteOptions(filter, store);
	    select.html(populateOptions);
	},
	rewriteOptions: function (filter, store) {
	    // Rewrite only the filtered stuff back into the option
	    var options = store.text().split('@%');
	    var result = false;
	    var filterClass = "store-" + filter;
	    var optionListing = "";

	    filterClass = (filter != "") ? filterClass : "all";
	    //first variable is always the value, second is always the class, third is always the text
	    for (var i = 3; i < options.length; i = i + 3) {
		if (options[i - 1] == filterClass || filterClass == "all") {
		    optionListing = optionListing + '<option value="' + options[i - 2] + '" class="sub-' + options[i - 1] + '">' + options[i] + '</option>';
		    result = true;
		}
	    }
	    if (result) {
		return optionListing;
	    }
	},
        truncateTextBlocks: function(blocks, maxHeight) {
            // Takes a list of jQuery objects and sets up
            // a nice truncate-by-height UI.
            blocks.each(function() {
                var $block = $(this);

                if ($block.height() > maxHeight) {
                    $block.addClass('truncated');
                    $block.height(maxHeight);

                    $block.after('<a href="#" class="truncated-expand">Expand</a>');

                    var $anc = $('a.truncated-expand', $block.parent());
                    $anc.click(function() {
                        if ($block.height() !== maxHeight) {
                            $block.height(maxHeight);
                            $anc.text('Expand');
                            $anc.removeClass('expanded');
                        } else {
                            $block.height('auto');
                            $anc.text('Collapse');
                            $anc.addClass('expanded');
                        }

                        return false;
                    });
                }
            });
        }
    };
    this.analytics = function() {
        if (typeof sendAnalytics !== 'undefined')
            sendAnalytics.apply(undefined, Array.prototype.slice.call(arguments, 0));
    };
    this.setupSearchBox = function() {
	var closure = this;
        $('form.search-form').submit(function(ev) {
	    closure.analytics('website', 'search', $('#id_q').val());
        });
    };
    this.setupModalDialogs = function($rootElt) {
        $('a.open-modal', $rootElt).each(function() {
            var $link = $(this);
            var modalId = $link.attr('href');
            var $modal = $(modalId);
            $link.bind('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                that.openModalForLink($link);
            });
            if($modal.hasClass('start-open')) {
                that.openModalForLink($link);
            }
        });
    }
    this.openModalDialog = function(modal_id) {
        var $target = $(modal_id);
        var $document = $(document);
        $target.addClass('shown');
        $('body').append('<div class="well"></div>');

        function handleCloseEvent(evt) {
            evt.preventDefault();
            evt.stopPropagation();
            $target.removeClass('shown');
            $('body div.well').remove();
            $closeButton.unbind('click.modal');
            $document.unbind('click.modal');
            $document.unbind('keydown.modal');
        }

        $closeButton = $('.action-close, .close', $target);
        $closeButton.bind('click.modal', handleCloseEvent);
        $document.bind('click.modal', function(evt) {
            var $target = $(evt.target);
            if($target.closest('aside.modal').length == 0 &&
                $target.closest('.bootstrap .modal').length == 0) {
                handleCloseEvent(evt);
            }
        });
        $document.bind('keydown.modal', function(evt) {
            if (evt.keyCode === 27) {
                handleCloseEvent(evt);
            }
        });
    };
    this.openModalForLink = function(link) {
        var modalId = link.attr('href');
        if(modalId == '#multi-video-create-subtitles-modal') {
            that.setupMultiVideoCreateSubtitlesModal(link);
        }
        that.openModalDialog(modalId);
    }
    this.setupMultiVideoCreateSubtitlesModal = function(link) {
        var form = ('#multi-video-create-subtitles-modal');
        var video_id = link.data('video-id');
        var primary_audio_lang_code = link.data('video-primary-audio-lang-code');
        var langs = link.data('video-langs').split(':');
        var video_input = $('input[name=video]', form);
        var primary_audio_lang_select = $('select[name=primary_audio_language_code]', form);
        var language_select = $('select[name=subtitle_language_code]', form);

        video_input.val(video_id);
        if(primary_audio_lang_code) {
            primary_audio_lang_select.val(primary_audio_lang_code);
            primary_audio_lang_select.attr('readonly', "1");
        } else {
            primary_audio_lang_select.val('');
            primary_audio_lang_select.removeAttr('readonly');

        }
        $('option', language_select).removeAttr('disabled');
        _.each(langs, function(lang) {
            $('option[value=' + lang + ']', language_select).attr('disabled',
                "1");

        });
        $("option:not([disabled]):first", language_select).attr('selected',
                "1");
    }

    this.Views = {
        /*
         * Each of these views runs on a specific
         * page on the Amara site
         * (except for base, which runs on every
         * page that extends base.html)
         *
         * Adding a view is as simple as adding an
         * ID attribute to the specific page's <html>
         * element, and adding the corresponding view
         * below.
         */

        // Global
        base: function() {

            /*
             * TODO: The modules in this section need to
             * be pulled out into that.Utils and only
             * initialized on pages that use them.
             */
            if ($('.abbr').length) {
                $('.abbr').each(function(){
                    var container = $(this);
                    var content = $(this).children('div');
                    var oheight = content.css('height', 'auto').height();
                    content.css('height','6em');
                    $(this).find('.expand').live('click', function(e){
                        e.preventDefault();
                        if(container.hasClass('collapsed')){
                            content.animate({
                                height: oheight
                            }, 'fast');
                            $(this).text('Collapse ↑');
                        } else {
                            content.animate({
                                height: '6em'
                            }, 'fast');
                            $(this).text('Show all ↓');
                        }
                        container.toggleClass('collapsed expanded');
                    });
                });
            }
            if ($('#sort-filter').length) {
                $('#sort-filter').click(function(e) {
                    e.preventDefault();
                    $('.filters').toggle();
                    $(this).children('span').toggleClass('open');
                });
		if ($('#sort-filter').hasClass("default-open")) {
                    $('.filters').show();
                    $('#sort-filter').children('span').addClass('open');
		}
                $('select', '.filters:not(.no-ajax)').change(function(e) {
                    window.location = $(this).children('option:selected').attr('value');
                });
            }
            $('select.languageSwitcher').each(function(i, select) {
                select = $(select);
                var alreadyAdded = {};
                var popularLanguageGroup = $('<optgroup/>', {
                    label: popularLanguagesLabel
                });
                var allLanguageGroup = $('<optgroup/>', {
                    label: allLanguagesLabel
                });
                function makeOption(optgroup, lc) {
                    if(!localeChoices[lc] || alreadyAdded[lc]) return;
                    var option = new Option(getLanguageName(lc), lc);
                    if(lc == LANGUAGE_CODE) {
                        option.selected = true;
                    }
                    optgroup.append(option);
                    alreadyAdded[lc] = 1;
                }
                $.each(popularLanguages, function(i, lc) {
                    makeOption(popularLanguageGroup, lc);
                });
                $.each(allLanguages, function(i, lc) {
                    makeOption(allLanguageGroup, lc);
                });
                select.append(popularLanguageGroup);
                select.append(allLanguageGroup);

                select.change(function(evt) {
                    var newUrl = window.location.pathname.replace(new RegExp("^/[^/]*"), "/" + select.val());
                    Cookies.set('language', select.val(), {expires: 5 * 365});
                    window.location = newUrl;
                    return false;
                });
            });
            $('.notes textarea').keypress(function(evt) {
                if(evt.which == 13 && !evt.shiftKey) {
                    evt.preventDefault();
                    evt.stopPropagation();
                    $(this).closest('form').submit();
                    return true;
                }
            });
            that.setupModalDialogs();
            that.setupSearchBox();
            $.fn.tabs = function(options){
                this.each(function(){
                    var $this = $(this);

                    var $last_active_tab = $($('li.current a', $this).attr('href'));
                    $('a', $this).add($('a.link_to_tab')).click(function(){
                        var href = $(this).attr('href');
                        $last_active_tab.hide();
                        $last_active_tab = $(href).show();
                        $('li', $this).removeClass('current');
                        $('a[href='+href+']', $this).parent('li').addClass('current');
                        document.location.hash = href.split('-')[0];
                        return false;
                    });
                });
                if (document.location.hash){
                    var tab_name = document.location.hash.split('-', 1);
                    if (tab_name) {
                        $('a[href='+tab_name+'-tab]').click();
                        document.location.href = document.location.href;
                    }
                }
                return this;
            };
            function addCSRFHeader($){
                /* Django will guard against csrf even on XHR requests, so we need to read
                   the value from the cookie and add the header for it */
                $.ajaxSetup({
                    beforeSend: function(xhr, settings) {
                        function getCookie(name) {
                            var cookieValue = null;
                            if (document.cookie && document.cookie !== '') {
                                var cookies = document.cookie.split(';');
                                for (var i = 0; i < cookies.length; i++) {
                                    var cookie = jQuery.trim(cookies[i]);
                                    // Does this cookie string begin with the name we want?
                                    if (cookie.substring(0, name.length + 1) == (name + '=')) {
                                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                                        break;
                                    }
                                }
                            }
                            return cookieValue;
                        }
                        if (!((/^http:.*/).test(settings.url) || (/^https:.*/).test(settings.url))) {
                            // Only send the token to relative URLs i.e. locally.
                            xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
                        }
                    }
                });
            }
            $('#closeBut').click(function(){
                $('#messages').remove();
                return false;
            });
            $('li.search input').keypress(function(e) {
                if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
                    $('li.search form').submit();
                    return false;
                }
                else
                    return true;
            });
            jQuery.Rpc.on('exception', function(e){
                jQuery.jGrowl.error(e.message);
            });
            if (window.OLD_MODAL) {
                $.mod();
                $.metadata.setType("attr", "data");
            }
            if ($('#language_modal').length || $('#apply-modal').length || $('#language_profile').length) {
                var cookies_are_enabled = function() {
                    document.cookie = 'testcookie=1';
                    return (document.cookie.indexOf('testcookie=1') != -1) ? true : false;
                };
                ProfileApi.get_user_languages(function(r) {
                    if (!r) {
                        return;
                    }
                    $('.language_bar span').remove();
                    var h = '';
                    for (l in r) {
                        h += '<span>'+ r[l] + '</span>, ';
                    }
                    $('.language_bar a').before('<span class="selected_language">' + h.slice(0,-2) + '</span>');
                });
                if (cookies_are_enabled()) {
		    var $w = $('#language_modal, #apply-modal, #language_profile');
		    [$('#language_modal'), $('#apply-modal'), $('#language_profile')].forEach(function($w) {
                        if($w.length)
                            $w.find('.submit_button').click(function() {
                                var values = {};
                                var has_value = false;
                                $('select', $w).each(function(i, item) {
                                    var $item = $(item);
                                    values[$item.attr('name')] = $item.val();
                                    if (!has_value && $item.val()) {
                                        has_value = true;
                                    }
                                });
                                if (!has_value) {
                                    $.jGrowl.error(window.LANGUAGE_SELECT_ERROR);
                                } else {
                                    if (typeof submit_languages_callback === "undefined")
                                        $w.html(window.LANGUAGE_SELECT_SAVING);
                                    ProfileApi.select_languages(values, function() {
                                            if (typeof submit_languages_callback != "undefined")
        					submit_languages_callback();
                                            else if (typeof redirect != "undefined")
                                                window.location = redirect;
                                            else
                                                window.location.reload(true);
                                        }, function() {
                                            $w.modClose();
                                        }
                                    );
                                }
                                return false;
                        });
                    });
                    $w.find('.close_button').click(function() {
                        $w.modClose();
                        return false;
                    });
                    if (window.FORCE_ASK) {
                        $w.mod({closeable: false});
                    } else {
                        $w.find('.close_button').show();
                    }
                } else {
                    $('#lang_select_btn').hide();
                }
            }
            $('.announce-banner').each(function() {
                var banner = $(this);
                var announcementId = banner.data('id');
                var lastHiddenAnnouncement = Cookies.get('lastHiddenAnnouncement');
                if(lastHiddenAnnouncement && lastHiddenAnnouncement >= announcementId) {
                    banner.hide();
                }
                $('.hide-announcement', this).click(function() {
                    banner.hide();
                    Cookies.set('lastHiddenAnnouncement', announcementId);
                    return false;
                });
            });

            $listsCollapsible = $('ul.list-collapsible');
            if ($listsCollapsible.length) {
                that.Utils.collapsibleLists($listsCollapsible);
            }

            window.usStartTime = (new Date()).getTime();
            window.addCSRFHeader = addCSRFHeader;
            addCSRFHeader($);

            if ($('select.goto').length) {
                $('select.goto').change(function(e) {
                    window.location = $(this).children('option:selected').attr('value');
                });
            }

            $('#youtube-prompt a.hide').click(function() {
                $('#youtube-prompt').hide();
                $.cookie('hide-yt-prompt', 'yes', { path: '/', expires: 365 });
                return false;
            });

            if ($('select[name="admin-edit-specific-version"]').length) {
                var $versionSelect = $('select[name="admin-edit-specific-version"]');

                $versionSelect.change(function() {
                    window.location = $versionSelect.val();
                });
            }
        },

        // Public
        subtitle_view: function() {
            var DIFFING_URL = function() {
                var url = window.DIFFING_URL;
                return url.replace(/11111/, '<<first_pk>>').replace(/22222/, '<<second_pk>>');
            }();
            function get_compare_link(first_pk, second_pk) {
                return DIFFING_URL.replace(/<<first_pk>>/, first_pk).replace(/<<second_pk>>/, second_pk);
            }
            function setupRevisions() {
                $('.version_checkbox', '.revisions').change( function() {
                    var $this = $(this);
                    var checked_length = $('.version_checkbox:checked').length;

                    if ($this.attr('checked') && (checked_length > 2)) {
                        $this.attr('checked', '');
                    }
                });
                $('.compare_versions_button').click( function() {
                    var $checked = $('.version_checkbox:checked');
                    if ($checked.length !== 2) {
                        alert(window.SELECT_REVISIONS_TRANS);
                    } else {
                        var url = get_compare_link($checked[0].value, $checked[1].value);
                        window.location.replace(url);
                    }
                });
            }
            setupRevisions();

            $('#edit_subtitles_button').click( function(e) {
                if (!(localStorage && localStorage.getItem)) {
                    alert("Sorry, you'll need to upgrade your browser to use the subtitling dialog.");
                    e.preventDefault();
                }
            });
            $('#rollback').click(function() {
                if (!confirm('Subtitles will be rolled back to a previous version')){
                    return false;
                }
            });
            that.Utils.truncateTextBlocks($('div.description'), 90);
        },
        video_set_language: function() {
            that.Utils.chosenify();
        },
        diffing: function() {
            that.Utils.truncateTextBlocks($('div.description'), 90);
        },
        // Teams
        team_approvals: function() {
            that.Utils.chosenify();
            that.Utils.bulkCheckboxes($('input.bulk-select'), $('input.bulkable'), $('a.bulk-select'));
	},
        teams_activity: function() {
            function onMoreClicked(e) {
                var parameters = that.Utils.parsedQuery();
                var $link = $(this);
                parameters["page"] = $link.attr("data-page");
                var loadingIcon = $('img.loading-icon');
                e.preventDefault();
                var href = "?";
                for (var key in parameters)
                    href +=  key + "=" + parameters[key] + "&";
                $link.attr("href", href);
                loadingIcon.show();
                $link.remove();
                $.get($link.attr('href'), function(data) {
                    var $data = $(data);
                    $('#activity-list ul').append($data.find('li'));
                    $('.pagination').append($data.find('a.show-more'));
                    $('div.pagination a').click(onMoreClicked);
                    loadingIcon.hide();
                });
            }
            that.Utils.chosenify();
            $('div.pagination a').click(onMoreClicked);
        },
        move_videos: function() {
            that.Utils.chosenify();
            that.Utils.bulkCheckboxes($('input.bulk-select'), $('input.bulkable'), $('a.bulk-select'));
	    $('#id_team').change(function() {
		var filter = $(this).val();
		that.Utils.filterOptions(filter, $('#projects-store'), $('#projects-select'));
	    }).change();
        },
        team_applications: function() {
            that.Utils.chosenify();
            that.Utils.truncateTextBlocks($('div.application-note'), 50);
            that.Utils.bulkCheckboxes($('input.bulk-select'), $('input.bulkable'), $('a.bulk-select'));
        },
        review_sync_errors: function() {
            that.Utils.bulkCheckboxes($('input.bulk-select'), $('input.bulkable'), $('a.bulk-select'));
        },
        user_review_sync_errors: function() {
            that.Utils.bulkCheckboxes($('input.bulk-select'), $('input.bulkable'), $('a.bulk-select'));
        },
        team_members_list: function() {
            that.Utils.resetLangFilter();
            that.Utils.chosenify();
        },
        team_tasks: function() {
            $('a.action-assign').click(function(e) {

                $('div.assignee-choice').hide();

                $form = $(e.target).parents('.admin-controls').siblings('form.assign-form');

                $assignee_choice = $form.children('div.assignee-choice');
                $assignee_choice.fadeIn('fast');

                if (!window.begin_typing_trans) {
                    window.begin_typing_trans = $('option.begin-typing-trans').eq(0).text();
                }
                $select = $form.find('select');
                $select.children('option').remove();
                $select.append('<option value="">-----</option>');
                $select.append('<option value="">' + window.begin_typing_trans + '</option>');
                $select.trigger('liszt:updated');

                $chzn_container = $assignee_choice.find('.chzn-container');
                $chzn_container.css('width', '100%');

                $chzn_drop = $chzn_container.find('.chzn-drop');
                $chzn_drop.css('width', '99%');

                $chzn_input = $chzn_drop.find('input');
                $chzn_input.css('width', '82%');

                return false;
            });
            $('a.action-decline').click(function(e) {
                $('form', this).submit();
                e.preventDefault();
            });
            $('.assignee-choice a.cancel').click(function(e) {
                $(e.target).parents('.assignee-choice').fadeOut('fast');
                return false;
            });
            $('a.action-assign-submit').click(function(e) {
                $(e.target).closest('form').submit();
                return false;
            });
            $('div.member-ajax-chosen select', '.v1 .content').ajaxChosen({
                method: 'GET',
                url: '/en/teams/' + window.TEAM_SLUG + '/members/search/',
                dataType: 'json'
            }, function (data) {
                var terms = {};
                $.each(data.results, function (i, val) {
                    var can_perform_task = data.results[i][2];

                    if (can_perform_task) {
                        terms[data.results[i][0]] = data.results[i][1];
                    }
                });
                return terms;
            });

            $('a.upload-draft-button').click(function() {
                $('input#id_task').val($(this).data('task'));
            });

            that.Utils.resetLangFilter($('select#id_task_language'));
            that.Utils.resetProjFilter();
            that.callOnPageShow(function() {
                that.Utils.resetLangFilter($('select#id_task_language'));
            });
            that.callOnPageShow(that.Utils.resetProjFilter);
            that.Utils.chosenify();
        },
        team_video_edit: function() {
            that.Utils.chosenify();

            var $move_form = $('form.move-video');

            $('a#move-video').click(function() {
                var $selected_team = $('select#id_team option:selected', $move_form);
                var $selected_team_projects = $('#team-projects-' + $selected_team.data('team-pk'));
                var $selected_team_projects_select = $('select', $selected_team_projects);
                $('div.team-projects').hide();

                if ($selected_team_projects_select.children('option').length) {
                    $selected_team_projects.show();
                }
            });

            $move_form.submit(function() {
                var $selected_team = $('select#id_team option:selected', $move_form);
                $('input[name="team_video"]', $move_form).val($selected_team.val());
                $('input[name="team"]', $move_form).val($selected_team.data('team-pk'));

                var $selected_team_projects = $('#team-projects-' + $selected_team.data('team-pk'));
                var $selected_team_projects_select = $('select', $selected_team_projects);

                // This team has projects. Grab the selected one.
                if ($selected_team_projects_select.children('option').length) {
                    var $selected_project = $('option:selected', $selected_team_projects_select).val();
                    $('input[name="project"]', $move_form).val($selected_project);
                } else {
                    $('input[name="project"]', $move_form).val('');
                }
            });

            var $move_modal_form = $('div#move-modal form');

            $move_modal_form.submit(function() {
                $move_form.submit();
                return false;
            });
        },
        team_dashboard: function() {
        },
        team_videos_list: function() {
            $form = $('form', 'div#remove-modal');

            $('a.remove-video').click(function() {
                $form.attr('action', $(this).siblings('form').attr('action'));
            });
            $form.submit(function() {
                var $checked = $('input[name="del-opt"]:checked', 'div#remove-modal');
                if ($checked.val() == 'total-destruction') {
                    if (confirm('Are you sure you want to permanently delete this video? This action is irreversible.')) {
                        return true;
                    } else {
                        return false;
                    }
                } else {
                    if (confirm('All open tasks for this video will be aborted, and in-progress subtitles will be published. Do you want to proceed?')) {
                        return true;
                    } else {
                        return false;
                    }
                }
            });
            $('form.filters.videos-list select').chosen({
                disable_search_threshold: 6
            });

        },
        team_settings_permissions: function() {
            $workflow = $('#id_workflow_enabled');

            // Fields to watch
            $subperm = $('#id_subtitle_policy');
            $transperm = $('#id_translate_policy');
            $revperm = $('#id_review_allowed');
            $appperm = $('#id_approve_allowed');

            // Inspect/observe the workflow checkbox
            if ($workflow.attr('checked')) {
                $('.v1 .workflow').show();
            }
            $workflow.change(function() {
                if ($workflow.attr('checked')) {
                    $('.v1 .workflow').show();
                    $revperm.trigger('change');
                    $appperm.trigger('change');
                } else {
                    $('.v1 .workflow').hide();
                    $('#review-step').hide();
                    $('#approve-step').hide();
                }
            });

            // Observe the permissions fields
            $subperm.change(function() {
                $('#perm-sub').html($subperm.children('option:selected').html());
            });
            $transperm.change(function() {
                $('#perm-trans').html($transperm.children('option:selected').html());
            });
            $revperm.change(function() {
                if ($revperm.children('option:selected').val() !== '0') {
                    $('#review-step').show();
                    $('#perm-rev').html($revperm.children('option:selected').html());
                } else {
                    $('#review-step').hide();
                }
            });
            $appperm.change(function() {
                if($appperm.children('option:selected').val() !== '0') {
                    $('#approve-step').show();
                    $('#perm-app').html($appperm.children('option:selected').html());
                } else {
                    $('#approve-step').hide();
                }
            });

            // Load state
            $subperm.trigger('change');
            $transperm.trigger('change');
            $revperm.trigger('change');
            $appperm.trigger('change');
        },
        team_settings_languages: function() {
            that.Utils.chosenify();
        },
        team_settings_externalsites: function() {
            // Track accounts that were enabled but are now disabled;
            function getAccountType(fieldset) {
                var classes = $(fieldset).attr('class').split(" ");
                for(var i=0; i < classes.length; i++) {
                    if(classes[i] != 'disabled') {
                        return classes[i];
                    }
                }
                return "";
            }
            var accountsToBeDisabled = {};
            function accountWillBeDisabled() {
                for(var key in accountsToBeDisabled) {
                    if(accountsToBeDisabled[key]) {
                        return true;
                    }
                }
                return false;
            }


            $('form input[type="checkbox"][name$="-enabled"]').change(function() {
                var fieldset = $(this).closest('fieldset');
                var accountFields = $('div.account-fields', fieldset);
                if(this.checked) {
                    accountFields.slideDown();
                    delete accountsToBeDisabled[getAccountType(fieldset)];
                } else {
                    if(!fieldset.hasClass('disabled')) {
                        accountsToBeDisabled[getAccountType(fieldset)] = true;
                    }
                    accountFields.slideUp();
                }
            });


            var form = $('form#external-accounts');
            form.submit(function(evt) {
                if(accountWillBeDisabled()) {
                    evt.preventDefault();
                    window.site.openModalDialog('#confirm-delete-account-modal');
                    $('#confirm-delete-account-modal button.continue').click(function() {
                        accountsToBeDisabled = {};
                        form.submit();
                    });

                }
            });

            function updateBrightcoveFeedInputs() {
                var cbx = $('#id_brightcove-feed_enabled');
                var feedFields = $('fieldset.brightcove fieldset.feed-fields input');
                if(cbx.attr('checked')) {
                    feedFields.removeAttr('disabled');
                } else {
                    feedFields.attr('disabled', '1');
                }
            }

            updateBrightcoveFeedInputs();
            $('#id_brightcove-feed_enabled').change(updateBrightcoveFeedInputs);
        },

        // Profile
        user_dashboard: function() {
            $('a.action-decline').click(function() {
                $(this).siblings('form').submit();
                return false;
            });
        },
        user_account: function() {
            $('#account-type-select').change(function() {
                if(this.value == 'Select...') {
                    $('#account-modal input[type="submit"]').attr('disabled','disabled');
                } else {
                    $('#account-modal input[type="submit"]').removeAttr('disabled');
                }
            });
            $(".api-key-holder").click(function(){
                $(this).select();
            });
            $(".get-new-api-bt").click(function(e){
                e.preventDefault();
                $.ajax({
                    url: $(this).attr("href"),
                    dataType: "json",
                    type: "POST",
                    success: function(res){
                        $(".api-key-holder").text(res.key);
                        $(".get-new-api-bt").text("Reset your API key");
                        $(".api-key-status").text("Key generated, enjoy!");
                    }
                });
                $("#api div").show();
                return false;
            });
            $.urlParam = function(name){
                var results = new RegExp('[\\?&amp;]' + name + '=([^&amp;#]*)').exec(window.location.href);
                if (results)
                    return results[1];
                return 0;
            }
            if($.urlParam('prompt') == 'true') {
                $('a[href="#youtube-modal"]').click();
            }
        },
        bulk_deletable_messages: function(from_sentbox) {
            $('.delete-selected').bind('click', function(event) {
                    if (confirm(window.DELETE_MESSAGES_CONFIRM)) {
			var $this = $(this);
			var messages = $('input.bulkable:checked', '.v1 .messages.listing').map(function() {
			    return $(this).attr('value');}).get();
			var callback = function(response) {
                            if (response.error) {
				$.jGrowl.error(response.error);
                            } else {
				var current_url = window.location.href;
				var redirect_url = current_url.replace(/([&\?])page=\d+/, "$1page=1");
				window.location = redirect_url;
                            }
			};
			if (from_sentbox)
                            MessagesApi.remove_sent(messages, callback);
			else
                            MessagesApi.remove(messages, callback);
                    }
                    return false;
            });
        },
        // Messages
        messages_list: function() {
            var reply_msg_data;
            $.metadata.setType('attr', 'data');

            if (!window.REPLY_MSG_DATA) {
                reply_msg_data = null;
            } else {
                reply_msg_data = window.REPLY_MSG_DATA;
            }
            function set_message_data(data, $modal) {
                $('#message_form_id_user').val(data['author-id']);
                $('#message_form_id_thread').val(data['thread']);
                $('.author-username', $modal).html(data['author-username']);
                $('.message-content', $modal).html(data['message-content']);
                $('.message-subject').html(data['message-subject-display']);
                $('#message_form_id_subject').val('Re: '+data['message-subject']);

                if (data['can-reply']) {
                    $('.reply-container textarea', $modal).val('');
                }
                return false;
            }
            if (reply_msg_data){
                set_message_data(reply_msg_data, $('#msg_modal'));
            }
            $('.reply').bind('click', function() {
                set_message_data($(this).metadata(), $('msg_modal'));
            });
            $('.mark-read').bind('click', function(event) {
                var $link = $(this);
                var data = $link.metadata();

                if (!data['is-read']) {
                    MessagesApi.mark_as_read(data['id'], function(response) {
                        if (response.error) {
                            $.jGrowl.error(response.error);
                        } else {
                            $li = $link.parents('li.message');
                            $li.removeClass('unread');
                            $li.find('span.unread').remove();
                            data['is-read'] = true;
                            $link.parent().remove();
                        }
                    });
                }
                set_message_data(data, $('#msg_modal'));
                return false;
            });
            $('.mark-as-read').bind('click', function(event) {
		MessagesApi.mark_as_read($('input.bulkable:checked', '.v1 .messages.listing').map(function() {
		    return $(this).attr('value');}).get(), function(response) {
			if (response.error) {
                            $.jGrowl.error(response.error);
			} else {
			    window.location.reload();
			}
                    });
		return false;
            });
            that.Utils.chosenify()
            this.bulk_deletable_messages(false);
            that.Utils.bulkCheckboxes($('input.bulk-select'), $('input.bulkable'), $('a.bulk-select'));
            that.Utils.messagesDeleteAndSend(false);
        },
        messages_sent: function() {
            this.bulk_deletable_messages(true);
            that.Utils.bulkCheckboxes($('input.bulk-select'), $('input.bulkable'), $('a.bulk-select'));
            that.Utils.messagesDeleteAndSend(true);
        },
        messages_new: function() {
            that.Utils.chosenify();

            $('.ajaxChosen select').ajaxChosen({
                method: 'GET',
                url: '/en/messages/users/search/',
                dataType: 'json'
            }, function (data) {
                var terms = {};
                $.each(data.results, function (i, val) {
                    var name;
                    if (data.results[i][2] !== '') {
                        name = ' - ' + data.results[i][2];
                    } else {
                        name = '';
                    }
                    terms[data.results[i][0]] = data.results[i][1] + name;
                });
                return terms;
            });
        },

        login: function() {

            /*$('.toggle-additional a').click(function(e) {

                e.preventDefault();

                var $more = $('ul.additional');
                var $anchor = $(this);

                if ($more.is(':visible')) {
                    $anchor.html('Show more providers');
                } else {
                    $anchor.html('Show fewer providers');
                }

                $more.animate({
                    height: 'toggle'
                }, 'fast');

            });*/

            $('.form-swap').click(function(e) {

                e.preventDefault();

                $('form.auth-form:hidden').show();
                $(this).parents('form').hide();
            });
        }
    };
};

$(function() {
    window.site = new Site();
    window.site.init();
    $(window).bind('pageshow', function() {
        window.site.onPageShow()
    });
});
