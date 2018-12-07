/* Amara, universalsubtitles.org
 *
 * Copyright (C) 2013 Participatory Culture Foundation
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see
 * http://www.gnu.org/licenses/agpl-3.0.html.
 */
(function() {

var $document = $(document);

$.fn.openModal = function(openEvent, setupData) {
    if(setupData === undefined) {
        setupData = {}
    }
    this.each(function() {
        var modal = $(this);
        if(setupData) {
            setupModal(modal, setupData);
        }
        var closeButton = $('button.close', modal);

        modal.addClass('shown');
        $('body').append('<div class="modal-overlay"></div>');
        closeButton.bind('click.modal', onClose);
        modal.trigger('open');

        $document.bind('click.modal', function(evt) {
            if(openEvent && evt.timeStamp <= openEvent.timeStamp) return;
            var clickedModal = $(evt.target).closest('aside.modal');
            if(clickedModal.length == 0) {
                // click outside the modal
                onClose(evt);
            } else if($(evt.target).closest('button.close', clickedModal).length > 0) {
                // click on the close button
                onClose(evt);
            }
        });
        $document.bind('keydown.modal', function(evt) {
            if (evt.keyCode === 27) {
                onClose(evt);
            }
        });
        modal.on('close', onClose);

        function onClose(evt) {
            evt.preventDefault();
            if(setupData.removeOnClose) {
                modal.remove();
            } else {
                modal.removeClass('shown');
            }
            removeModalOverlay();
            closeButton.unbind('click.modal');
            $document.unbind('click.modal');
            $document.unbind('keydown.modal');
            modal.trigger('close');
        }
    });

    function setupModal(modal, setupData) {
        if(setupData['clear-errors']) {
            $('ul.errorlist', modal).remove();
        }
        if(setupData['heading']) {
            $('h3', modal).text(setupData['heading']);
        }
        if(setupData['text']) {
            $('.text', modal).text(setupData['text']);
        }
        if(setupData['setFormValues']) {
            $.each(setupData['setFormValues'], function(name, value) {
                $('*[name=' + name + ']', modal).val(value);
            });
        }
        if(setupData['copyInput']) {
            var inputName = setupData['copyInput'];
            var form = $('form', modal);
            // Delete any inputs added before
            $('input[name=' + inputName + '].copied', form).remove();
            // Copy any inputs outside of forms into the modal
            $('input[name=' + inputName + ']')
                .not(':checkbox:not(:checked)').each(function() {
                    var input = $(this);
                    if(input.closest("form").length > 0) {
                        return;
                    }
                    input.clone().attr('type', 'hidden').addClass('copied').appendTo(form);
                });
        }
    }
}

function removeModalOverlay() {
    $('body div.modal-overlay').remove();
}

window.ajaxOpenModal = function(url, params, setupData) {
    if(params === undefined) {
        params = {};
    }
    var setupData = $.extend({}, setupData, {removeOnClose: true});
    var loadingHTML = $('<div class="modal-overlay"><div class="loading"><span class="fa fa-spinner fa-pulse"></span></div></div>');

    $('body').append(loadingHTML);

    function setupAjaxModal(modal) {
        modal.updateBehaviors();
        $('form', modal).ajaxForm({
            url: url + '?' + $.param(params),
            beforeSubmit: function(data, form, options) {
                $('button.submit', form).append(
                    ' <i class="fa fa-refresh fa-spin"></i>'
                ).prop('disabled', true);
            },
            error: function(xhr, errorString, textStatus) {
                modal.remove();
                showErrorModal("Error Submitting Form", textStatus);
            },
            success: function(responseText, textStatus, xhr) {
                if(xhr.getResponseHeader('X-Form-Success')) {
                    removeModalOverlay();
                    modal.trigger('close');
                    if(xhr.getResponseHeader('X-Form-Redirect')) {
                        window.location = xhr.getResponseHeader('X-Form-Redirect');
                    } else if(setupData.reloadElt) {
                        var newElt = $(responseText);
                        $(setupData.reloadElt).replaceWith(newElt);
                        newElt.updateBehaviors();
                    } else {
                        window.location.reload();
                    }
                } else {
                    removeModalOverlay();
                    var newModal = $(responseText);
                    modal.replaceWith(newModal);
                    newModal.openModal();
                    setupAjaxModal(newModal);
                }
            }
        });
    }

    $.get(url, params)
    .done(function(data, textStatus, xhr) {
        loadingHTML.remove();
        var modal = $(data);
        modal.appendTo(document.body).openModal(null, setupData);
        setupAjaxModal(modal);
    })
    .fail(function(xhr, textStatus, errorThrown) {
        console.log("error loading modal from " + url + "(" + textStatus + ")");
        loadingHTML.remove();
    });
}

window.showErrorModal = function(header, text) {
    var header = $('<h3>').text(header);
    var text = $('<p>').text(text);
    var closeButton = $('<button class="close">');
    var modal = $('<aside class="modal">').append(closeButton, header, text);
    modal.appendTo('body').openModal();
}

$document.ready(function() {
    $('.open-modal').each(function() {
        var link = $(this);
        var modal = $('#' + link.data('modal'));

        link.bind('click', function(e) {
            e.preventDefault();
            modal.openModal(e, link.data());
        });
    });

    $('aside.modal.start-open').openModal();
});

})();
