(function(window, document, undefined) {

    // When the embedder is compiled, dependencies will be loaded directly before this
    // function. Set dependencies to use no-conflict mode to avoid destroying any
    // original objects.
    var __ = _.noConflict();
    var _$ = jQuery.noConflict();
    var _Backbone = Backbone.noConflict();
    var _Popcorn = Popcorn.noConflict();
    // _amara may exist with a queue of actions that need to be processed after the
    // embedder has finally loaded. Store the queue in toPush for processing in init().
    var toPush = window._amara || [];
    var originDomain = null;
    
    //////////////////////////////////////////////////////////////////
    //The following section is to communicate with the host page
    var hostPage = {};
    window.addEventListener('message', initReceiver, false);
    var apiDomain = function(on_amara) {
	if (on_amara && originDomain) return originDomain;
	return '//' + _amaraConf.baseURL;
    };
    var analytics = function() {
        if (typeof sendAnalytics !== 'undefined')
            sendAnalytics.apply(undefined, Array.prototype.slice.call(arguments, 0));
    };
    function initReceiver(e) {
	originDomain = e.origin;
	if (e.data) {
	    if (e.data.fromIframeController) {
		hostPage = {origin: e.origin, source: e.source, index: e.data.index};
                analytics('embedder', 'init-origin', e.origin);
		hostPage.source.postMessage({initDone: true, index: hostPage.index}, hostPage.origin);
		window.removeEventListener('message', initReceiver, false);
		window.addEventListener('message', resizeInside, false);
	    }
	}
    }
    function resizeInside(e) {
	if (e && e.data && e.data.resize) {
	    window._amara.amaraInstances[0].resize_();
	}
    }
    // Should be triggered whenever the size of the content of the widget changes
    function sizeUpdated(model) {
	if(hostPage.source) {
	    var width;
	    if (model && model.get("width"))
		width = model.get("width");
	    else
		width = _$(".amara-tools").width();
	    var height = _$(".amara-popcorn").height() + _$(".amara-tools").height();
            var documentHeight = _$(document).height();
            var fontSize = Math.max(documentHeight / 25.0, 14);
            _$(".amara-popcorn").css('font-size', fontSize + 'px');
	    hostPage.source.postMessage({resize: true, index: hostPage.index,
					 width: width,
					 height: height,
					 transcriptHeight: (_$(".amara-tools").height()) - 37,
					}, hostPage.origin);
	}
    }
    ////////////////////////////////////////////

    // Should be triggered when the content of the iframe is know
    // This content is used to have the host page include the transcript
    // for indexing 
    function setIndexingContent(content) {
	if(hostPage.source)
	    hostPage.source.postMessage({resize: false, index: hostPage.index,
					 content: content,
					}, hostPage.origin);
    }
    ////////////////////////////////////////////

    function notifyVideoLoadedToHost(error) {
	if(hostPage.source)
	    hostPage.source.postMessage({resize: false, index: hostPage.index,
					 videoReady: (error == undefined),
                                         error: error}, hostPage.origin);
    }

    function notifyThumbnailLoadedToHost(args) {
	if(hostPage.source) {
	    hostPage.source.postMessage({resize: false, index: hostPage.index,
					 thumbnailReady: args && (args.error == undefined),
                                         error: args && args.error}, hostPage.origin);
	    if (args && args.model)
		sizeUpdated(args.model);
	} else
            setTimeout(function() { notifyThumbnailLoadedToHost(args && args.error); }, 50);
    }

    function regexEscape(str) {
        var specials = /[.*+?|()\[\]{}\\$^]/g; // .*+?|()[]{}\$^
        return str.replace(specials, "\\$&");
    }

    function padWithZeros(number, width) {
        var numString = number.toString();
        var characters = [];

        for(var i=numString.length; i < width; i++) {
            characters.push("0");
        }
        characters.push(numString);
        return characters.join('');
    }

    function formatTime(milliseconds) {
        if(milliseconds === undefined || milliseconds === null || milliseconds < 0) {
            return '';
        }
        var seconds = Math.floor(milliseconds / 1000);
        var hours = Math.floor(seconds / 3600);
        var minutes = Math.floor((seconds % 3600) / 60);

        var timeParts = [];
        if(hours > 0) {
            timeParts.push(hours);
            timeParts.push(padWithZeros(minutes, 2));
        } else {
            timeParts.push(minutes);
        }
        timeParts.push(padWithZeros(seconds % 60, 2));
        return timeParts.join(":");
    }

    function requestFullscreen() {
        var docElm = document.documentElement;
        if (docElm.requestFullscreen) {
            docElm.requestFullscreen();
        }
        else if (docElm.mozRequestFullScreen) {
            docElm.mozRequestFullScreen();
        }
        else if (docElm.webkitRequestFullScreen) {
            docElm.webkitRequestFullScreen();
        }
        else if (docElm.msRequestFullscreen) {
            docElm.msRequestFullscreen();
        }
    }

    function cancelFullscreen() {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        }
        else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        }
        else if (document.webkitCancelFullScreen) {
            document.webkitCancelFullScreen();
        }
        else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }

    function isFullscreen() {
        if(document.fullscreen !== undefined) {
            return document.fullscreen;
        } else if(document.mozFullScreen !== undefined) {
            return document.mozFullScreen;
        } else if(document.webkitIsFullScreen !== undefined) {
            return document.webkitIsFullScreen;
        } else if(document.msFullscreenElement !== undefined) {
            return document.msFullscreenElement;
        }
    }

    var Amara = function(Amara) {

        // For reference in inner functions.
        var that = this;

        // This will store all future instances of Amara-powered videos.
        // I'm trying really hard here to not use the word "widget".
        this.amaraInstances = [];

        // Private methods that are called via the push() method.
        var actions = {

            // The core function for constructing an entire video with Amara subtitles from
            // just a video URL. This includes DOM creation for the video, etc.
            embedVideo: function(options) {

                // Make sure we have a URL to work with.
                // If we do, init a new Amara view.
                if (__.has(options, 'url') && __.has(options, 'div')) {

                    that.amaraInstances.push(
                        new that.AmaraView({

                            // TODO: This needs to support a node OR ID string.
                            el: _$(options.div)[0],
                            model: new VideoModel(options)
                        })
                    );
                }
            }
        };

        // Utilities.
        var utils = {
            parseFloatAndRound: function(val) {
                return (Math.round(parseFloat(val) * 100) / 100).toFixed(2);
            }
        };

        // Video model.
        var VideoModel = _Backbone.Model.extend({

            // The initialization of these vars is unnecessary, but it's nice to know
            // what vars will *eventually* be on the video model.

            // This var will be true once we've retrieved the rest of the model attrs
            // from the Amara API.
            is_complete: false,

            // Set from within the embedder.
            div: '',
            height: '',
            initial_language: null,
            embed_on_amara: null,
            subtitles: [], // Backbone collection
            url: '',
            video_type: '',
            video_id: null,
            show_logo: true,
            show_subtitle_me: true,
            show_order_subtitles: true,
            show_improve_subtitles: true,
            show_download_subtitles: true,
            show_embed_code: true,
            show_subtitles_default: false,
            show_transcript_default: false,
            width: '',

            // Set from the Amara API
            all_urls: [],
            created: null,
            description: null,
            duration: null,
            id: null,
            languages: [],
	    languages_dir: {},
            original_language: null,
            project: null,
            resource_uri: null,
            team: null,
            team_type: null,
            thumbnail: null,
            title: null,

            // Every time a video model is created, do this.
            initialize: function() {
                var video = this;
                if(this.get('video_id')) {
                    var fetchingOneVideo = true;
                    var apiURL = '/api/videos/' + encodeURIComponent(this.get('video_id')) + '/?extra=player_urls';
                } else {
                    var fetchingOneVideo = false;
                    var apiURL = '/api/videos/?extra=player_urls&video_url=' + encodeURIComponent(this.get('url'));
                    if(this.get('team')) {
                        apiURL += '&team=' + encodeURIComponent(this.get('team'));
                    } else if(this.get('team') === null) {
                        apiURL += '&team=null';
                    }
                }
                this.subtitles = new that.Subtitles();
                // Make a call to the Amara API to get attributes like available languages,
                // internal ID, description, etc.
                _$.ajax({
                    url: apiURL,
                    success: function(resp) {
                        if(fetchingOneVideo) {
                            video.set('is_on_amara', true);
                            video.setFromVideoData(resp);
                        } else if (resp.objects.length) {
                            // The video exists on Amara.
                            video.set('is_on_amara', true);
                            // Set all of the API attrs as attrs on the video model.
                            video.setFromListingResponse(resp);
                        } else {
                            // The video does not exist on Amara.
                            video.set('is_on_amara', false);
                        }

                        // Mark that the video model has been completely populated.
                        video.set('is_complete', true);
                        video.view.render();
                        video.view.initThumbnail();
                    }
                });
            },
            setFromListingResponse: function(resp) {
                // Try to find a non-team video
                for(var i=0; i < resp.objects.length; i++) {
                    if(!resp.objects[i].team) {
                        this.setFromVideoData(resp.objects[i]);
                        return;
                    }
                }
                // Fall back to the first video
                this.setFromVideoData(resp.objects[0]);
            },
            setFromVideoData: function(videoData) {
                var that = this;
                this.set(videoData);
                sizeUpdated(this);
                var visibleLanguages = _$.map(_$.grep(this.get('languages'), function(language) {return language.published;}),
                        function(language) {return language.code;});
                this.get('languages').forEach(function(lang) {
                    that.languages_dir[lang.code] = lang.dir;
                });
                // Set the initial language to either the one provided by the initial
                // options, or the original language from the API.
                this.set('initial_language',
                        (this.get('initial_language') && (visibleLanguages.indexOf(this.get('initial_language')) > -1) && this.get('initial_language')) ||
                        (this.get('original_language') && (visibleLanguages.indexOf(this.get('original_language')) > -1) && this.get('original_language')) ||
                        ((visibleLanguages.indexOf('en') > -1) && 'en') ||
                        ((visibleLanguages.length > 0) && visibleLanguages[0])
                        );
            }
        });

        // SubtitleSet model.
        var SubtitleSet = _Backbone.Model.extend({

            // Set from the Amara API
            description: null,
            language: null,
            note: null,
            resource_uri: null,
            site_url: null,
            sub_format: null,
            subtitles: [],
            title: null,
            version_no: null,
            video: null,
            video_description: null,
            video_title: null

        });

        // Subtitles collection.
        this.Subtitles = _Backbone.Collection.extend({
            model: SubtitleSet
        });

        // Amara view. This contains all of the events and logic for a single instance of
        // an Amara-powered video.
        this.AmaraView = _Backbone.View.extend({
            initialize: function() {
                this.model.view = this;
                this.template = __.template(this.templateHTML());
                this.templateVideo = __.template(this.templateVideoHTML());
                // Default states.
                this.states = {
                    autoScrolling: true,
                    autoScrollPaused: false,
                    contextMenuActive: false
                };
                // Fullscreen requires several different events since it's not yet standardized
                var that = this;
                function onFullscreenChange() {
                    sizeUpdated(that.model);
                }
                document.addEventListener("fullscreenchange", onFullscreenChange, false);
                document.addEventListener("mozfullscreenchange", onFullscreenChange, false);
                document.addEventListener("webkitfullscreenchange", onFullscreenChange, false);
                document.addEventListener("msfullscreenchange", onFullscreenChange, false);
            },
            events: {

                // Global
                'click':                                 'mouseClicked',
                'mousemove':                             'mouseMoved',
		'click div.video-thumbnail':             'thumbnailClicked',
                // Toolbar
                'click a.amara-share-button':            'shareButtonClicked',
                'click a.amara-subtitles-button':        'toggleSubtitlesDisplay',
                'click ul.amara-languages-list a.language-item':       'changeLanguage',
                'click a.amara-transcript-button':       'toggleTranscriptDisplay',
                'click a.amara-fullscreen-button':       'toggleFullscreen',
                'keyup input.amara-transcript-search':   'updateSearch',
                'change input.amara-transcript-search':  'updateSearch',

                'click a.amara-transcript-search-next':  'moveSearchNext',
                'click a.amara-transcript-search-prev':  'moveSearchPrev',

                // Transcript
                'click a.amara-transcript-autoscroll':   'pauseAutoScroll',
                'click a.amara-transcript-line':         'transcriptLineClicked'
                //'contextmenu a.amara-transcript-line':   'showTranscriptContextMenu'
            },
	    initThumbnail: function() {
		if (this.model.get('thumbnail')) {
		    this.$thumbnailContainer.css('background', '#000000 url(' +  this.model.get('thumbnail') + ') no-repeat').css('background-size', '100%');
		    notifyThumbnailLoadedToHost({model: this.model});
		}
		else
		    this.$thumbnailContainer.hide();
	    },
	    hideThumbnail: function() {
		this.$thumbnailContainer.hide();
	    },
	    resize_: function() {
                var width = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
                var height = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
                height -= _$('.amara-tools').height();
                this.$popContainer.width(width);
                this.$popContainer.height(height);
                if (this.$amaraTools !== undefined)
                    this.$amaraTools.width(width);
                this.$thumbnailContainer.width(width);
                this.$thumbnailContainer.height(height);
                this.$videoDivContainer.width(width);
                this.$videoDivContainer.height(height);
                // For HTML5 videos, we also need to update the element
                _$('video', this.$popContainer).width(width).height(height);
                this.$thumbnailButton.css('margin-top', ((height - 35) / 2) + "px");
                this.model.set('height', height);
                this.model.set('width', width);
	    },
            render: function() {
                // TODO: Split this monster of a render() into several render()s.
                var that = this;
                this.subtitleLines = [];
                this.currentSearch = '';
                this.currentSearchIndex = 0;
                this.currentSearchMatches = 0;

                var width = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
                var height = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
                // If jQuery exists on the page, Backbone tries to use it and there's an odd
                // bug if we don't convert it to a local Zepto object.
                this.$el = _$(this.$el.get(0));
		// We add a thumbnail, which includes the thumbnail image
		// if it was set, plus a play button
		this.$el.prepend('<div class="video-div">' +
                                 '  <div style="position:absolute;" class="amara-popcorn"></div>' +
                                 '  <div class="video-thumbnail" style="position:absolute;">' +
                                 '    <div class="thumbnail-button medium"><button class="play"></button></div>' +
                                 '  </div>' +
                                 '</div>');
                this.$popContainer = _$('div.amara-popcorn', this.$el);
                this.$thumbnailContainer = _$('div.video-thumbnail', this.$el);
                this.$videoDivContainer = _$('div.video-div', this.$el);
                this.$thumbnailButton = _$('div.thumbnail-button', this.$el);
                this.resize_();

                this.$el.append(this.template({
                    video_url: apiDomain(this.model.get('embed_on_amara')) + '/en/videos/create/?initial_url=' + this.model.get('url'),
		    original_video_url:  this.model.get('url'),
		    download_subtitle_url: '',
                    width: this.model.get('width')
                }));

                // This is a hack until Popcorn.js supports passing a DOM elem to
                // its smart() method. See: http://bit.ly/L0Lb7t
                var id = 'amara-popcorn-' + Math.floor(Math.random() * 100000000);
                this.$popContainer.attr('id', id);

                // Reset the height on the parent amara-embed div. If we don't do this,
                // our amara-tools div won't be visible.
                this.$el.height('auto');
                // Init the Popcorn video.
                this.pop = _Popcorn.amara(this.$popContainer.attr('id'),
                        this.model.get('player_urls'),
                        this.model.get('video_type'), {
                            controls: true,
                            frameAnimation: true
                        });
                this.pop.controls(true);

                this.pop.on('error', function() {
                    if (that.pop.error.code == window.MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED) {
                            notifyVideoLoadedToHost(window.MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED);
		    }
                });

                this.pop.on('loadedmetadata', function() {
                    // Just set some cached Zepto selections for later use.
                    that.cacheNodes();

                    // Setup tracking for the scroll event on the transcript body.
                    // TODO: Find a way to get this into the core Backbone events on the Amara view.
                    that.$transcriptBody.on('scroll', function() {
                        that.transcriptScrolled();
                    });

                    // Wait until we have a complete video model (the API was hit as soon as
                    // the video instance was created), and then retrieve the initial set
                    // of subtitles, so we can begin building out the transcript viewer
                    // and the subtitle display.
                    //
                    // We could just make this a callback on the model's initialize() for
                    // after we get a response, but there may be cases where we want to init
                    // a VideoModel separately from an AmaraView.
                    that.waitUntilVideoIsComplete(
                        function() {
                            // Grab the subtitles for the initial language and do yo' thang.
                            if (that.model.get('is_on_amara') && that.model.get('initial_language')) {
                                analytics('embedder', 'launched');
                                // Build the language selection dropdown menu.
                                that.buildLanguageSelector();
                                // update the view on amara button
                                that.$viewOnAmaraButton.attr('href', apiDomain(that.model.get('embed_on_amara')) + '/en/videos/' + that.model.get('id'));
                                // change video url based on team type
                                if (that.model.get('team_type') == 'EC') {
                                    _$('#amara-video-link').attr('href', apiDomain(that.model.get('embed_on_amara')) + '/subtitles/editor/' + that.model.get('id') + '/en/?team=' + that.model.get('team'));
                                } else {
                                    _$('#amara-video-link').attr('href', apiDomain(that.model.get('embed_on_amara')) + '/subtitles/editor/' + that.model.get('id') + '/');
                                }
                                // Make the request to fetch the initial subtitles.
                                // TODO: This needs to be an option.
                                that.loadSubtitles(that.model.get('initial_language'));
                            } else {
                                // Do some other stuff for videos that aren't yet on Amara
				// or that do not have subtitles
                                // Language selector drop-up menu becomes a link to amara
				that.model.set({'no_subtitles': true});
				_$(".amara-displays").hide();
				if (!that.model.get('show_subtitle_me'))
				    _$(".amara-languages").hide();
				_$(".amara-languages").css('min-width', "130px").css({"border-left-color": "#2B2C2D", "border-left-width":"1px", "border-left-style":"solid"});
				if (that.model.get('is_on_amara'))
                                    that.$amaraCurrentLang.attr("href", apiDomain(that.model.get('embed_on_amara')) + '/en/videos/' + that.model.get('id'));
				else
                                    that.$amaraCurrentLang.attr("href", apiDomain(that.model.get('embed_on_amara')) + '/en/videos/create/?initial_url=' + that.model.get('url'));
                                that.$amaraCurrentLang.attr("target", '_blank');
                                that.$amaraCurrentLang.removeAttr("data-toggle");
                                that.setCurrentLanguageMessage('subtitle me');
                                that.setTranscriptDisplay(false);
                            }
                            sizeUpdated(that.model);
                            window.setInterval(sizeUpdated, 1000, that.model);
			    notifyVideoLoadedToHost();
                        }
                    );
                });
                return this;

            },
            // View methods.
            mouseClicked: function(e) {
                this.hideTranscriptContextMenu();
            },
            thumbnailClicked: function(e) {
		if (this.pop && this.pop.play) {
		    this.hideThumbnail();
		    this.pop.play();
		}
            },
            mouseMoved: function(e) {
                this.setCursorPosition(e);
            },
            
            buildLanguageSelector: function() {
                var langs = this.model.get('languages');
                langs.sort(function(l1, l2) {
		    if (l1.name > l2.name) return 1;
		    if (l1.name < l2.name) return -1;
		    return 0;
		});
                var video_url = this.model.get('url');
                this.$amaraLanguagesList.append(this.templateVideo({
                        video_url: apiDomain(this.model.get('embed_on_amara')) + '/en/videos/create/?initial_url=' + video_url,
		}));
		if (this.model.get('show_order_subtitles') ||
		    this.model.get('show_download_subtitles') ||
		    this.model.get('show_improve_subtitles') ||
		    this.model.get('show_embed_code'))
                    this.$amaraLanguagesList.append('            <li role="presentation" class="divider"></li>');
		// TODO: This wont work if we have several widgets in one page
                this.$amaraLanguagesList.append('            <li role="presentation"><div><ul id="language-list-inside"></ul></div></li>');
                

                if (langs.length) {
                    for (var i = 0; i < langs.length; i++) {
                        _$('#language-list-inside').append('' +
							   '<li role="presentation">' +
							   '<a role="menuitem" tabindex="-1" ' +
							   (langs[i].published  ? ('href="#" class="language-item" data-language="' + langs[i].code + '"') : 'class="language-item-inactive"') +
							   '>' +
							   langs[i].name +
							   '</a>' +
							   '</li>');
                    }
		    // Scrollbar for languages only
		    _$('#language-list-inside').mCustomScrollbar({
			theme:"light-thick"
		    });
		    // When the user clicks on the scrollbar, don't close the dropdown
		    _$(".mCSB_scrollTools").click(function( event ) {
			event.stopPropagation();
		    });
		    // When the menu opens, we scroll to the selected language
		    _$('.dropdown').on('shown.bs.dropdown', function () {
			_$("#language-list-inside").mCustomScrollbar("update");
			_$("#language-list-inside").mCustomScrollbar("scrollTo",".currently-selected");
		    });
                } else {
                    // We have no languages.
                }
            },
            setCurrentLanguageMessage: function(text) {
                this.$amaraCurrentLang.text(text);
                // Hide the expander triangle
                this.$amaraCurrentLang.css('background-image', 'none');
            },
            buildSubtitles: function(language) {

                // Remove any existing subtitle events.
                this.pop.removePlugin('amarasubtitle');
                
                // TODO: This is a temporary patch for Popcorn bug http://bit.ly/NShGdX
                //
                // (we think)
                this.pop.data.trackEvents.endIndex = 0;
                this.pop.data.trackEvents.startIndex = 0;

                // Get the subtitle sets for this language.
                var subtitleSets = this.model.subtitles.where({'language': language});

                if (subtitleSets.length) {
                    var subtitleSet = subtitleSets[0];

                    // Get the actual subtitles for this language.
                    var subtitles = subtitleSet.get('subtitles');

                    // For each subtitle, init the Popcorn subtitle plugin.
                    for (var i = 0; i < subtitles.length; i++) {
                        this.pop.amarasubtitle({
                            start: subtitles[i].start / 1000.0,
                            end: subtitles[i].end / 1000.0,
                            text: subtitles[i].text,
                            region: subtitles[i].meta.region
                        });
                    }

                    this.$popSubtitlesContainer = _$('div.amara-popcorn-subtitles', this.$el);

                }
            },
            buildTranscript: function(language) {

                var that = this;

                // remove plugins added for previous languages
                this.pop.removePlugin('code');

                // TODO: This is a temporary patch for Popcorn bug http://bit.ly/NShGdX
                //
                // (we think)
                this.pop.data.trackEvents.endIndex = 0;
                this.pop.data.trackEvents.startIndex = 0;

                // Get the subtitle sets for this language.
                this.$transcriptBody.attr("dir", this.model.languages_dir[language]);
                this.$popContainer.attr("dir", this.model.languages_dir[language]);
                var subtitleSets = this.model.subtitles.where({'language': language});
                if (subtitleSets.length) {
                    var subtitleSet = subtitleSets[0];

                    // Get the actual subtitles for this language.
                    var subtitles = subtitleSet.get('subtitles');

                    // Remove the loading indicator.
                    this.$transcriptBody.html('');
                    var indexingTranscript = "";

                    for (var i = 0; i < subtitles.length; i++) {
                        var line = this.addSubtitleLine(subtitles[i]);
                        indexingTranscript += " " + subtitles[i].text;
                        this.pop.code({
                            start: subtitles[i].start / 1000.0,
                            end: subtitles[i].end / 1000.0,
                            line: line,
                            view: this,
                            onStart: function(options) {
                                options.line.classList.add('current-subtitle');
                                options.view.autoScrollToLine(options.line);
                            },
                            onEnd: function(options) {
                                options.line.classList.remove('current-subtitle');
                            }
                        });
                    }

	            setIndexingContent(indexingTranscript);

                    this.$amaraTranscriptLines = _$('a.amara-transcript-line', this.$transcriptBody);

                } else {
                    _$('.amara-transcript-line', this.$transcriptBody).text('No subtitles available.');
                }
            },
            addSubtitleLine: function(subtitle) {
                // Construct the transcript line.
                var line = document.createElement('a');
                line.href = '#';
                line.classList.add('amara-transcript-line');
                line.innerHTML = subtitle.text;
                line.title = formatTime(subtitle.start);
                // On transcript, we do not want thos new lines
                _$(line).find("br").replaceWith(" ");
                var container = this.$transcriptBody;
                if ((container.children().length == 0) || (subtitle.meta.new_paragraph))
                    container.append(document.createElement('p'));
                var currentParagraph = container.children().last();

                var pop = this.pop;
                line.addEventListener('click', function(e) {
                    pop.currentTime(subtitle.start / 1000.0);
                    e.preventDefault();
                    return false;
                }, false);
                // Add the subtitle to the transcript container.
                currentParagraph.append(line);
                this.subtitleLines.push({
                    line: line,
                    subtitle: subtitle,
                });
                return line;
            },
            cacheNodes: function() {
                this.$amaraTools         = _$('div.amara-tools',      this.$el);
                this.$amaraBar           = _$('div.amara-bar',        this.$amaraTools);
                this.$amaraTranscript    = _$('div.amara-transcript', this.$amaraTools);

                this.$viewOnAmaraButton   = _$('a.amara-logo', this.$amaraBar);
                this.$amaraDisplays      = _$('ul.amara-displays',         this.$amaraTools);
                this.$transcriptButton   = _$('a.amara-transcript-button', this.$amaraDisplays);
                this.$subtitlesButton    = _$('a.amara-subtitles-button',  this.$amaraDisplays);
                this.$fullscreenButton   = _$('a.amara-fullscreen-button', this.$amaraDisplays);
                this.$transcriptHeaderRight = _$('div.amara-transcript-header-right', this.$amaraTranscript);
                this.$search              = _$('input.amara-transcript-search', this.$transcriptHeaderRight);
                this.$searchNext          = _$('a.amara-transcript-search-next', this.$transcriptHeaderRight);
                this.$searchPrev          = _$('a.amara-transcript-search-prev', this.$transcriptHeaderRight);

                this.$amaraLanguages     = _$('div.amara-languages',       this.$amaraTools);
                this.$amaraCurrentLang   = _$('a.amara-current-language',  this.$amaraLanguages);
                this.$amaraLanguagesList = _$('ul.amara-languages-list',   this.$amaraLanguages);

                this.$transcriptBody     = _$('div.amara-transcript-body',     this.$amaraTranscript);
                this.$autoScrollButton   = _$('a.amara-transcript-autoscroll', this.$amaraTranscript);
                this.$autoScrollOnOff    = _$('span', this.$autoScrollButton);
            },
            changeLanguage: function(e) {
                var that = this;
                var language = _$(e.target).data('language');
                analytics('embedder', 'change-language', language);
                this.loadSubtitles(language);
            },
            loadSubtitles: function(language) {
                // If we've already fetched subtitles for this language, don't
                // fetch them again.
                var that = this;
		if (language) {
                    var subtitleSets = this.model.subtitles.where({'language': language});
                    if (subtitleSets.length) {
			this.setCurrentLanguage(language);
                    } else {
			this.fetchSubtitles(language, function() {
                            that.setCurrentLanguage(language);
			});
                    }
		} else {
                    that.setCurrentLanguage("");
		}
            },
            setCurrentLanguage: function(language) {
                this.buildTranscript(language);
                this.buildSubtitles(language);
		if (language.length) {
		    this.setSubtitlesDisplay(this.model.get('show_subtitles_default'));
		    this.setTranscriptDisplay(this.model.get('show_transcript_default'));
                    this.scrollTranscriptToCurrentTime();
                    var subtitleSets = this.model.subtitles.where({'language': language});
                    if (subtitleSets.length) {
			var languageCode = subtitleSets[0].get('language');
			var languageName = this.getLanguageNameForCode(languageCode);
			_$('ul.amara-languages-list a').removeClass('currently-selected');
			this.$amaraLanguagesList.find("[data-language='" + language + "']").addClass('currently-selected');
			this.$amaraCurrentLang.text(languageName);
			_$('#amara-download-subtitles').attr('href', apiDomain(this.model.get('embed_on_amara')) + '/en/videos/' + this.model.get('id') + '/' + languageCode);
                        var amara_video_link = apiDomain(this.model.get('embed_on_amara')) + '/subtitles/editor/' + this.model.get('id') + '/' + languageCode;
                        if (this.model.get('team') && (this.model.get('team_type') == 'EC'))
                            amara_video_link += '?team=' + this.model.get('team');
			_$('#amara-video-link').attr('href', amara_video_link);
			_$('ul.amara-languages-list li').removeClass('currently-selected-item');
			_$('.currently-selected').parent().addClass('currently-selected-item');
                    } else {
			this.setCurrentLanguageMessage('No Subtiles');
                    }
		} else
		    this.setCurrentLanguageMessage('No Subtiles');
                // Show the expander triangle
                this.$amaraCurrentLang.css('background-image', '');
            },
            fetchSubtitles: function(language, callback) {
                // Make a call to the Amara API and retrieve a set of subtitles for a specific
                // video in a specific language. When we get a response, add the subtitle set
                // to the video model's 'subtitles' collection for later retrieval by language code.
                var that = this;

                var apiURL = ''+
                    apiDomain(this.model.get('embed_on_amara')) + '/api/videos/' +
                    this.model.get('id') + '/languages/' + language + '/subtitles/';

                // Make a call to the Amara API to retrieve subtitles for this language.
                //
                // TODO: If we already have subtitles in this language, don't do anything.
                _$.ajax({
                    url: apiURL,
                    success: function(resp) {
                        // Save these subtitles to the video's 'subtitles' collection.
                        // TODO: Placeholder until we have the API return the language code.
                        resp.language = language;

                        // Sometimes the last subtitle may have no end time. Fix that.
                        var lastSub = resp.subtitles[resp.subtitles.length - 1];
                        if (lastSub.end === -1) {
                            lastSub.end = that.pop.duration();
                        }

                        that.model.subtitles.add(
                            new SubtitleSet(resp)
                        );

                        // Call the callback.
                        callback();
                    },
                    error: function() {
                        // We should handle errors better here, but simply
                        // invoking the callback works okay for now.
                        callback();
                    }
                });
            },
            getLanguageNameForCode: function(languageCode) {
                // TODO: This is a temporary utility function to grab a language's name from a language
                // code. We won't need this once we update our API to return the language name
                // with the subtitles.
                // See https://unisubs.sifterapp.com/projects/12298/issues/722972/comments
                var languages = this.model.get('languages');
                var language = __.find(languages, function(l) { return l.code === languageCode; });
                return language.name;
            },
            hideTranscriptContextMenu: function() {
                if (this.states.contextMenuActive) {

                    // Deselect the transcript line and remove the context menu.
                    this.$amaraTranscriptLines.removeClass('selected');
                    this.$amaraContextMenu.remove();

                }
            },
            linkToTranscriptLine: function(line) {
                this.hideTranscriptContextMenu();
                return false;
            },
            pauseAutoScroll: function(isNowPaused) {

                var that = this;
                var previouslyPaused = this.states.autoScrollPaused;

                // If 'isNowPaused' is an object, it's because it was sent to us via
                // Backbone's event click handler.
                var fromClick = (typeof isNowPaused === 'object');

                // If the transcript plugin is triggering this scroll change, do not
                // pause the auto-scroll.
                if (this.states.autoScrolling && !fromClick) {
                    this.states.autoScrolling = false;
                    return false;
                }

                // If from clicking the "Auto-scroll" button, just toggle it.
                if (fromClick) {
                    isNowPaused = !this.states.autoScrollPaused;
                }

                // Switch the autoScrollPaused state on the view.
                this.states.autoScrollPaused = isNowPaused;

                // Update the Auto-scroll label in the transcript viewer.
                this.$autoScrollOnOff.text(isNowPaused ? 'OFF' : 'ON');

                // If we're no longer paused, scroll to the currently active subtitle.
                if (!isNowPaused) {
                    this.scrollTranscriptToCurrentTime();
                } else {

                    // If we're moving from a scrolling state to a paused state,
                    // highlight the auto-scroll button to indicate that we've changed
                    // states.
                    if (!previouslyPaused) {
                        this.$autoScrollButton.animate({
                            color: '#FF2C2C'
                        }, {
                            duration: 50,
                            easing: 'ease-in',
                            complete: function() {
                                that.$autoScrollButton.animate({
                                    color: '#9A9B9C'
                                }, 2000, 'ease-out');
                            }
                        });
                    }
                }
                
                return false;
            },
            autoScrollToLine: function(transcriptLine) {
                if (!this.states.autoScrollPaused) {
                    this.scrollToLine(transcriptLine);
                }
            },
            scrollToLine: function(transcriptLine) {
                // Scroll the transcript container to the line, and bring the
                // line to the center of the vertical height of the container.

                var $line = _$(transcriptLine);
                var $container = this.$transcriptBody;

                var lineTop = $line.offset().top - $container.offset().top;
                var lineHeight = $line.height();
                var containerHeight = $container.height();
                var oldScrollTop = $container.prop('scrollTop');
                // We need to tell our transcript tracking to ignore this
                // scroll change, otherwise our scrolling detector would
                // trigger the auto-scroll to stop.
                this.states.autoScrolling = true;
                $container.prop('scrollTop', oldScrollTop + lineTop -
                        (containerHeight / 2) + (lineHeight / 2));
            },
            scrollTranscriptToCurrentTime: function() {
                var currentTime = this.pop.currentTime() * 1000;
                // For each subtitle, init the Popcorn transcript plugin.
                for (var i = 0; i < this.subtitleLines.length; i++) {
                    var subtitleLine = this.subtitleLines[i];
                    if(subtitleLine.subtitle.start >= currentTime) {
                        this.scrollToLine(subtitleLine.line);
                        break;
                    }
                }
            },
            setCursorPosition: function(e) {
                this.cursorX = e.pageX;
                this.cursorY = e.pageY;
            },
            shareButtonClicked: function() {
                return false;
            },
            showTranscriptContextMenu: function(e) {

                var that = this;

                // Don't show the default context menu.
                e.preventDefault();

                // Remove the auto-selection that the browser does for some reason.
                window.getSelection().removeAllRanges();

                // Remove any existing context menus.
                this.hideTranscriptContextMenu();

                // Remove any previously selected line classes.
                this.$amaraTranscriptLines.removeClass('selected');

                // Signal that the line is selected.
                var $line = _$(e.target);
                $line.addClass('selected');

                // Create the context menu DOM.
                //
                // TODO: Use a sensible templating system. Everywhere.
                _$('body').append('' +
                        '<div class="amara-context-menu">' +
                        '    <ul>' +
                        '        <li>' +
                        '            <a class="amara-transcript-link-to-line" href="#">Link to this line</a>' +
                        '        </li>' +
                        '    </ul>' +
                        '</div>');

                this.$amaraContextMenu = _$('div.amara-context-menu');

                // Handle clicks.
                //_$('a', this.$amaraContextMenu).click(function() {
                    //that.linkToTranscriptLine($line);
                    //return false;
                //});

                // Don't let clicks inside the context menu bubble up.
                // Otherwise, the container listener will close the context menu.
                this.$amaraContextMenu.click(function(e) {
                    e.stopPropagation();
                });

                // Position the context menu near the cursor.
                this.$amaraContextMenu.css('top', this.cursorY + 11);
                this.$amaraContextMenu.css('left', this.cursorX + 6);

                // Set the state so we know we have an active context menu.
                this.states.contextMenuActive = true;

                return false;
            },
            toggleSubtitlesDisplay: function() {
		if (this.model.get('initial_language')) {
                    // TODO: This button needs to be disabled unless we have subtitles to toggle.
                    this.$popSubtitlesContainer.toggle();
                    analytics('embedder', 'subtitles-display',
				   (this.$popSubtitlesContainer.is(":visible") ? "show" : "hide"));
                    this.$subtitlesButton.toggleClass('amara-button-enabled');
		} else {
                    this.$subtitlesButton.removeClass('amara-button-enabled');
		}
                return false;
            },
            toggleTranscriptDisplay: function() {
                // TODO: This button needs to be disabled unless we have a transcript to toggle.
                this.$amaraTranscript.toggle();
                analytics('embedder', 'transcript-display',
                               (this.$amaraTranscript.is(":visible") ? "show" : "hide"));
                this.$transcriptButton.toggleClass('amara-button-enabled');
                sizeUpdated(this.model);
                return false;
            },
            toggleFullscreen: function() {
                if(isFullscreen()) {
                    cancelFullscreen();
                } else {
                    requestFullscreen();
                }
                return false;
            },
            setSubtitlesDisplay: function(show) {
		if (show) {
                    this.$popSubtitlesContainer.show();
                    this.$subtitlesButton.addClass('amara-button-enabled');
		} else {
                    this.$popSubtitlesContainer.hide();
                    this.$subtitlesButton.removeClass('amara-button-enabled');
		}
                analytics('embedder', 'subtitles-display',
                               (this.$popSubtitlesContainer.is(":visible") ? "show" : "hide"));
                return false;
            },
            setTranscriptDisplay: function(show) {
		if (show) {
                    this.$amaraTranscript.show();
                    this.$transcriptButton.addClass('amara-button-enabled');
		} else {
                    this.$amaraTranscript.hide();
                    this.$transcriptButton.removeClass('amara-button-enabled');
		}
                analytics('embedder', 'transcript-display',
                               (this.$amaraTranscript.is(":visible") ? "show" : "hide"));
		sizeUpdated(this.model);
                return false;
            },
            transcriptLineClicked: function(e) {
                this.hideTranscriptContextMenu();
                return false;
            },
            transcriptScrolled: function() {
                this.hideTranscriptContextMenu();
                this.pauseAutoScroll(true);
            },
            updateSearch: function() {
                var text = this.$search.val().trim();
                if(text != this.currentSearch) {
                    this.removeSearchSpans();
                    if(text) {
                        this.addSearchSpans(text);
                    }
                    this.currentSearch = text;
                    this.currentSearchIndex = 0;
                    this.currentSearchMatches = _$('span.search-match', this.$transcriptBody).length;
                    this.updateSearchCurrentMatch();
                }
                return false;
            },
            addSearchSpans: function(text) {
                var replacementText = '<span class="search-match">$1</span>';
                for(var i = 0; i < this.subtitleLines.length; i++) {
                    var line = this.subtitleLines[i].line;
                    var regex = new RegExp('(' + regexEscape(text) + ')', 'gi');
                    line.innerHTML = line.innerHTML.replace(regex,
                            replacementText);
                }
            },
            removeSearchSpans: function() {
                for(var i = 0; i < this.subtitleLines.length; i++) {
                    var line = this.subtitleLines[i].line;
                    var subtitle = this.subtitleLines[i].subtitle;
                    line.innerHTML = subtitle.text;
                }
            },
            moveSearchNext: function(evt) {
                this.currentSearchIndex = Math.min(this.currentSearchIndex + 1, this.currentSearchMatches - 1);
                this.updateSearchCurrentMatch();
                evt.preventDefault();
                return false;
            },
            moveSearchPrev: function(evt) {
                this.currentSearchIndex = Math.max(this.currentSearchIndex - 1, 0);
                this.updateSearchCurrentMatch();
                evt.preventDefault();
                return false;
            },
            updateSearchCurrentMatch: function() {
                if(this.currentSearchMatches > 0) {
                    this.showSearchArrows();
                } else {
                    this.hideSearchArrows();
                }
                if(this.currentSearchIndex == 0) {
                    this.$searchPrev.addClass('disabled');
                } else {
                    this.$searchPrev.removeClass('disabled');
                }
                if(this.currentSearchIndex == this.currentSearchMatches - 1) {
                    this.$searchNext.addClass('disabled');
                } else {
                    this.$searchNext.removeClass('disabled');
                }
                _$('span.current-search-match', this.$transcriptBody).removeClass('current-search-match');
                var that = this;
                _$('span.search-match', this.$transcriptBody)
                    .eq(this.currentSearchIndex)
                    .addClass('current-search-match')
                    .each(function(index, span) {
                        that.scrollToLine(span.parentElement);

                    });
            },
            showSearchArrows: function() {
                this.$searchNext.show();
                this.$searchPrev.show();
            },
            hideSearchArrows: function() {
                this.$searchNext.hide();
                this.$searchPrev.hide();
            },
            waitUntilVideoIsComplete: function(callback) {
                var that = this;
                // is_complete gets set as soon as the initial API call to build out the video
                // instance has finished.
                if (!this.model.get('is_complete')) {
                    setTimeout(function() { that.waitUntilVideoIsComplete(callback); }, 100);
                } else {
                    callback();
                }
            },
	    templateVideoHTML: function() {
                return '' +
                (this.model.get('show_improve_subtitles') ? '<li role="presentation" class="unisubs-subtitle-homepage"><a role="menuitem" tabindex="-1" id="amara-video-link" href="{{ video_url }}" target="blank" title="Improve these subtitles on amara.org">Improve these Subtitles</a></li>' : '') +
                (this.model.get('show_embed_code') ? '<li role="presentation" class="unisubs-embed-link"><a role="menuitem" tabindex="-1" id="amara-embed-link" href="" data-toggle="modal" data-target="#embed-code-modal" title="Get the embed code">Get Embed Code</a></li>' : '') +
                (this.model.get('show_download_subtitles') ? '<li role="presentation" class="unisubs-download-subtitles"><a role="menuitem" tabindex="-1" id="amara-download-subtitles" href="{{ video_url }}" target="blank" title="Download subtitles from amara.org">Download Subtitles</a></li>' : '') +
		(this.model.get('show_order_subtitles') ? '<li role="presentation" class="unisubs-order-subtitles"><a role="menuitem" tabindex="-1" href="//pro.amara.org/ondemand" target="blank" title="Order Captions or Subtitles">Order Captions or Subtitles</a></li>' : '');
	    },
	    templateHTML: function() {
		return '' +
                '<div class="amara-tools">' +
                '    <div class="amara-bar amara-group">' +
                (this.model.get('show_logo') ? '        <a href="{{ video_url }}" target="blank" class="amara-logo amara-button" title="View this video on Amara.org in a new window">Amara</a>' : '') +
                '        <ul class="amara-displays amara-group">' +
                '            <li><a href="#" class="amara-transcript-button amara-button" title="Toggle transcript viewer"></a></li>' +
                '            <li><a href="#" class="amara-subtitles-button amara-button" title="Toggle subtitles"></a></li>' +
                '        </ul>' +
                '        <ul class="amara-displays amara-displays-right amara-group">' +
                '            <li><a href="#" class="amara-fullscreen-button amara-button amara-button-enabled" title="Toggle fullscreen"></a></li>' +
                '        </ul>' +
                '        <div class="dropdown amara-languages">' +
                '            <a class="amara-current-language" id="dropdownMenu1" role="button" data-toggle="dropdown" data-target="#" href="">Loading&hellip;' +
                '            </a>'+
                '            <ul id="languages-dropdown" class="dropdown-menu amara-languages-list" role="menu" aria-labelledby="dropdownMenu1"></ul>' +
                '        </div>' +
                '    </div>' +
                '    <div class="amara-transcript">' +
                '        <div class="amara-transcript-header amara-group">' +
                '            <div class="amara-transcript-header-left">' +
                '                <a class="amara-transcript-autoscroll" href="#">Auto-scroll <span>ON</span></a>' +
                '            </div>' +
                '            <div class="amara-transcript-header-right">' +
                '                    <input class="amara-transcript-search" placeholder="Search transcript" />' +
                '                    <a href="#" class="amara-transcript-search-next"></a>' +
                '                    <a href="#" class="amara-transcript-search-prev"></a>' +
                '            </div>' +
                '        </div>' +
                '        <div class="amara-transcript-body">' +
                '            <a href="#" class="amara-transcript-line">' +
                '                <span class="amara-transcript-line">' +
                '                    Loading transcript&hellip;' +
                '                </span>' +
                '            </a>' +
                '        </div>' +
                '    </div>' +
                '</div>' +
		'<link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.0.2/css/bootstrap.min.css">' +
	        '<script src="//netdna.bootstrapcdn.com/bootstrap/3.0.2/js/bootstrap.min.js"></script>' +
                '    <div class="modal fade" id="embed-code-modal" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" aria-hidden="true">' +
		'        <div class="modal-dialog">' +
		'            <div class="modal-content">' +
		'                <div class="modal-body">' +    
		'                    <p>Step 1: paste this anywhere in your document:</p>' +
                '                        <pre class="pre-small">' +
                '&lt;script type="text/javascript" src="https://amara.org/embedder-iframe"&gt;\n' +
                '&lt;/script&gt;' +
                '                        </pre>' +
                '                        <p>Step 2: paste this somewhere inside your HTML body, wherever you would like your widgets to appear:</p>' +
                '                        <pre class="pre-small">' +
                '&lt;div class="amara-embed" data-url="{{ original_video_url }}"&gt;&lt;/div&gt;' +
                '                        </pre>' +
                '                        <ul>' +
                '                            <li>Hide order subtitles menu item: <code>data-hide-order="true"</code>.</li>' +
                '                            <li>Set initial active subtitle language: <code>data-initial-language="en"</code>.</li>' +
                '                            <li>Display subtitles by default: <code>data-show-subtitles-default="true"</code>.</li>' +
                '                            <li>Display transcript by default: <code>data-show-transcript-default="true"</code>.</li>' +
                '                        </ul>' +
		'                <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>' +

		'                    </div>' +
		'        </div>' +
		'    </div>' +
		'</div>'

	    }
        });

        // push() handles all action calls before and after the embedder is loaded.
        // Aside from init(), this is the only function that may be called from the
        // parent document.
        //
        // Must send push() an object with only two items:
        //     * Action  (string)
        //     * Options (object)
        //
        // Note: we don't use traditional function arguments because before the
        // embedder is loaded, _amara is just an array with a normal push() method.
        this.push = function(args) {
            
            // No arguments? Don't do anything.
            if (!arguments.length) { return; }

            // Must send push() an object with only two items.
            if (__.size(arguments[0]) === 2) {

                var action = args[0];
                var options = args[1];

                // If a method exists for this action, call it with the options.
                if (actions[action]) {
                    actions[action](options);
                }
            }

        };

        // init() gets called as soon as the embedder has finished loading.
        // Simply processes the existing _amara queue if we have one.
        this.init = function() {
            // Change the template delimiter for Underscore templates.
            __.templateSettings = { interpolate : /\{\{(.+?)\}\}/g };

            // If we have a queue from before the embedder loaded, process the actions.
            if (toPush) {
                for (var i = 0; i < toPush.length; i++) {
                    that.push(toPush[i]);
                }
                toPush = [];
            }

            // Check to see if we have any amara-embed's to initilize.
            var amaraEmbeds = _$('div.amara-embed');

            if (amaraEmbeds.length) {
                _$.each(amaraEmbeds, function() {

                    var $div = _$(this);

                    // Call embedVideo with this div and URL.
                    that.push(['embedVideo', {
                        'div': this,
                        'initial_language': $div.data('initial-language'),
                        'url': $div.data('url'),
                        'team': $div.data('team'),
                        'video_id': $div.data('videoId'),
			'show_subtitle_me': $div.data('hide-subtitle-me') ? false : true,
                        'show_logo': $div.data('hide-logo') ? false : true,
                        'show_order_subtitles': $div.data('hide-order') ? false : true,
                        'show_improve_subtitles': $div.data('hide-improve') ? false : true,
                        'show_download_subtitles': $div.data('hide-download') ? false : true,
                        'show_embed_code': $div.data('hide-embed') ? false : true,
			'show_subtitles_default': $div.data('show-subtitles-default'),
			'show_transcript_default': $div.data('show-transcript-default'),
			'embed_on_amara': $div.data('embed-on-amara') ? true : false,
                    }]);
                });
            }	    
        };

    };

    _$(document).ready(function() {
        window._amara = new Amara();
        window._amara.init();
    });

}(window, document));
